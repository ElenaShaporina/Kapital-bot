import requests
from bs4 import BeautifulSoup
import schedule
import time
import logging
 
# === НАСТРОЙКИ ===
BOT_TOKEN = "8721322369:AAEbrSQliG9A2lwgsf6S7QB7nyWswKwAkUQ"
CHAT_ID = "808170700"
URL = "https://uzrates.uz/kapitalbank/currency/"
CHECK_INTERVAL_HOURS = 2
 
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
 
def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
        logging.info("Сообщение отправлено")
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")
 
def get_eur_rate():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        r = requests.get(URL, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
 
        tables = soup.find_all("table")
        
        app_sell = None
        app_buy = None
        exchange_sell = None
        exchange_buy = None
 
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 4:
                    currency_text = cells[0].get_text(strip=True)
                    code_text = cells[1].get_text(strip=True)
                    buy_text = cells[2].get_text(strip=True).replace(" ", "").replace("\xa0", "")
                    sell_text = cells[3].get_text(strip=True).replace(" ", "").replace("\xa0", "")
                    
                    if "EUR" in code_text or "Евро" in currency_text:
                        try:
                            buy_val = int(buy_text)
                            sell_val = int(sell_text)
                            if buy_val > 0 and sell_val > 0:
                                if exchange_sell is None:
                                    exchange_sell = sell_val
                                    exchange_buy = buy_val
                                else:
                                    app_sell = sell_val
                                    app_buy = buy_val
                        except ValueError:
                            pass
 
        return {
            "app_sell": app_sell,
            "app_buy": app_buy,
            "exchange_sell": exchange_sell,
            "exchange_buy": exchange_buy,
        }
 
    except Exception as e:
        logging.error(f"Ошибка парсинга: {e}")
        return None
 
def check_and_notify():
    logging.info("Проверяю курс...")
    rate = get_eur_rate()
    if rate:
        if rate["app_sell"]:
            msg = (
                f"💶 <b>EUR — Мобильное приложение Kapital Bank</b>\n\n"
                f"📈 Продажа: <b>{rate['app_sell']} сум</b>\n"
                f"📉 Покупка: <b>{rate['app_buy']} сум</b>"
            )
        elif rate["exchange_sell"]:
            msg = (
                f"💶 <b>EUR — Обменники Kapital Bank</b>\n"
                f"<i>(курс приложения сейчас недоступен на uzrates.uz)</i>\n\n"
                f"📈 Продажа: <b>{rate['exchange_sell']} сум</b>\n"
                f"📉 Покупка: <b>{rate['exchange_buy']} сум</b>"
            )
        else:
            msg = "⚠️ Курс EUR не найден. Попробую через 2 часа."
        
        logging.info(f"Курс: {rate}")
        send_telegram(msg)
    else:
        send_telegram("⚠️ Не удалось получить курс EUR. Попробую через 2 часа.")
 
# Запуск сразу при старте
check_and_notify()
 
# Расписание каждые 2 часа
schedule.every(CHECK_INTERVAL_HOURS).hours.do(check_and_notify)
 
logging.info(f"Бот запущен. Проверка каждые {CHECK_INTERVAL_HOURS} часа.")
 
while True:
    schedule.run_pending()
    time.sleep(60)
 
