import json
from scraper import get_best_sellers
from affiliate import generate_affiliate_link
from notifier import send_telegram
import os

DATABASE_FILE = "src/database.json"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def load_db():
    try:
        with open(DATABASE_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_db(data):
    with open(DATABASE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def main():
    seen = load_db()
    products = get_best_sellers()
    new_seen = seen.copy()

    for item in products:
        if item["link"] not in seen:
            affiliate = generate_affiliate_link(item["link"])
            message = f"🔥 <b>{item['name']}</b>\n\n🔗 {affiliate}"

            send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message)
            new_seen.append(item["link"])

    save_db(new_seen)

if __name__ == "__main__":
    main()
