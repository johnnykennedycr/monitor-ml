import os
import re
import asyncio
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl
import requests
import sys
import logging

# Configura logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# --- CONFIGURAÇÕES ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
AFFILIATE_TAG = "tepa6477885"

# CANAL DE DESTINO
DEST_ENV = os.environ.get("DESTINATION_CHANNEL", "")
try:
    if DEST_ENV.startswith("-"):
        DESTINATION_CHANNEL = int(DEST_ENV)
    else:
        DESTINATION_CHANNEL = DEST_ENV
except:
    DESTINATION_CHANNEL = DEST_ENV

# LISTA DE CANAIS PERMITIDOS
ALLOWED_CHATS = [
    -1002026298205, # Promozone
]

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Sniper Bot V10 - MLB Cleaner Active"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- FUNÇÕES AUXILIARES ---
def get_all_links(message):
    urls = set()
    text = message.text or ""
    regex_links = re.findall(r'(https?://[^\s]+)', text)
    for url in regex_links:
        urls.add(url)
    if message.entities:
        for entity in message.entities:
            if isinstance(entity, MessageEntityTextUrl):
                urls.add(entity.url)
    return list(urls)

def extract_clean_ml_link(dirty_url):
    """
    1. Resolve o redirecionamento (/sec/).
    2. Procura pelo ID do produto (MLB...) na URL final.
    3. Retorna um link limpo apenas com o produto, removendo o concorrente.
    """
    final_url = dirty_url
    
    # 1. Resolve redirecionamento se necessário
    if "/sec/" in dirty_url or "mercado.li" in dirty_url:
        print(f"   🕵️ Resolvendo: {dirty_url[:30]}...", flush=True)
        try:
            session = requests.Session()
            session.headers.update({"User-Agent": "Mozilla/5.0"})
            resp = session.get(dirty_url, allow_redirects=True, timeout=10, stream=True)
            final_url = resp.url
        except:
            pass

    # 2. PROCURA PELO CÓDIGO MLB (A MÁGICA)
    # Padrões comuns: /p/MLB123, /MLB-123, ?item_id=MLB123
    mlb_match = re.search(r'(MLB-?\d+)', final_url)
    
    if mlb_match:
        clean_id = mlb_match.group(1).replace("-", "") # Padroniza para MLB12345
        clean_link = f"https://www.mercadolivre.com.br/p/{clean_id}"
        print(f"   ✨ Produto Identificado: {clean_id} (Link Limpo Gerado)", flush=True)
        return clean_link
    
    # Se não achou MLB (ex: link de categoria), retorna a URL resolvida limpa de parametros
    print("   ⚠️ ID MLB não encontrado, usando link resolvido genérico.", flush=True)
    return final_url.split("?")[0]

def convert_link(url):
    # Passa pela "Lavanderia" para tirar o Promozone da jogada
    clean_product_url = extract_clean_ml_link(url)
    
    # Verifica se continua sendo ML
    if "mercadolivre" not in clean_product_url and "mercado.li" not in clean_product_url:
        return url

    # Manda para a API Oficial (que vai aplicar o SEU Social Profile automaticamente se configurado no ML)
    api_url = "https://www.mercadolivre.com.br/afiliados/api/linkbuilder/meli"
    payload = {"tag": AFFILIATE_TAG, "urls": [clean_product_url]}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.post(api_url, json=payload, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if "links" in data and len(data["links"]) > 0:
                print("   💰 Link Afiliado Gerado com Sucesso!", flush=True)
                return data["links"][0]["url"]
    except Exception as e:
        print(f"   [ERRO API] {e}", flush=True)
    
    # Fallback
    return f"{clean_product_url}?matt_word={AFFILIATE_TAG}"

# --- ROBÔ TELEGRAM ---
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage())
async def handler(event):
    if event.chat_id not in ALLOWED_CHATS:
        return

    print(f"[NOVA MENSAGEM] Origem Aceita: {event.chat_id}", flush=True)

    urls = get_all_links(event.message)
    ml_urls = [u for u in urls if "mercadolivre.com" in u or "mercado.li" in u]
    
    if not ml_urls:
        return

    print(f"✅ OFERTA ML DETECTADA! ({len(ml_urls)} links)", flush=True)
    
    main_link = ml_urls[0]
    # Aqui ocorre a conversão com limpeza
    aff_link = convert_link(main_link)
    
    original_text = event.message.text or "Confira!"
    
    # Substitui links antigos por emoji
    for u in ml_urls:
        original_text = original_text.replace(u, "🔗")
    
    new_caption = (
        f"{original_text}\n\n"
        f"🔥 <b>OFERTA DETECTADA</b>\n"
        f"👇 <b>COMPRE AQUI:</b>\n"
        f"👉 {aff_link}"
    )
    
    try:
        print(f"   -> Enviando para: {DESTINATION_CHANNEL}", flush=True)
        if event.message.media:
            await client.send_file(DESTINATION_CHANNEL, event.message.media, caption=new_caption, parse_mode="html")
        else:
            await client.send_message(DESTINATION_CHANNEL, new_caption, link_preview=True, parse_mode="html")
        print("🚀 SUCESSO!", flush=True)
    except Exception as e:
        print(f"❌ ERRO AO POSTAR: {e}", flush=True)

# --- THREAD DE INICIALIZAÇÃO ---
def start_telethon_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def main_telethon_logic():
        print("--- TENTANDO CONECTAR (ASYNC) ---", flush=True)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                print("\n❌❌❌ ERRO: SESSÃO INVÁLIDA ❌❌❌", flush=True)
                return
            print("--- ✅ CONECTADO E MONITORANDO ---", flush=True)
            await client.run_until_disconnected()
        except Exception as e:
            print(f"❌ ERRO CRÍTICO NO CLIENTE: {e}", flush=True)

    loop.run_until_complete(main_telethon_logic())

t = Thread(target=start_telethon_thread)
t.daemon = True
t.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)