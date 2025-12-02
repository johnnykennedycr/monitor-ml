import os
import sys
import json
from scraper import get_best_sellers
from affiliate import generate_affiliate_link
from notifier import send_telegram

# Configura path e diretórios
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, "database.json")

# Carrega variáveis de ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def load_db():
    """Carrega o banco de dados. Cria um novo se não existir ou estiver corrompido/vazio."""
    if not os.path.exists(DATABASE_FILE):
        print("[DEBUG] Database não existe. Criando novo.")
        return []
    
    # VERIFICAÇÃO CRÍTICA: Se o arquivo existe mas tem 0 bytes (vazio)
    if os.stat(DATABASE_FILE).st_size == 0:
        print("[DEBUG] Database encontrado mas está vazio. Resetando.")
        return []

    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("[DEBUG] Erro de JSON (arquivo corrompido). Resetando database.")
        return []
    except Exception as e:
        print(f"[DEBUG] Erro ao ler database: {e}")
        return []

def save_db(data):
    try:
        with open(DATABASE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print("[DEBUG] Database salvo com sucesso.")
    except Exception as e:
        print(f"[DEBUG] Erro ao salvar database: {e}")

def main():
    print("--- INICIANDO EXECUÇÃO ---")
    
    # 1. Carregar produtos já enviados
    seen_links = load_db()
    print(f"[DEBUG] Total de links já enviados no histórico: {len(seen_links)}")

    # 2. Buscar produtos na API (usando o scraper corrigido)
    products = get_best_sellers()
    
    if not products:
        print("[DEBUG] Nenhum produto retornado pela API. Encerrando.")
        return

    # Lista para salvar novos envios
    # (Começamos com uma cópia do que já tínhamos para não perder histórico)
    updated_seen_links = seen_links.copy()
    items_sent = 0

    # 3. Processar produtos
    for item in products:
        # Verifica se o link JÁ existe na lista de enviados
        if item["link"] in seen_links:
            continue # Pula este produto
            
        print(f"[DEBUG] Novo produto encontrado: {item['name']}")

        # Gera link (ajuste conforme sua lógica no affiliate.py)
        affiliate_url = generate_affiliate_link(item["link"])
        
        # Monta mensagem
        message = (
            f"🔥 <b>{item['name']}</b>\n\n"
            f"💰 <b>{item.get('price', '')}</b>\n\n"
            f"🔗 <a href='{affiliate_url}'>Ver Oferta</a>"
        )

        # Envia Telegram
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            try:
                send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message)
                items_sent += 1
                # Adiciona à lista de vistos APENAS se enviou com sucesso
                updated_seen_links.append(item["link"])
            except Exception as e:
                print(f"[DEBUG] Falha ao enviar Telegram: {e}")
        else:
            print("[DEBUG] Modo teste (sem token Telegram):", item['name'])
            updated_seen_links.append(item["link"])

    # 4. Salvar database apenas se houve novidades
    if items_sent > 0 or len(updated_seen_links) > len(seen_links):
        save_db(updated_seen_links)
        print(f"[DEBUG] {items_sent} novas mensagens enviadas.")
    else:
        print("[DEBUG] Nenhuma novidade para enviar.")

    print("--- FIM DA EXECUÇÃO ---")

if __name__ == "__main__":
    main()