import os
import re
import asyncio
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import requests

# --- CONFIGURAÇÕES ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# SEU CANAL DE DESTINO (Onde as ofertas vão cair)
# Pode ser username (@meucanal) ou ID (-100...)
DESTINATION_CHANNEL = os.environ.get("DESTINATION_CHANNEL")

# CANAIS PARA MONITORAR (Exemplos: Gatry, Pelando, etc)
# Você pode adicionar quantos quiser (usernames ou IDs)
SOURCE_CHANNELS = [
    '@promozoneoficial' 
    # Adicione aqui os canais que você quer "clonar"
]

# Seu ID de afiliado
AFFILIATE_TAG = "tepa6477885"

# --- FLASK (Para manter o Render acordado) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Sniper Bot Ativo!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- FUNÇÃO DE AFILIADO ---
def convert_link(url):
    """ Tenta converter o link para afiliado mantendo parâmetros ou limpando """
    # Se for link curto ou redirecionador, precisaríamos resolver primeiro.
    # Por simplicidade, vamos assumir que se tiver 'mercadolivre', montamos o link direto.
    
    # 1. Limpa o link de sujeira
    clean_url = url.split("?")[0]
    
    # 2. Gera link API oficial (reutilizando sua lógica)
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
    
    # Fallback simples
    return f"{clean_url}?matt_word={AFFILIATE_TAG}"

# --- ROBÔ TELEGRAM ---
print("Conectando ao Telegram...")
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handler(event):
    text = event.message.text or ""
    
    # Filtro: Só queremos Mercado Livre
    if "mercadolivre.com" in text or "mercado.li" in text:
        print(f"🎯 Oferta detectada de: {event.chat_id}")
        
        # 1. Encontrar o Link na mensagem
        # Regex para achar urls
        url_regex = r'(https?://[^\s]+)'
        urls = re.findall(url_regex, text)
        
        new_text = text
        link_found = False
        
        for url in urls:
            if "mercadolivre" in url or "mercado.li" in url:
                # 2. Gerar Link Afiliado
                aff_link = convert_link(url)
                
                # 3. Substituir no texto original
                # Substituimos o link original pelo seu
                new_text = new_text.replace(url, aff_link)
                link_found = True
        
        if link_found:
            try:
                # 4. Enviar para o seu canal
                # Se tiver foto/video, manda o arquivo junto
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
                print("✅ Clonado com sucesso!")
            except Exception as e:
                print(f"Erro ao clonar: {e}")

# --- INICIALIZAÇÃO ---
if __name__ == '__main__':
    # Roda o site em background
    t = Thread(target=run_web)
    t.start()
    
    # Roda o cliente do Telegram
    with client:
        client.run_until_disconnected()