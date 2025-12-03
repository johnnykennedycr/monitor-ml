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

# --- LISTA DE CANAIS PERMITIDOS (Ids Inteiros) ---
# Aqui colocamos o ID do Promozone como NÚMERO (sem aspas)
ALLOWED_CHATS = [
    -1002026298205, 
]

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Sniper Bot V6 - Filtro Interno Ativo"

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
    # Se não for link curto, não precisa resolver
    if "/sec/" not in url and "mercado.li" not in url:
        return url.split("?")[0]

    print(f"   🕵️ Resolvendo redirecionamento: {url[:30]}...", flush=True)
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        resp = session.get(url, allow_redirects=True, timeout=10, stream=True)
        final_url = resp.url
        clean_final = final_url.split("?")[0]
        print(f"   ✅ Link Real Descoberto: {clean_final[:40]}...", flush=True)
        return clean_final
    except Exception as e:
        print(f"   ⚠️ Falha ao resolver link: {e}", flush=True)
        return url

def convert_link(url):
    # 1. Primeiro descobre o link real
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
    
    return f"{real_product_url}?matt_word={AFFILIATE_TAG}"

# --- ROBÔ TELEGRAM ---
print("--- INICIANDO CLIENTE ---", flush=True)
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# REMOVEMOS O FILTRO DO DECORATOR PARA EVITAR O ERRO DE STARTUP
@client.on(events.NewMessage())
async def handler(event):
    # --- FILTRO MANUAL ---
    # Só processa se o ID do chat estiver na lista ALLOWED_CHATS
    # Nota: Se quiser testar em 'Saved Messages', o ID será positivo (seu ID de usuário)
    if event.chat_id not in ALLOWED_CHATS:
        # Se quiser descobrir seu ID pessoal para testes, descomente a linha abaixo:
        # print(f"Ignorando mensagem de: {event.chat_id}", flush=True)
        return

    print(f"[NOVA MENSAGEM] Origem Aceita: {event.chat_id}", flush=True)

    urls = get_all_links(event.message)
    ml_urls = [u for u in urls if "mercadolivre.com" in u or "mercado.li" in u]
    
    if not ml_urls:
        return

    print(f"✅ OFERTA ML DETECTADA! ({len(ml_urls)} links)", flush=True)
    
    main_link = ml_urls[0]
    aff_link = convert_link(main_link)
    
    original_text = event.message.text or "Confira esta oferta!"
    
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

# --- STARTUP CORRIGIDO ---
def start_telethon_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    with client:
        print("--- MONITORAMENTO ATIVO (FILTRO MANUAL) ---", flush=True)
        client.run_until_disconnected()

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    
    # Inicia a thread do Telethon
    t2 = Thread(target=start_telethon_thread)
    t2.daemon = True
    t2.start()
    
    # Mantém o script rodando
    t.join()