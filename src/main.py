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

# LISTA DE CANAIS PERMITIDOS (Ids Inteiros)
ALLOWED_CHATS = [
    -1002026298205, # Promozone
]

# CANAL DE DESTINO
DEST_ENV = os.environ.get("DESTINATION_CHANNEL", "")
try:
    if DEST_ENV.startswith("-"):
        DESTINATION_CHANNEL = int(DEST_ENV)
    else:
        DESTINATION_CHANNEL = DEST_ENV
except:
    DESTINATION_CHANNEL = DEST_ENV

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot Monitor ML - V7 (Debug Auth)"

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

def resolve_real_url(url):
    if "/sec/" not in url and "mercado.li" not in url:
        return url.split("?")[0]
    
    print(f"   🕵️ Resolvendo: {url[:30]}...", flush=True)
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        resp = session.get(url, allow_redirects=True, timeout=10, stream=True)
        final = resp.url.split("?")[0]
        print(f"   ✅ Real: {final[:40]}...", flush=True)
        return final
    except:
        return url

def convert_link(url):
    real_url = resolve_real_url(url)
    if "mercadolivre" not in real_url and "mercado.li" not in real_url:
        return url

    api_url = "https://www.mercadolivre.com.br/afiliados/api/linkbuilder/meli"
    payload = {"tag": AFFILIATE_TAG, "urls": [real_url]}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.post(api_url, json=payload, headers=headers, timeout=5)
        data = r.json()
        if "links" in data and len(data["links"]) > 0:
            return data["links"][0]["url"]
    except Exception as e:
        print(f"   [ERRO API] {e}", flush=True)
    
    return f"{real_url}?matt_word={AFFILIATE_TAG}"

# --- ROBÔ TELEGRAM ---
print("--- CARREGANDO CONFIGURAÇÕES ---", flush=True)
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
    aff_link = convert_link(main_link)
    
    original_text = event.message.text or "Confira!"
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

# --- THREAD DE INICIALIZAÇÃO BLINDADA ---
def start_telethon_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    print("--- TENTANDO CONECTAR AO TELEGRAM ---", flush=True)
    
    try:
        # Tenta conectar
        client.connect()
        
        # VERIFICA SE ESTÁ LOGADO
        if not client.is_user_authorized():
            print("\n❌❌❌ ERRO CRÍTICO: SESSÃO INVÁLIDA OU EXPIRADA ❌❌❌", flush=True)
            print("O bot está esperando login, mas não pode fazer isso no Render.", flush=True)
            print("SOLUÇÃO: Gere uma nova SESSION_STRING no seu PC e atualize no Render.\n", flush=True)
            return

        print("--- ✅ LOGIN SUCESSO! MONITORAMENTO ATIVO ---", flush=True)
        
        # Mantém rodando
        client.run_until_disconnected()
        
    except Exception as e:
        print(f"❌ ERRO FATAL NA THREAD DO BOT: {e}", flush=True)

# Inicia a thread IMEDIATAMENTE no escopo global
t = Thread(target=start_telethon_thread)
t.daemon = True
t.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)