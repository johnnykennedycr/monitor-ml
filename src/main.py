import os
import json
import requests
import sys

from scraper import get_best_sellers
from affiliate import generate_affiliate_link

# Configurações
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, "database.json")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def load_db():
    if not os.path.exists(DATABASE_FILE) or os.stat(DATABASE_FILE).st_size == 0:
        return []
    try:
        with open(DATABASE_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_db(data):
    try:
        with open(DATABASE_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[DEBUG] Erro ao salvar DB: {e}")

def send_telegram_photo(token, chat_id, photo_url, caption):
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except:
        return None

def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

def main():
    print("--- INICIANDO BOT ---")
    seen_links = load_db()
    products = get_best_sellers()
    
    if not products:
        print("[DEBUG] Nenhum produto encontrado.")
        return

    new_seen = seen_links.copy()
    count = 0

    for item in products:
        if item["id"] in seen_links:
            continue

        print(f"[DEBUG] Processando: {item['name']} - {item['price']}")
        
        affiliate_url = generate_affiliate_link(item["link"])
        
        # LAYOUT DA MENSAGEM ATUALIZADO
        # Focamos em deixar o preço GIGANTE e o botão claro
        caption = (
            f"<b>{item['name']}</b>\n\n"
            f"🔥 <b>OFERTA:</b> <code>{item['price']}</code>\n"
            f"💳 <i>(Pode haver parcelamento sem juros)</i>\n\n"
            f"👇 <b>GARANTA O SEU AQUI:</b>\n"
            f"<a href='{affiliate_url}'>🛒 IR PARA O MERCADO LIVRE</a>"
        )

        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            if item.get("image_url"):
                resp = send_telegram_photo(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, item["image_url"], caption)
                if not resp or not resp.get("ok"):
                    send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, caption)
            else:
                send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, caption)
            
            count += 1
            new_seen.append(item["id"])
        else:
            print("[DEBUG] Simulação de envio:")
            print(caption)
            new_seen.append(item["id"])

    if count > 0:
        save_db(new_seen)
        print(f"[DEBUG] {count} envios realizados.")
    else:
        print("[DEBUG] Sem novidades.")

if __name__ == "__main__":
    main()