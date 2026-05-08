import requests
from bs4 import BeautifulSoup
import schedule
import time
import logging
import csv
import os
from datetime import datetime
import pytz
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO

# === НАСТРОЙКИ ===
BOT_TOKEN = "8721322369:AAEbrSQliG9A2lwgsf6S7QB7nyWswKwAkUQ"
CHAT_ID = "808170700"
URL = "https://uzrates.uz/kapitalbank/currency/"
HISTORY_FILE = "eur_history.csv"
TASHKENT_TZ = pytz.timezone("Asia/Tashkent")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
        logging.info("Сообщение отправлено")
    except Exception as e:
        logging.error(f"Ошибка отправки текста: {e}")

def send_telegram_photo(image_bytes, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        r = requests.post(
            url,
            data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": ("chart.png", image_bytes, "image/png")},
            timeout=30
        )
        r.raise_for_status()
        logging.info("График отправлен")
    except Exception as e:
        logging.error(f"Ошибка отправки графика: {e}")

def save_to_history(sell, buy):
    now = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M")
    file_exists = os.path.exists(HISTORY_FILE)
    with open(HISTORY_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["datetime", "sell", "buy"])
        writer.writerow([now, sell, buy])
    logging.info(f"Сохранено в историю: {now} sell={sell} buy={buy}")

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return [], [], []
    dates, sells, buys = [], [], []
    with open(HISTORY_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dates.append(datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M"))
                sells.append(int(row["sell"]))
                buys.append(int(row["buy"]))
            except Exception:
                pass
    return dates, sells, buys

def build_chart(dates, sells, buys):
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    ax.plot(dates, sells, color="#f5a623", linewidth=2, marker="o", markersize=4, label="Продажа")
    ax.plot(dates, buys, color="#4fc3f7", linewidth=2, marker="o", markersize=4, label="Покупка")

    ax.set_title("EUR/UZS — Kapital Bank (Мобильное приложение)", color="white", fontsize=13, pad=12)
    ax.set_ylabel("Сум", color="white")
    ax.tick_params(colors="white")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m %H:%M"))
    fig.autofmt_xdate(rotation=30)

    for spine in ax.spines.values():
        spine.set_edgecolor("#333355")

    ax.yaxis.get_major_formatter().set_useOffset(False)
    ax.legend(facecolor="#1a1a2e", labelcolor="white")
    ax.grid(color="#333355", linestyle="--", linewidth=0.5)

    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()

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
    if not rate:
        send_telegram("⚠️ Не удалось получить курс EUR. Попробую позже.")
        return

    sell = rate["app_sell"] or rate["exchange_sell"]
    buy = rate["app_buy"] or rate["exchange_buy"]
    source = "Мобильное приложение" if rate["app_sell"] else "Обменники"

    if not sell:
        send_telegram("⚠️ Курс EUR не найден. Попробую позже.")
        return

    save_to_history(sell, buy)
    dates, sells, buys = load_history()

    now_str = datetime.now(TASHKENT_TZ).strftime("%d.%m.%Y %H:%M")
    caption = (
        f"💶 <b>EUR/UZS — Kapital Bank ({source})</b>\n"
        f"🕐 {now_str} (Ташкент)\n\n"
        f"📈 Продажа: <b>{sell} сум</b>\n"
        f"📉 Покупка: <b>{buy} сум</b>"
    )

    if len(dates) >= 2:
        chart = build_chart(dates, sells, buys)
        send_telegram_photo(chart, caption)
    else:
        send_telegram(caption)

# Запуск сразу при старте
check_and_notify()

# Расписание по Ташкентскому времени
def schedule_tashkent(hour, minute=0):
    def job():
        now = datetime.now(TASHKENT_TZ)
        if now.hour == hour and now.minute == minute:
            check_and_notify()
    return job

schedule.every().minute.do(lambda: None)  # keep alive

# Проверяем каждую минуту и запускаем в нужное время
def tick():
    now = datetime.now(TASHKENT_TZ)
    if now.minute == 0 and now.hour in (11, 17):
        check_and_notify()

schedule.every().minute.do(tick)

logging.info("Бот запущен. Уведомления в 11:00 и 17:00 по Ташкенту.")

while True:
    schedule.run_pending()
    time.sleep(30)
