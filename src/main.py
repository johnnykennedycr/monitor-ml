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

# --- BOT SÍNCRONO ---
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- FUNÇÕES DE EXTRAÇÃO ---
def format_price(value):
    try:
        val = float(value)
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return value

def get_ml_data(url):
    print(f"🔎 Iniciando Scraping: {url}", flush=True)
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'mobile': False})
    
    # Estrutura inicial
    data = {
        "title": "Oferta Imperdível", 
        "price_text": "Ver no site" # Texto final que vai pro post
    }
    
    try:
        resp = scraper.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 1. TÍTULO
        title = soup.find("h1", class_="ui-pdp-title")
        if title: data["title"] = title.text.strip()
        
        # 2. PREÇO NOVO (O valor real de venda)
        new_price = None
        price_meta = soup.find("meta", property="product:price:amount")
        if price_meta:
            new_price = format_price(price_meta["content"])
            
        # 3. PREÇO ANTIGO (O valor riscado "De:")
        old_price = None
        # Procura por tags de preço riscado (<s> ou classes específicas)
        # O ML usa classes como 'ui-pdp-price__original-value' ou 'andes-money-amount--previous'
        old_price_tag = soup.find("s", class_="andes-money-amount--previous")
        
        if not old_price_tag:
            # Tenta outra classe comum
            old_price_tag = soup.find("s", class_="ui-pdp-price__original-value")
            
        if old_price_tag:
            # O texto vem sujo (ex: "R$ 100"), usamos get_text para limpar
            # As vezes o simbolo R$ está separado, o get_text junta tudo
            old_price = old_price_tag.get_text(separator=" ", strip=True)
            # Remove espaços duplos
            old_price = " ".join(old_price.split())

        # 4. MONTAGEM DA STRING DE PREÇO
        if old_price and new_price:
            data["price_text"] = f"DE {old_price} | POR {new_price}"
        elif new_price:
            data["price_text"] = f"{new_price}"
        else:
            data["price_text"] = "CONFIRA NO SITE"

        print(f"✅ Scraping concluído: {data}", flush=True)
        return data

    except Exception as e:
        print(f"❌ Erro Scraping: {e}", flush=True)
        return data

def generate_affiliate_link(url, tag):
    final_url = url
    if "/sec/" in url or "mercado.li" in url or "bit.ly" in url:
        try:
            resp = requests.get(url, allow_redirects=True, timeout=10)
            final_url = resp.url
        except: pass

    clean_link = final_url.split("?")[0]
    match = re.search(r'(MLB-?\d+)', final_url)
    if match:
        clean_id = match.group(1).replace("-", "")
        clean_link = f"https://www.mercadolivre.com.br/p/{clean_id}"
    
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
def home(): return "🤖 Bot V14 - Preço Duplo Ativo!"

@app.route(f'/{TOKEN}', methods=['POST'])
def process_webhook():
    try:
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return Response('OK', status=200)
    except Exception as e:
        print(f"❌ Erro Webhook: {e}", flush=True)
        return Response('Error', status=500)

# --- BOT LÓGICA ---
@bot.message_handler(commands=['ids', 'start'])
def command_ids(message):
    bot.reply_to(message, f"🆔 Seu ID: `{message.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
    user_id = str(message.from_user.id).strip()
    if ADMIN_ID and user_id != str(ADMIN_ID).strip():
        bot.reply_to(message, "⛔ Acesso Negado.")
        return
    
    text = message.text.strip()
    
    if "mercadolivre" in text or "mercado.li" in text:
        msg = bot.reply_to(message, "⏳ **Analisando Preços...**", parse_mode="Markdown")
        try:
            product_data = get_ml_data(text)
            aff_link = generate_affiliate_link(text, AFFILIATE_TAG)
            
            # Armazena os dados
            user_steps[message.chat.id] = {
                "title": product_data.get("title", "Oferta"),
                "detected_price": product_data.get("price_text"), # Guarda o texto formatado (De/Por)
                "final_link": aff_link,
                "raw_link": text
            }
            
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("📢 Geral", callback_data="grp_geral"), InlineKeyboardButton("👶 Mãe", callback_data="grp_mae"))
            markup.row(InlineKeyboardButton("🏠 Util", callback_data="grp_util"), InlineKeyboardButton("❌ Cancelar", callback_data="cancel"))
            
            bot.edit_message_text(
                f"📦 **{user_steps[message.chat.id]['title']}**\n"
                f"💰 **{user_steps[message.chat.id]['detected_price']}**\n\n"
                "**Para qual grupo enviar?** 👇",
                chat_id=message.chat.id,
                message_id=msg.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            bot.edit_message_text(f"❌ Erro: {e}", chat_id=message.chat.id, message_id=msg.message_id)
    else:
        bot.reply_to(message, "Mande um link do ML.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "cancel":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        user_steps.pop(call.message.chat.id, None)
        return

    if call.data.startswith("grp_"):
        grp = call.data.replace("grp_", "")
        target = GROUPS.get(grp)
        if not target:
            bot.answer_callback_query(call.id, "❌ ID não configurado!")
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
        
        # Mostra o preço detectado (De/Por) e permite editar
        curr = user_steps[message.chat.id].get("detected_price", "N/A")
        msg = bot.reply_to(message, 
                           f"💰 **Preço da Oferta**\n"
                           f"Detectado: `{curr}`\n\n"
                           "Digite para corrigir ou /skip para usar o detectado.", 
                           parse_mode="Markdown")
        bot.register_next_step_handler(msg, step_price)

def step_price(message):
    txt = message.text
    # Se o usuário digitar algo, substitui o preço automático
    if txt != "/skip" and message.chat.id in user_steps:
        user_steps[message.chat.id]["detected_price"] = txt
    
    msg = bot.reply_to(message, "🎥 **Vídeo?** (Envie ou /skip)")
    bot.register_next_step_handler(message, step_video)

def step_video(message):
    data = user_steps.get(message.chat.id)
    if not data: return

    headline = data.get('custom_msg', '').upper()
    title = f"📦 {data['title']}"
    # Usa o preço que veio do scraper ou o que o usuário editou
    price = f"🔥 {data['detected_price']}" 
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
    time.sleep(2)
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
    print("✅ Webhook OK.", flush=True)

t = Thread(target=set_webhook)
t.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)