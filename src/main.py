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

# CANAIS PARA MONITORAR
SOURCE_CHANNELS = [
    '-1002026298205',
    'me'
]

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Sniper Bot V5 - Link Resolver Ativo"

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

def resolve_real_url(url):
    """
    Segue o redirecionamento dos links /sec/ ou curtos para achar o produto real.
    """
    # Se não for link curto, não precisa resolver (economiza tempo)
    if "/sec/" not in url and "mercado.li" not in url:
        return url.split("?")[0] # Só limpa parâmetros

    print(f"   🕵️ Resolvendo redirecionamento: {url[:30]}...", flush=True)
    try:
        # Fazemos uma requisição HEAD ou GET permitindo redirects
        # Usamos stream=True para não baixar o HTML inteiro, só ver a URL final
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        resp = session.get(url, allow_redirects=True, timeout=10, stream=True)
        
        final_url = resp.url
        # Limpa parâmetros de rastreio do concorrente (tudo depois de ?)
        clean_final = final_url.split("?")[0]
        
        print(f"   ✅ Link Real Descoberto: {clean_final[:40]}...", flush=True)
        return clean_final
    except Exception as e:
        print(f"   ⚠️ Falha ao resolver link: {e}", flush=True)
        return url

def convert_link(url):
    # 1. Primeiro descobre o link real do produto (Tira o Promozone da jogada)
    real_product_url = resolve_real_url(url)
    
    # 2. Verifica se continua sendo ML
    if "mercadolivre" not in real_product_url and "mercado.li" not in real_product_url:
        return url

    # 3. Manda para a API Oficial
    api_url = "https://www.mercadolivre.com.br/afiliados/api/linkbuilder/meli"
    payload = {"tag": AFFILIATE_TAG, "urls": [real_product_url]}
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
    
    # Fallback: Adiciona tag manualmente no link limpo
    return f"{real_product_url}?matt_word={AFFILIATE_TAG}"

# --- ROBÔ TELEGRAM ---
print("--- INICIANDO CLIENTE ---", flush=True)
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
    
    # Pega o primeiro link, resolve e afilia
    main_link = ml_urls[0]
    aff_link = convert_link(main_link)
    
    original_text = event.message.text or "Confira esta oferta!"
    
    # Remove visualmente os links antigos do texto
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
            await client.send_file(
                DESTINATION_CHANNEL, 
                event.message.media, 
                caption=new_caption, 
                parse_mode="html"
            )
        else:
            await client.send_message(
                DESTINATION_CHANNEL, 
                new_caption, 
                link_preview=True, 
                parse_mode="html"
            )
        print("🚀 SUCESSO!", flush=True)
    except Exception as e:
        print(f"❌ ERRO AO POSTAR: {e}", flush=True)

# --- STARTUP ---
async def startup_check():
    print("--- VERIFICANDO CANAIS ---")
    async for dialog in client.iter_dialogs(limit=15):
        print(f"   - Vejo: {dialog.name} (ID: {dialog.id})")

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    
    print("--- CONECTANDO... ---", flush=True)
    with client:
        client.loop.run_until_complete(startup_check())
        print("--- MONITORAMENTO ATIVO ---", flush=True)
        client.run_until_disconnected()