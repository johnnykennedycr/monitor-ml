import os
import sys
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from flask import Flask, request, Response
from threading import Thread
import time
import logging

# --- LOGS DETALHADOS ---
# Isso faz o Telebot narrar tudo o que acontece internamente
telebot.logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

# --- IMPORTAÇÃO SEGURA ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from link_utils import get_ml_data, generate_affiliate_link
    print("✅ Link Utils carregado.", flush=True)
except ImportError as e:
    print(f"⚠️ Aviso: link_utils não encontrado ({e}). Usando fallback.", flush=True)
    def get_ml_data(url): return {"title": "Produto", "price": "Ver no site"}
    def generate_affiliate_link(url, tag): return url

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
AFFILIATE_TAG = "tepa6477885"
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

@app.route('/')
def home():
    return "🤖 Bot Raio-X Ativo"

# --- ROTA WEBHOOK COM LOG BRUTO ---
@app.route(f'/{TOKEN}', methods=['POST'])
def process_webhook():
    try:
        # Lê o pacote que o Telegram mandou
        json_string = request.get_data().decode('utf-8')
        
        # --- RAIO-X: IMPRIME TUDO O QUE CHEGA ---
        print(f"📦 PACOTE RECEBIDO:\n{json_string}", flush=True)
        # ----------------------------------------
        
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return Response('OK', status=200)
    except Exception as e:
        print(f"❌ Erro Webhook: {e}", flush=True)
        return Response('Error', status=500)

# --- COMANDOS ---
@bot.message_handler(commands=['ids', 'id', 'start'])
def command_ids(message):
    print(f"⚡ Comando /ids detectado de {message.from_user.id}", flush=True)
    bot.reply_to(message, f"🆔 Seu ID: `{message.from_user.id}`", parse_mode="Markdown")

# --- PROCESSADOR DE MENSAGENS (TEXTO) ---
@bot.message_handler(content_types=['text'])
def handle_text(message):
    print(f"⚡ Mensagem de texto recebida de {message.from_user.id}: {message.text}", flush=True)
    
    # Validação de Admin com log explícito
    if ADMIN_ID:
        if str(message.from_user.id).strip() != str(ADMIN_ID).strip():
            print(f"⛔ BLOQUEIO: ID {message.from_user.id} != Admin {ADMIN_ID}", flush=True)
            return
        else:
            print("✅ ID Autorizado.", flush=True)
    
    text = message.text.strip()
    
    if "mercadolivre" in text or "mercado.li" in text:
        msg = bot.reply_to(message, "🔎 Processando...", parse_mode="Markdown")
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
            markup.row(InlineKeyboardButton("📢 Geral", callback_data="grp_geral"))
            markup.row(InlineKeyboardButton("👶 Mãe", callback_data="grp_mae"))
            markup.row(InlineKeyboardButton("🏠 Utilidades", callback_data="grp_util"))
            
            bot.edit_message_text(
                f"📦 **{user_steps[message.chat.id]['title']}**\n"
                f"💰 {user_steps[message.chat.id]['original_price']}\n\n"
                "Para qual grupo enviar?",
                chat_id=message.chat.id,
                message_id=msg.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"❌ Erro lógica: {e}", flush=True)
            bot.reply_to(message, f"Erro: {e}")
    else:
        print("⚠️ Texto ignorado (não contém mercadolivre)", flush=True)

# --- CALLBACKS E PASSOS (WIZARD) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_router(call):
    print(f"⚡ Callback recebido: {call.data}", flush=True)
    if call.data.startswith("grp_"):
        step_group_selected(call)

def step_group_selected(call):
    group_key = call.data.replace("grp_", "")
    target_id = GROUPS.get(group_key)
    
    if not target_id:
        bot.answer_callback_query(call.id, "❌ ID não configurado no Render!")
        return

    user_steps[call.message.chat.id]["target_id"] = target_id
    msg = bot.edit_message_text("📝 **Headline?** (Digite ou /skip)", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, step_get_message)

def step_get_message(message):
    txt = message.text
    if txt == "/skip": txt = ""
    if message.chat.id in user_steps:
        user_steps[message.chat.id]["custom_msg"] = txt
        msg = bot.reply_to(message, "🎟 **Cupom?** (Digite ou /skip)")
        bot.register_next_step_handler(msg, step_get_coupon)

def step_get_coupon(message):
    txt = message.text
    if txt == "/skip": txt = None
    if message.chat.id in user_steps:
        user_steps[message.chat.id]["coupon"] = txt
        detected = user_steps[message.chat.id].get("original_price", "N/A")
        msg = bot.reply_to(message, f"💰 **Preço?** (Atual: {detected})\nDigite novo ou /skip")
        bot.register_next_step_handler(msg, step_get_price)

def step_get_price(message):
    txt = message.text
    if txt != "/skip" and message.chat.id in user_steps:
        user_steps[message.chat.id]["original_price"] = txt
    
    msg = bot.reply_to(message, "🎥 **Vídeo?** Envie arquivo ou /skip")
    bot.register_next_step_handler(message, step_get_video)

def step_get_video(message):
    data = user_steps.get(message.chat.id)
    if not data: return

    headline = data.get('custom_msg', '').upper()
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

# --- STARTUP ---
def set_webhook():
    time.sleep(3)
    bot.remove_webhook()
    time.sleep(1)
    # Define o webhook
    bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
    print("✅ Webhook Configurado.", flush=True)

t = Thread(target=set_webhook)
t.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)