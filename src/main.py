import os
import re
import asyncio
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import requests
import sys
import logging

# Configura logs para aparecerem no Render
logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO)

# --- CONFIGURAÇÕES ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# SEU ID DE AFILIADO
AFFILIATE_TAG = "tepa6477885"

# TRATAMENTO DO CANAL DE DESTINO (Converte ID numérico se necessário)
DEST_ENV = os.environ.get("DESTINATION_CHANNEL", "")
try:
    if DEST_ENV.startswith("-"):
        DESTINATION_CHANNEL = int(DEST_ENV) # Converte "-100..." para número
    else:
        DESTINATION_CHANNEL = DEST_ENV # Mantém "@canal" como texto
except:
    DESTINATION_CHANNEL = DEST_ENV

# CANAIS PARA MONITORAR
SOURCE_CHANNELS = [
    '@promozoneoficial',  # O canal que você pediu
    'me'                  # 'me' = Suas Mensagens Salvas (PARA TESTE IMEDIATO)
]

# --- FLASK (Para manter o Render acordado) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Sniper Bot Monitorando @promozoneoficial"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- FUNÇÃO DE AFILIADO ---
def convert_link(url):
    """ Tenta converter o link para afiliado mantendo parâmetros ou limpando """
    print(f"   -> Gerando link afiliado para: {url[:30]}...", flush=True)
    
    clean_url = url.split("?")[0]
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
    
    # Fallback simples
    return f"{clean_url}?matt_word={AFFILIATE_TAG}"

# --- ROBÔ TELEGRAM ---
print("--- INICIANDO CLIENTE TELETHON ---", flush=True)
try:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
except Exception as e:
    print(f"ERRO CRÍTICO AO INICIAR CLIENTE: {e}", flush=True)

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handler(event):
    # Log para saber que o bot está ouvindo
    try:
        chat_name = "Desconhecido"
        chat = await event.get_chat()
        chat_name = chat.title if hasattr(chat, 'title') else "Private/Me"
    except:
        chat_name = str(event.chat_id)

    print(f"[MSG RECEBIDA] Fonte: {chat_name} | Texto: {event.text[:30]}...", flush=True)

    text = event.message.text or ""
    
    # Filtro: Só queremos Mercado Livre
    if "mercadolivre.com" in text or "mercado.li" in text:
        print(f"✅ OFERTA ML DETECTADA!", flush=True)
        
        # 1. Encontrar o Link na mensagem
        url_regex = r'(https?://[^\s]+)'
        urls = re.findall(url_regex, text)
        
        new_text = text
        link_found = False
        
        for url in urls:
            if "mercadolivre" in url or "mercado.li" in url:
                # 2. Gerar Link Afiliado
                aff_link = convert_link(url)
                
                # 3. Substituir no texto original
                new_text = new_text.replace(url, aff_link)
                link_found = True
        
        if link_found:
            try:
                print(f"   -> Enviando para canal de destino: {DESTINATION_CHANNEL}", flush=True)
                
                # 4. Enviar para o seu canal
                if event.message.media:
                    await client.send_file(
                        DESTINATION_CHANNEL, 
                        event.message.media, 
                        caption=new_text
                    )
                else:
                    await client.send_message(
                        DESTINATION_CHANNEL, 
                        new_text, 
                        link_preview=False
                    )
                print("🚀 CLONAGEM SUCESSO!", flush=True)
            except Exception as e:
                print(f"❌ ERRO AO POSTAR: {e}", flush=True)
                print("DICA: Verifique se o ID do canal de destino está correto e se você é Admin dele.")

# --- INICIALIZAÇÃO ---
if __name__ == '__main__':
    # Roda o site em background
    t = Thread(target=run_web)
    t.start()
    
    # Roda o cliente do Telegram
    print("--- AGUARDANDO MENSAGENS ---", flush=True)
    with client:
        client.run_until_disconnected()