import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from flask import Flask, request, Response
from threading import Thread
import time
import logging
import requests
import re
import json
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
        # Limpa R$, pontos e troca vírgula
        if isinstance(value, str):
            value = value.replace("R$", "").replace(".", "").replace(",", ".")
        val = float(value)
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(value)

def clean_title(title):
    """Remove sufixos de preço do título (ex: '- R$ 100')"""
    if not title: return "Oferta"
    # Remove " | Mercado Livre"
    title = title.split(" | ")[0]
    # Remove preços no final (ex: "Nome - R$ 100,00" ou "Nome R$ 100")
    title = re.sub(r'\s[-\s]*R\$\s?[\d.,]+.*$', '', title, flags=re.IGNORECASE)
    return title.strip()

def get_ml_data(url):
    print(f"🔎 Scraping: {url}", flush=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    data = {
        "title": "Oferta Imperdível", 
        "price_text": "Ver no site", 
        "image_url": None
    }
    
    try:
        # Usa requests para ser rápido
        resp = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # --- 1. TENTATIVA VIA JSON-LD (DADOS ESTRUTURADOS) ---
        # É onde o ML declara o "lowPrice" oficial para o Google
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                if 'Product' in script.text:
                    jd = json.loads(script.text)
                    if isinstance(jd, list): jd = jd[0] # Às vezes vem lista
                    
                    if jd.get('@type') == 'Product':
                        data["title"] = clean_title(jd.get('name'))
                        data["image_url"] = jd.get('image')
                        
                        offers = jd.get('offers')
                        if offers:
                            # Tenta pegar o menor preço (lowPrice) ou preço normal
                            price = offers.get('lowPrice') or offers.get('price')
                            if price:
                                # Se achou no JSON, já formata e define como novo preço
                                new_price_val = format_price(price)
                                # Vamos tentar achar o antigo visualmente depois
                                data["price_json"] = new_price_val 
                        break
        except Exception as e:
            print(f"⚠️ Erro JSON-LD: {e}", flush=True)

        # --- 2. FALLBACK VISUAL (BS4) ---
        # Se não achou título/imagem no JSON, pega das Meta Tags
        if data["title"] == "Oferta Imperdível":
            meta_title = soup.find("meta", property="og:title")
            if meta_title: data["title"] = clean_title(meta_title["content"])
            else: 
                h1 = soup.find("h1", class_="ui-pdp-title")
                if h1: data["title"] = clean_title(h1.text)

        if not data["image_url"]:
            meta_image = soup.find("meta", property="og:image")
            if meta_image: data["image_url"] = meta_image["content"]

        # --- 3. ESTRATÉGIA DE PREÇO VISUAL ---
        # O JSON às vezes não tem o preço antigo (riscado). Vamos caçar no HTML.
        
        # Preço Novo (Visual - Prioridade para o bloco principal)
        new_price = data.get("price_json") # Começa com o do JSON se tiver
        if not new_price:
            # Procura a fração do preço no container principal
            price_container = soup.find("div", class_="ui-pdp-price__second-line")
            if price_container:
                fraction = price_container.find("span", class_="andes-money-amount__fraction")
                if fraction: new_price = f"R$ {fraction.text}"
        
        # Se ainda não achou, tenta meta tag genérica
        if not new_price:
            meta_price = soup.find("meta", property="product:price:amount")
            if meta_price: new_price = format_price(meta_price["content"])

        # Preço Antigo (Riscado)
        old_price = None
        # Classes comuns de preço riscado no ML
        old_tag = soup.find("s", class_="andes-money-amount--previous") or \
                  soup.find("s", class_="ui-pdp-price__original-value")
        
        if old_tag:
            # Limpa o texto (tira espaços extras)
            old_text = old_tag.get_text(separator=" ", strip=True)
            old_price = " ".join(old_text.split())

        # --- 4. MONTAGEM FINAL DO TEXTO ---
        if old_price and new_price:
            # Verifica se são diferentes para não ficar "DE 100 POR 100"
            if old_price != new_price:
                data["price_text"] = f"DE {old_price} | POR {new_price}"
            else:
                data["price_text"] = f"{new_price}"
        elif new_price:
            data["price_text"] = f"{new_price}"
        
        print(f"✅ Dados Finais: {data}", flush=True)
        return data

    except Exception as e:
        print(f"❌ Erro Geral Scraping: {e}", flush=True)
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
def home(): return "🤖 Bot V17 - Sniper de Preços Ativo!"

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
        msg = bot.reply_to(message, "⏳ **Extraindo menor preço...**", parse_mode="Markdown")
        try:
            product_data = get_ml_data(text)
            aff_link = generate_affiliate_link(text, AFFILIATE_TAG)
            
            user_steps[message.chat.id] = {
                "title": product_data.get("title", "Oferta"),
                "detected_price": product_data.get("price_text"),
                "image_url": product_data.get("image_url"),
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
        curr = user_steps[message.chat.id].get("detected_price", "N/A")
        msg = bot.reply_to(message, f"💰 **Preço?** (Atual: `{curr}`)\nDigite novo ou /skip", parse_mode="Markdown")
        bot.register_next_step_handler(msg, step_price)

def step_price(message):
    txt = message.text
    if txt != "/skip" and message.chat.id in user_steps:
        user_steps[message.chat.id]["detected_price"] = txt
    
    msg = bot.reply_to(message, "🎥 **Mídia Manual?** (Envie Foto/Vídeo ou /skip)")
    bot.register_next_step_handler(message, step_video)

def step_video(message):
    data = user_steps.get(message.chat.id)
    if not data: return

    headline = data.get('custom_msg', '').upper()
    title = f" {data['title']}"
    price = f"🔥R$ {data['detected_price']}"
    coupon = f"\n🎟 CUPOM: {data['coupon']}" if data.get('coupon') else ""
    link = f"\n🔗 {data['final_link']}"
    
    final_text = f"<b>{headline}</b>\n\n{title}\n\n{price}{coupon}\n{link}"
    target = data['target_id']
    scraped_image = data.get('image_url')
    
    try:
        if message.content_type == 'video':
            bot.send_video(target, message.video.file_id, caption=final_text, parse_mode="HTML")
        elif message.content_type == 'photo':
            bot.send_photo(target, message.photo[-1].file_id, caption=final_text, parse_mode="HTML")
        elif scraped_image and message.text == "/skip":
             bot.send_photo(target, scraped_image, caption=final_text, parse_mode="HTML")
        else:
            bot.send_message(target, final_text, disable_web_page_preview=False, parse_mode="HTML")
            
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