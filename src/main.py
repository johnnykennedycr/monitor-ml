import os
import sys

# --- CORREÇÃO DE IMPORTAÇÃO (Essencial para o Render) ---
# Adiciona a pasta atual (src) ao caminho do Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread
import time

# Agora o import vai funcionar
from link_utils import get_ml_data, generate_affiliate_link

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
AFFILIATE_TAG = "tepa6477885"

# IDs dos Grupos
GROUPS = {
    "geral": os.getenv("GROUP_GERAL"),
    "mae": os.getenv("GROUP_MAE"),
    "util": os.getenv("GROUP_UTIL")
}

user_steps = {}

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- WEB SERVER ---
@app.route('/')
def home():
    return "🤖 Bot Publicador V1 - Online!"

# --- COMANDOS ---
@bot.message_handler(commands=['ids'])
def get_id(message):
    bot.reply_to(message, f"🆔 ID deste chat: `{message.chat.id}`", parse_mode="Markdown")

# --- LÓGICA DE PUBLICAÇÃO ---
@bot.message_handler(func=lambda m: True)
def start_publishing(message):
    # Segurança
    if ADMIN_ID and str(message.from_user.id) != str(ADMIN_ID):
        return

    text = message.text.strip()
    
    if "mercadolivre" in text or "mercado.li" in text:
        msg = bot.reply_to(message, "🔎 **Extraindo dados...**", parse_mode="Markdown")
        
        try:
            product_data = get_ml_data(text)
            aff_link = generate_affiliate_link(text, AFFILIATE_TAG)
            
            user_steps[message.chat.id] = {
                "title": product_data["title"],
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
                f"📦 **Produto:** {product_data['title']}\n"
                f"💰 **Preço:** {product_data['price']}\n\n"
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
        bot.answer_callback_query(call.id, "❌ Configure o ID desse grupo no Render!")
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
    user_steps[message.chat.id]["custom_msg"] = txt
    
    msg = bot.reply_to(message, "🎟 **Cupom?** Digite ou /skip")
    bot.register_next_step_handler(msg, step_get_coupon)

def step_get_coupon(message):
    txt = message.text
    if txt == "/skip": txt = None
    user_steps[message.chat.id]["coupon"] = txt
    
    detected = user_steps[message.chat.id].get("original_price", "N/A")
    msg = bot.reply_to(message, f"💰 **Preço?** (Detectado: {detected})\nDigite o valor correto ou /skip")
    bot.register_next_step_handler(msg, step_get_price)

def step_get_price(message):
    txt = message.text
    if txt != "/skip":
        user_steps[message.chat.id]["original_price"] = txt
    
    msg = bot.reply_to(message, "🎥 **Vídeo?** Envie o arquivo ou /skip")
    bot.register_next_step_handler(message, step_get_video)

def step_get_video(message):
    data = user_steps.get(message.chat.id)
    if not data: return

    headline = data['custom_msg'].upper() if data['custom_msg'] else ""
    title = f"📦 {data['title']}"
    price = f"🔥 {data['original_price']}" if data['original_price'] else "🔥 VER PREÇO NO SITE"
    coupon = f"\n🎟 CUPOM: {data['coupon']}" if data['coupon'] else ""
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
        bot.reply_to(message, f"❌ Erro: {e}")
        
    user_steps.pop(message.chat.id, None)

# --- INICIALIZAÇÃO ---
def run_bot():
    bot.infinity_polling()

# Thread global para o Gunicorn pegar
t = Thread(target=run_bot)
t.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)