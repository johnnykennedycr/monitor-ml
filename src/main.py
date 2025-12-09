import os
import sys
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from flask import Flask, request, Response
from threading import Thread
import time
import logging

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(level=logging.INFO)

# --- CORREÇÃO DE IMPORTAÇÃO ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from link_utils import get_ml_data, generate_affiliate_link
except ImportError:
    # Fallback caso o arquivo não exista, para não crashar o deploy
    def get_ml_data(url): return {"title": "Oferta", "price": "Ver no site"}
    def generate_affiliate_link(url, tag): return url

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
AFFILIATE_TAG = "tepa6477885"

# URL DO SEU APP NO RENDER (Peguei dos seus logs)
# Se mudar o nome do projeto, atualize aqui.
RENDER_URL = "https://monitor-ml.onrender.com" 

# IDs dos Grupos
GROUPS = {
    "geral": os.getenv("GROUP_GERAL"),
    "mae": os.getenv("GROUP_MAE"),
    "util": os.getenv("GROUP_UTIL")
}

user_steps = {}

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- ROTA PRINCIPAL (Health Check) ---
@app.route('/')
def home():
    return "🤖 Bot Webhook Ativo! O Fantasma foi eliminado."

# --- ROTA DE WEBHOOK (Onde o Telegram entrega as msgs) ---
@app.route(f'/{TOKEN}', methods=['POST'])
def process_webhook():
    try:
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return Response('OK', status=200)
    except Exception as e:
        print(f"Erro no webhook: {e}")
        return Response('Error', status=500)

# --- CONFIGURAÇÃO DO WEBHOOK (Roda uma vez ao iniciar) ---
def set_webhook_on_startup():
    # Espera um pouco para o servidor subir
    time.sleep(5)
    print("--- CONFIGURANDO WEBHOOK... ---")
    
    # 1. Remove qualquer configuração anterior (Mata o Polling)
    bot.remove_webhook()
    
    # 2. Define o novo endereço
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    success = bot.set_webhook(url=webhook_url)
    
    if success:
        print(f"✅ Webhook definido com sucesso para: {webhook_url}")
        print("👻 O 'Bot Fantasma' (Polling) foi desativado pelo Telegram!")
    else:
        print("❌ Falha ao definir webhook. Verifique o Token.")

# --- LÓGICA DO BOT (Mesma de antes) ---
@bot.message_handler(commands=['ids'])
def get_id(message):
    bot.reply_to(message, f"🆔 ID deste chat: `{message.chat.id}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def start_publishing(message):
    if ADMIN_ID and str(message.from_user.id) != str(ADMIN_ID):
        return

    text = message.text.strip()
    
    if "mercadolivre" in text or "mercado.li" in text:
        msg = bot.reply_to(message, "🔎 **Extraindo dados...**", parse_mode="Markdown")
        
        try:
            product_data = get_ml_data(text)
            aff_link = generate_affiliate_link(text, AFFILIATE_TAG)
            
            user_steps[message.chat.id] = {
                "title": product_data.get("title", "Produto"),
                "original_price": product_data.get("price"),
                "final_link": aff_link,
                "raw_link": text
            }
            
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("📢 Promoções Gerais", callback_data="grp_geral"))
            markup.row(InlineKeyboardButton("👶 Mãe e Bebê", callback_data="grp_mae"))
            markup.row(InlineKeyboardButton("🏠 Utilidades", callback_data="grp_util"))
            markup.row(InlineKeyboardButton("❌ Cancelar", callback_data="cancel"))
            
            bot.edit_message_text(
                f"📦 **Produto:** {user_steps[message.chat.id]['title']}\n"
                f"💰 **Preço:** {user_steps[message.chat.id]['original_price']}\n\n"
                "**Onde vamos publicar?** 👇",
                chat_id=message.chat.id,
                message_id=msg.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            bot.edit_message_text(f"❌ Erro ao processar: {e}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("grp_") or call.data == "cancel")
def callback_group(call):
    if call.data == "cancel":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        user_steps.pop(call.message.chat.id, None)
        return

    group_key = call.data.replace("grp_", "")
    target_id = GROUPS.get(group_key)
    
    if not target_id:
        bot.answer_callback_query(call.id, "❌ ID não configurado!")
        return

    user_steps[call.message.chat.id]["target_id"] = target_id
    
    msg = bot.edit_message_text(
        "📝 **Headline (Título Chamativo)**\nDigite ou /skip",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, step_get_message)

def step_get_message(message):
    txt = message.text
    if txt == "/skip": txt = ""
    if message.chat.id in user_steps:
        user_steps[message.chat.id]["custom_msg"] = txt
        msg = bot.reply_to(message, "🎟 **Cupom?** Digite ou /skip")
        bot.register_next_step_handler(msg, step_get_coupon)

def step_get_coupon(message):
    txt = message.text
    if txt == "/skip": txt = None
    if message.chat.id in user_steps:
        user_steps[message.chat.id]["coupon"] = txt
        detected = user_steps[message.chat.id].get("original_price", "N/A")
        msg = bot.reply_to(message, f"💰 **Preço?** (Detectado: {detected})\nDigite novo valor ou /skip")
        bot.register_next_step_handler(msg, step_get_price)

def step_get_price(message):
    txt = message.text
    if txt != "/skip" and message.chat.id in user_steps:
        user_steps[message.chat.id]["original_price"] = txt
    
    msg = bot.reply_to(message, "🎥 **Vídeo?** Envie ou /skip")
    bot.register_next_step_handler(message, step_get_video)

def step_get_video(message):
    data = user_steps.get(message.chat.id)
    if not data: return

    headline = data['custom_msg'].upper() if data.get('custom_msg') else ""
    title = f"📦 {data['title']}"
    price = f"🔥 {data['original_price']}" if data.get('original_price') else "🔥 VER PREÇO NO SITE"
    coupon = f"\n🎟 CUPOM: {data['coupon']}" if data.get('coupon') else ""
    link = f"\n🔗 {data['final_link']}"
    
    final_text = f"{headline}\n\n{title}\n\n{price}{coupon}\n{link}"
    target_group = data['target_id']
    
    try:
        if message.content_type == 'video':
            bot.send_video(target_group, message.video.file_id, caption=final_text)
        elif message.content_type == 'photo':
            bot.send_photo(target_group, message.photo[-1].file_id, caption=final_text)
        else:
            bot.send_message(target_group, final_text, disable_web_page_preview=False)
            
        bot.reply_to(message, "✅ **Postado!**")
    except Exception as e:
        bot.reply_to(message, f"❌ Erro envio: {e}")
        
    user_steps.pop(message.chat.id, None)

# --- EXECUÇÃO ---
# Inicia a configuração do webhook em paralelo
t = Thread(target=set_webhook_on_startup)
t.start()

if __name__ == "__main__":
    # Inicia o servidor Web (Flask)
    app.run(host='0.0.0.0', port=8080)