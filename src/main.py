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

# Configura logs para aparecerem no Render (STDOUT)
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

# CANAIS PARA MONITORAR
SOURCE_CHANNELS = [
    '@promozoneoficial',
    'me' # Para testes
]

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Sniper Bot V4 - Rodando com Gunicorn!"

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

def convert_link(url):
    print(f"   ⚙️ Convertendo: {url[:40]}...", flush=True)
    clean_url = url.split("?")[0]
    
    if "mercadolivre" not in clean_url and "mercado.li" not in clean_url:
        return url

    api_url = "https://www.mercadolivre.com.br/afiliados/api/linkbuilder/meli"
    payload = {"tag": AFFILIATE_TAG, "urls": [clean_url]}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.post(api_url, json=payload, headers=headers, timeout=5)
        data = r.json()
        if "links" in data and len(data["links"]) > 0:
            return data["links"][0]["url"]
    except Exception as e:
        print(f"   [ERRO API] {e}", flush=True)
    
    return f"{clean_url}?matt_word={AFFILIATE_TAG}"

# --- ROBÔ TELEGRAM ---
# Inicializa o cliente, mas não conecta ainda
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handler(event):
    try:
        chat = await event.get_chat()
        chat_title = chat.title if hasattr(chat, 'title') else "Private/Me"
    except:
        chat_title = str(event.chat_id)
        
    print(f"[NOVA MENSAGEM] Origem: {chat_title}", flush=True)

    urls = get_all_links(event.message)
    ml_urls = [u for u in urls if "mercadolivre.com" in u or "mercado.li" in u]
    
    if not ml_urls:
        return

    print(f"✅ OFERTA ML DETECTADA! ({len(ml_urls)} links)", flush=True)
    
    main_link = ml_urls[0]
    aff_link = convert_link(main_link)
    
    original_text = event.message.text or "Confira esta oferta!"
    
    # Remove links antigos visualmente
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

# --- INICIALIZAÇÃO CORRIGIDA PARA GUNICORN ---
def start_telethon_thread():
    """Roda o Telethon em um loop de eventos isolado na thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    print("--- CONECTANDO TELETHON ---", flush=True)
    
    # Conecta e Mantém rodando
    with client:
        # Verificação inicial de canais
        print("--- VERIFICANDO LISTA DE CANAIS (STARTUP) ---", flush=True)
        async def check():
            async for dialog in client.iter_dialogs(limit=15):
                print(f"   - Vejo: {dialog.name} (ID: {dialog.id})", flush=True)
        client.loop.run_until_complete(check())
        print("--- MONITORAMENTO ATIVO ---", flush=True)
        
        client.run_until_disconnected()

# DISPARO IMEDIATO (FORA DO IF MAIN)
# Isso garante que o Gunicorn execute a thread assim que carregar o arquivo
t = Thread(target=start_telethon_thread)
t.daemon = True # Importante para não travar o shutdown
t.start()

if __name__ == "__main__":
    # Apenas para teste local
    app.run(host='0.0.0.0', port=8080)