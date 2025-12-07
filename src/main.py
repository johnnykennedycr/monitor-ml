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
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# Configura logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# --- CONFIGURAÇÕES ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
AFFILIATE_TAG = "tepa6477885"
MY_SOCIAL_HANDLE = "tepa6477885"

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
    return "🤖 Sniper Bot V13 - Surgical URL Clean"

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

def hijack_social_url(url):
    """
    Substitui cirurgicamente o dono da loja social e o parâmetro de afiliado.
    """
    try:
        parsed = urlparse(url)
        
        # 1. Troca o caminho (Path) -> /social/novo_dono
        path_parts = parsed.path.split('/')
        new_path_parts = []
        for part in path_parts:
            # Se for o nome do concorrente (logo depois de social), troca
            if 'social' in new_path_parts:
                new_path_parts.append(MY_SOCIAL_HANDLE)
            else:
                new_path_parts.append(part)
        
        # Reconstrói o caminho se a lógica acima falhar (regex fallback)
        new_path = "/".join(new_path_parts)
        if MY_SOCIAL_HANDLE not in new_path:
             new_path = re.sub(r'/social/[^/]+', f'/social/{MY_SOCIAL_HANDLE}', parsed.path)

        # 2. Troca os parâmetros (Query) -> matt_word=minha_tag
        query_params = parse_qs(parsed.query)
        query_params['matt_word'] = [AFFILIATE_TAG] # Força sua tag
        
        # Remove ferramentas de rastreio de terceiros se quiser
        if 'matt_tool' in query_params:
            del query_params['matt_tool']

        new_query = urlencode(query_params, doseq=True)
        
        # 3. Reconstrói a URL final
        new_url = urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, new_query, parsed.fragment))
        return new_url
        
    except Exception as e:
        print(f"   ⚠️ Erro no Hijack: {e}. Usando fallback simples.", flush=True)
        # Fallback bruto se o parser falhar
        return f"https://www.mercadolivre.com.br/social/{MY_SOCIAL_HANDLE}?matt_word={AFFILIATE_TAG}"

def extract_clean_ml_link(dirty_url):
    final_url = dirty_url
    
    # 1. Resolve redirecionamentos
    if "/sec/" in dirty_url or "mercado.li" in dirty_url or "bit.ly" in dirty_url:
        print(f"   🕵️ Resolvendo: {dirty_url}...", flush=True)
        try:
            session = requests.Session()
            session.headers.update({"User-Agent": "Mozilla/5.0"})
            resp = session.get(dirty_url, allow_redirects=True, timeout=10, stream=True)
            final_url = resp.url
        except:
            pass

    # 2. TENTA EXTRAIR ID DO PRODUTO (Prioridade Máxima)
    match = re.search(r'(MLB-?\d+)', final_url)
    if match:
        clean_id = match.group(1).replace("-", "")
        clean_link = f"https://www.mercadolivre.com.br/p/{clean_id}"
        print(f"   ✨ Produto MLB encontrado: {clean_id}", flush=True)
        return clean_link
    
    # 3. FALLBACK: SEQUESTRO DE LINK SOCIAL
    if "/social/" in final_url:
        print("   🔄 Link Social detectado. Realizando Hijack...", flush=True)
        new_social = hijack_social_url(final_url)
        print(f"   ✅ URL Social Dominada: {new_social}", flush=True)
        return new_social

    # 4. Fallback final
    return final_url.split("?")[0]

def convert_link(url):
    clean_url = extract_clean_ml_link(url)
    
    if "mercadolivre" not in clean_url and "mercado.li" not in clean_url:
        return url

    # Se já fizemos o hijack social, retorna direto
    if "/social/" in clean_url and MY_SOCIAL_HANDLE in clean_url:
        return clean_url

    # Se é link de produto, tenta API oficial
    api_url = "https://www.mercadolivre.com.br/afiliados/api/linkbuilder/meli"
    payload = {"tag": AFFILIATE_TAG, "urls": [clean_url]}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.post(api_url, json=payload, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "links" in data and len(data["links"]) > 0:
                print("   💰 Link Afiliado API Gerado!", flush=True)
                return data["links"][0]["url"]
    except Exception as e:
        print(f"   [ERRO API] {e}", flush=True)
    
    return f"{clean_url}?matt_word={AFFILIATE_TAG}"

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
    aff_link = convert_link(main_link)
    
    # Limpa texto original
    original_text = event.message.text or "Confira!"
    for u in ml_urls:
        original_text = original_text.replace(u, "") # Remove a URL antiga do texto
    
    # NOVA LEGENDA COM LINK CLICÁVEL (HTML)
    new_caption = (
        f"{original_text.strip()}\n\n"
        f"🔥 <b>OFERTA DETECTADA</b>\n"
        f"👇 <b>CLIQUE PARA COMPRAR:</b>\n"
        f"➡️ <a href='{aff_link}'>ACESSAR OFERTA NO SITE</a>"
    )
    
    try:
        print(f"   -> Enviando...", flush=True)
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