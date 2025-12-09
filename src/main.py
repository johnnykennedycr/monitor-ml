import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from flask import Flask, request, Response
from threading import Thread
import time
import logging
import requests
import re
import cloudscraper
from bs4 import BeautifulSoup

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(level=logging.INFO)

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
AFFILIATE_TAG = "tepa6477885"
RENDER_URL = "https://monitor-ml.onrender.com" 

GROUPS = {
    "geral": os.getenv("GROUP_GERAL"),
    "mae": os.getenv("GROUP_MAE"),
    "util": os.getenv("GROUP_UTIL")
}

user_steps = {}

# --- CRIAÇÃO DO BOT (MODO SÍNCRONO) ---
# threaded=False é essencial para Webhooks no Render/Gunicorn
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- FUNÇÕES UTILITÁRIAS ---
def get_ml_data(url):
    print(f"🔎 Iniciando Scraping: {url}", flush=True)
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'mobile': False})
    data = {"title": "Oferta Imperdível", "price": None}
    try:
        resp = scraper.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.find("h1", class_="ui-pdp-title")
        if title: data["title"] = title.text.strip()
        price_meta = soup.find("meta", property="product:price:amount")
        if price_meta: 
            try:
                val = float(price_meta["content"])
                data["price"] = f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except: pass
        print(f"✅ Scraping concluído: {data}", flush=True)
        return data
    except Exception as e:
        print(f"❌ Erro Scraping: {e}", flush=True)
        return data

def generate_affiliate_link(url, tag):
    final_url = url
    # 1. Resolve redirecionamento
    if "/sec/" in url or "mercado.li" in url or "bit.ly" in url:
        try:
            resp = requests.get(url, allow_redirects=True, timeout=10)
            final_url = resp.url
        except: pass

    # 2. Busca ID MLB
    clean_link = final_url.split("?")[0]
    match = re.search(r'(MLB-?\d+)', final_url)
    if match:
        clean_id = match.group(1).replace("-", "")
        clean_link = f"https://www.mercadolivre.com.br/p/{clean_id}"
    
    # 3. API
    api_url = "https://www.mercadolivre.com.br/afiliados/api/linkbuilder/meli"
    payload = {"tag": tag, "urls": [clean_link]}
    try:
        r = requests.post(api_url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            js = r.json()
            if "links" in js and js["links"]: return js["links"][0]["url"]
    except: pass
    
    return f"{clean_link}?matt_word={tag}"

# --- ROTAS FLASK ---
@app.route('/')
def home():
    return "🤖 Bot Síncrono Ativo!"

@app.route(f'/{TOKEN}', methods=['POST'])
def process_webhook():
    try:
        # Recebe e processa na mesma thread (Síncrono)
        json_string = request.get_data().decode('utf-8')
        print("📨 Webhook recebeu dados...", flush=True)
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return Response('OK', status=200)
    except Exception as e:
        print(f"❌ Erro Crítico no Webhook: {e}", flush=True)
        return Response('Error', status=500)

# --- HANDLERS DO BOT ---

@bot.message_handler(commands=['ids', 'start'])
def command_ids(message):
    print(f"⚡ Comando recebido de {message.from_user.id}", flush=True)
    bot.reply_to(message, f"🆔 Seu ID: `{message.from_user.id}`", parse_mode="Markdown")

# HANDLER PRINCIPAL - Aceita Texto
@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
    user_id = str(message.from_user.id)
    print(f"⚡ Mensagem de Texto de {user_id}: {message.text}", flush=True)
    
    # Verificação de Admin com Log
    if ADMIN_ID:
        # Limpa espaços em branco para evitar erro de string
        env_admin = str(ADMIN_ID).strip()
        msg_admin = user_id.strip()
        
        if msg_admin != env_admin:
            print(f"⛔ Bloqueado: {msg_admin} != {env_admin}", flush=True)
            bot.reply_to(message, f"⛔ Acesso Negado.\nSeu ID: `{msg_admin}`\nConfigurado: `{env_admin}`", parse_mode="Markdown")
            return
    
    text = message.text.strip()
    
    if "mercadolivre" in text or "mercado.li" in text:
        msg = bot.reply_to(message, "⏳ **Extraindo dados... Aguarde.**", parse_mode="Markdown")
        try:
            product_data = get_ml_data(text)
            aff_link = generate_affiliate_link(text, AFFILIATE_TAG)
            
            user_steps[message.chat.id] = {
                "title": product_data.get("title", "Oferta"),
                "original_price": product_data.get("price"),
                "final_link": aff_link,
                "raw_link": text
            }
            
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("📢 Geral", callback_data="grp_geral"), InlineKeyboardButton("👶 Mãe", callback_data="grp_mae"))
            markup.row(InlineKeyboardButton("🏠 Util", callback_data="grp_util"), InlineKeyboardButton("❌ Cancelar", callback_data="cancel"))
            
            bot.edit_message_text(
                f"📦 **{product_data.get('title')}**\n"
                f"💰 {product_data.get('price')}\n\n"
                "**Para qual grupo enviar?** 👇",
                chat_id=message.chat.id,
                message_id=msg.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"❌ Erro logica: {e}", flush=True)
            bot.edit_message_text(f"❌ Erro: {e}", chat_id=message.chat.id, message_id=msg.message_id)
    else:
        print("⚠️ Texto ignorado (não é link ML)", flush=True)
        bot.reply_to(message, "Mande um link do Mercado Livre.")

# HANDLER DE CALLBACKS (Botões)
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    print(f"⚡ Callback: {call.data}", flush=True)
    
    if call.data == "cancel":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        user_steps.pop(call.message.chat.id, None)
        return

    if call.data.startswith("grp_"):
        grp = call.data.replace("grp_", "")
        target = GROUPS.get(grp)
        if not target:
            bot.answer_callback_query(call.id, "❌ ID do grupo não configurado!")
            return
        
        user_steps[call.message.chat.id]["target_id"] = target
        msg = bot.edit_message_text("📝 **Headline?** (Digite ou /skip)", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        bot.register_next_step_handler(msg, step_message)

def step_message(message):
    txt = message.text
    if txt == "/skip": txt = ""
    if message.chat.id in user_steps:
        user_steps[message.chat.id]["custom_msg"] = txt
        msg = bot.reply_to(message, "🎟 **Cupom?** (Digite ou /skip)")
        bot.register_next_step_handler(msg, step_coupon)

def step_coupon(message):
    txt = message.text
    if txt == "/skip": txt = None
    if message.chat.id in user_steps:
        user_steps[message.chat.id]["coupon"] = txt
        curr = user_steps[message.chat.id].get("original_price", "N/A")
        msg = bot.reply_to(message, f"💰 **Preço?** (Atual: {curr})\nDigite novo ou /skip")
        bot.register_next_step_handler(msg, step_price)

def step_price(message):
    txt = message.text
    if txt != "/skip" and message.chat.id in user_steps:
        user_steps[message.chat.id]["original_price"] = txt
    msg = bot.reply_to(message, "🎥 **Vídeo?** (Envie ou /skip)")
    bot.register_next_step_handler(message, step_video)

def step_video(message):
    data = user_steps.get(message.chat.id)
    if not data: return

    headline = data.get('custom_msg', '').upper()
    title = f"❄️ {data['title']}"
    price = f"🔥 {data['original_price']}" if data.get('original_price') else "🔥 VER PREÇO NO SITE"
    coupon = f"\n🎟 CUPOM: {data['coupon']}" if data.get('coupon') else ""
    link = f"\n🔗 {data['final_link']}"
    
    final_text = f"{headline}\n\n{title}\n\n{price}{coupon}\n{link}"
    target = data['target_id']
    
    try:
        if message.content_type == 'video':
            bot.send_video(target, message.video.file_id, caption=final_text)
        elif message.content_type == 'photo':
            bot.send_photo(target, message.photo[-1].file_id, caption=final_text)
        else:
            bot.send_message(target, final_text, disable_web_page_preview=False)
        bot.reply_to(message, "✅ **Postado!**")
    except Exception as e:
        bot.reply_to(message, f"❌ Erro envio: {e}")
    
    user_steps.pop(message.chat.id, None)

# --- STARTUP ---
def set_webhook():
    time.sleep(3)
    bot.remove_webhook()
    time.sleep(1)
    s = bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
    print(f"✅ Webhook Configurado: {s}", flush=True)

t = Thread(target=set_webhook)
t.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)