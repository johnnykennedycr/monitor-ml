import json
import os
from .scraper import get_best_sellers
from .affiliate import generate_affiliate_link
from .notifier import send_telegram

print("[DEBUG] Iniciando script...")

# Debug das variáveis de ambiente
print("[DEBUG] TELEGRAM_TOKEN está setado?", "sim" if os.getenv("TELEGRAM_TOKEN") else "não")
print("[DEBUG] TELEGRAM_CHAT_ID:", os.getenv("TELEGRAM_CHAT_ID"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, "database.json")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def load_db():
    if not os.path.exists(DATABASE_FILE):
        print("[DEBUG] Database não existe ainda, iniciando vazio.")
        return []
    try:
        with open(DATABASE_FILE, "r") as f:
            print("[DEBUG] Database carregado.")
            return json.load(f)
    except Exception as e:
        print("[DEBUG] Erro ao ler database:", e)
        return []


def save_db(data):
    with open(DATABASE_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print("[DEBUG] Database salvo.")


def main():
    print("[DEBUG] Executando main()...")

    seen = load_db()
    print("[DEBUG] Links já enviados:", len(seen))

    products = get_best_sellers()
    print("[DEBUG] Produtos coletados:", len(products))

    new_seen = seen.copy()

    for item in products:
        print("[DEBUG] Avaliando produto:", item["name"])

        if item["link"] not in seen:
            print("[DEBUG] Novo produto detectado! Gerando link afiliado...")

            affiliate = generate_affiliate_link(item["link"])
            message = f"🔥 <b>{item['name']}</b>\n\n🔗 {affiliate}"

            print("[DEBUG] Enviando mensagem ao Telegram:", message)

            # Captura a resposta da API para debug
            response = send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message)
            print("[DEBUG] Resposta da API Telegram:", response)

            new_seen.append(item["link"])
        else:
            print("[DEBUG] Já enviado anteriormente, ignorando.")

    save_db(new_seen)
    print("[DEBUG] Execução finalizada.")


if __name__ == "__main__":
    main()
