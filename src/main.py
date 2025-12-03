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
logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO)

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

# --- IMPORTANTE: LISTA DE CANAIS ---
# Por enquanto deixe vazio ou só com 'me'.
# O código abaixo vai te dizer qual ID colocar aqui.
SOURCE_CHANNELS = ['me'] 

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Scanner de IDs Ativo!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- FUNÇÕES AUXILIARES ---
def get_all_links(message):
    urls = set()
    text = message.text or ""
    # Regex ajustado para pegar mercadolivre.com (sem br) e /sec/
    regex_links = re.findall(r'(https?://[^\s]+)', text)
    for url in regex_links:
        urls.add(url)
    if message.entities:
        for entity in message.entities:
            if isinstance(entity, MessageEntityTextUrl):
                urls.add(entity.url)
    return list(urls)

def convert_link(url):
    print(f"   ⚙️ Convertendo: {url[:30]}...", flush=True)
    clean_url = url.split("?")[0]
    
    # Validação mais flexível (aceita .com e .com.br)
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
    except:
        pass
    
    return f"{clean_url}?matt_word={AFFILIATE_TAG}"

# --- ROBÔ TELEGRAM ---
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- SCANNER DE CANAIS (A MÁGICA) ---
async def print_dialogs():
    print("\n" + "="*40, flush=True)
    print("📋 LISTA DE CANAIS QUE ESTOU VENDO:", flush=True)
    print("="*40, flush=True)
    
    # Itera sobre os últimos 20 chats/canais
    async for dialog in client.iter_dialogs(limit=30):
        print(f"📌 Nome: {dialog.name} | ID: {dialog.id}", flush=True)
        
    print("="*40, flush=True)
    print("⚠️ COPIE O ID DO CANAL 'PROMOZONE' E COLOQUE NO CÓDIGO!\n", flush=True)

# Listener Genérico (Ouve tudo por enquanto para testar)
@client.on(events.NewMessage())
async def handler(event):
    # Loga de onde veio a mensagem
    print(f"[NOVA MENSAGEM] Chat ID: {event.chat_id} | Texto: {event.text[:20]}...", flush=True)
    
    # Se o ID não estiver na lista (que vamos configurar depois), ignora
    # Mas como estamos debugando, vamos processar se for ML
    
    urls = get_all_links(event.message)
    ml_urls = [u for u in urls if "mercadolivre" in u or "mercado.li" in u]
    
    if ml_urls:
        print(f"✅ LINK ML ENCONTRADO NO CHAT {event.chat_id}", flush=True)
        # (A lógica de envio fica pausada até pegarmos o ID certo para não fazer spam)

# --- START ---
if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    
    print("--- CONECTANDO... ---", flush=True)
    with client:
        # RODA O SCANNER AO INICIAR
        client.loop.run_until_complete(print_dialogs())
        client.run_until_disconnected()