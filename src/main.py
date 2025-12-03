import os
import json
import requests
import sys

# Importa seus módulos
from scraper import get_best_sellers
from affiliate import generate_affiliate_link # Sua função

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
    """ Envia uma FOTO com legenda """
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
    except Exception as e:
        print(f"[ERRO] Falha ao enviar foto: {e}")
        return None

def send_telegram_message(token, chat_id, text):
    """ Fallback: Envia apenas TEXTO se não tiver foto """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    requests.post(url, json=payload)

def main():
    print("--- INICIANDO BOT ---")
    
    seen_links = load_db()
    print(f"[DEBUG] Histórico: {len(seen_links)} itens já enviados.")

    # 1. Busca produtos (com imagem)
    products = get_best_sellers()
    
    if not products:
        print("[DEBUG] Nenhum produto encontrado agora.")
        return

    new_seen = seen_links.copy()
    count = 0

    for item in products:
        # Verifica duplicidade
        if item["id"] in seen_links:
            continue

        print(f"[DEBUG] Processando: {item['name']}")
        
        # 2. Gera seu link de afiliado
        affiliate_url = generate_affiliate_link(item["link"])
        
        # Monta a legenda (Caption)
        caption = (
            f"🔥 <b>{item['name']}</b>\n\n"
            f"💰 <b>{item['price']}</b>\n\n"
            f"👇 <b>Link da Oferta:</b>\n"
            f"<a href='{affiliate_url}'>➡️ VER NO MERCADO LIVRE</a>"
        )

        # 3. Envia para o Telegram
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            # Tenta enviar com FOTO se tiver url da imagem
            if item.get("image_url"):
                resp = send_telegram_photo(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, item["image_url"], caption)
                # Se der erro (ex: url da imagem inválida), tenta enviar só texto
                if not resp or not resp.get("ok"):
                    print("[DEBUG] Erro ao enviar foto, tentando apenas texto...")
                    send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, caption)
            else:
                # Se não tem imagem, manda texto direto
                send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, caption)
            
            count += 1
            new_seen.append(item["id"])
        else:
            print("[DEBUG] Modo teste (Sem Token Telegram):")
            print(caption)
            new_seen.append(item["id"])

    if count > 0:
        save_db(new_seen)
        print(f"[DEBUG] {count} novas ofertas enviadas com sucesso!")
    else:
        print("[DEBUG] Nenhuma novidade para enviar.")

if __name__ == "__main__":
    main()