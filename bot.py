import requests
from bs4 import BeautifulSoup
import schedule
import time
import logging

# === НАСТРОЙКИ ===
BOT_TOKEN = "8721322369:AAEbrSQliG9A2lwgsf6S7QB7nyWswKwAkUQ"
CHAT_ID = "808170700"
URL = "https://kapitalbank.uz/ru/welcome.php"
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
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Referer": "https://kapitalbank.uz/",
    }
    try:
        r = requests.get(URL, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Ищем блок "Мобильное приложение" и EUR
        # Вкладки курсов обычно в data-атрибутах или отдельных div-ах
        # Парсим все таблицы/блоки с курсами
        text = r.text

        # Ищем JSON или структуру с курсами мобильного приложения
        # Попробуем найти EUR в контексте мобильного приложения
        import re
        
        # Ищем паттерн: EUR с продажей рядом с "мобильным приложением"
        # Попробуем найти все числа рядом с EUR
        eur_blocks = re.findall(r'EUR[^>]*?>.*?(\d{4,6}).*?(\d{4,6})', text, re.DOTALL)
        
        if not eur_blocks:
            # Альтернативный парсинг через BeautifulSoup
            all_text = soup.get_text()
            eur_idx = all_text.find('EUR')
            if eur_idx > 0:
                snippet = all_text[eur_idx:eur_idx+100]
                nums = re.findall(r'\d{4,6}', snippet)
                if len(nums) >= 2:
                    return {"sell": nums[0], "buy": nums[1]}
            return None
        
        # Берём первое совпадение (мобильное приложение идёт первым на странице при загрузке)
        sell, buy = eur_blocks[0]
        return {"sell": sell, "buy": buy}

    except Exception as e:
        logging.error(f"Ошибка парсинга: {e}")
        return None

def check_and_notify():
    logging.info("Проверяю курс...")
    rate = get_eur_rate()
    if rate:
        msg = (
            f"💶 <b>Курс EUR — Мобильное приложение Kapital Bank</b>\n\n"
            f"📈 Продажа: <b>{rate['sell']} сум</b>\n"
            f"📉 Покупка: <b>{rate['buy']} сум</b>"
        )
        send_telegram(msg)
    else:
        send_telegram("⚠️ Не удалось получить курс EUR с сайта Kapital Bank. Попробую через 2 часа.")

# Запуск сразу при старте
check_and_notify()

# Расписание каждые 2 часа
schedule.every(CHECK_INTERVAL_HOURS).hours.do(check_and_notify)

logging.info(f"Бот запущен. Проверка каждые {CHECK_INTERVAL_HOURS} часа.")

while True:
    schedule.run_pending()
    time.sleep(60)
