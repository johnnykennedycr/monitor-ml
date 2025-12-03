import os
import sys
import json
from scraper import get_best_sellers
from affiliate import generate_affiliate_link
from notifier import send_telegram

# Configura path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, "database.json")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def load_db():
    if not os.path.exists(DATABASE_FILE) or os.stat(DATABASE_FILE).st_size == 0:
        return []
    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_db(data):
    try:
        with open(DATABASE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[DEBUG] Erro ao salvar DB: {e}")

def main():
    print("--- INICIANDO BOT VIA API OFICIAL ---")
    
    seen = load_db()
    print(f"[DEBUG] Histórico carregado: {len(seen)} itens.")

    # A mágica acontece aqui (agora autenticado)
    products = get_best_sellers()

    if not products:
        print("[DEBUG] Nenhum produto retornado. Verifique as credenciais.")
        return

    new_seen = seen.copy()
    count = 0

    for item in products:
        if item["link"] not in seen:
            print(f"[DEBUG] Novo: {item['name']}")
            
            affiliate = generate_affiliate_link(item["link"])
            message = f"🔥 <b>{item['name']}</b>\n\n💰 {item['price']}\n🔗 <a href='{affiliate}'>Ver Oferta</a>"
            
            if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
                send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message)
                count += 1
            
            new_seen.append(item["link"])

    if count > 0:
        save_db(new_seen)
        print(f"[DEBUG] {count} mensagens enviadas.")
    else:
        print("[DEBUG] Sem novidades.")

    print("--- FIM ---")

if __name__ == "__main__":
    main()