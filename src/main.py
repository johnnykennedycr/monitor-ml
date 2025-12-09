import os
import sys
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from flask import Flask, request, Response
from threading import Thread
import time
import logging

# --- LOGS ---
logging.basicConfig(level=logging.INFO)

# --- IMPORTAÇÃO SEGURA ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from link_utils import get_ml_data, generate_affiliate_link
    print("✅ Módulo link_utils carregado com sucesso.", flush=True)
except ImportError as e:
    print(f"⚠️ Erro ao importar link_utils: {e}", flush=True)
    # Fallbacks para não quebrar
    def get_ml_data(url): return {"title": "Produto Detectado", "price": "Ver no Site"}
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

# --- ROTA DE SAÚDE ---
@app.route('/')
def home():
    return "🤖 Bot Webhook Diagnóstico Ativo!"

# --- ROTA WEBHOOK ---
@app.route(f'/{TOKEN}', methods=['POST'])
def process_webhook():
    try:
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return Response('OK', status=200)
    except Exception as e:
        print(f"❌ Erro no processamento do Webhook: {e}", flush=True)
        return Response('Error', status=500)

# --- COMANDO IDS (Para todos, ajuda a descobrir seu ID) ---
@bot.message_handler(commands=['ids', 'id', 'start'])
def get_id(message):
    print(f"📝 Comando recebido de: {message.from_user.id} ({message.from_user.first_name})", flush=True)
    bot.reply_to(message, f"🆔 **Seu ID:** `{message.from_user.id}`\n📍 **ID do Chat:** `{message.chat.id}`", parse_mode="Markdown")

# --- PROCESSADOR DE LINKS ---
@bot.message_handler(func=lambda m: True)
def start_publishing(message):
    user_id = str(message.from_user.id)
    print(f"📩 Mensagem recebida de ID: {user_id} | Admin configurado: {ADMIN_ID}", flush=True)

    # DIAGNÓSTICO DE ADMIN
    if ADMIN_ID and user_id != str(ADMIN_ID).strip():
        print(f"⛔ Bloqueado! O usuário {user_id} não é o Admin {ADMIN_ID}", flush=True)
        # Opcional: Avisar no chat para você saber que errou o ID
        bot.reply_to(message, f"⛔ Acesso Negado. Seu ID `{user_id}` não confere com o Admin configurado.", parse_mode="Markdown")
        return

    text = message.text.strip()
    print(f"🔎 Analisando texto: {text}", flush=True)
    
    if "mercadolivre" in text or "mercado.li" in text:
        msg = bot.reply_to(message, "⏳ **Processando link...**", parse_mode="Markdown")
        
        try:
            # Tenta extrair
            print("   -> Extraindo dados...", flush=True)
            product_data = get_ml_data(text)
            print(f"   -> Dados: {product_data}", flush=True)
            
            aff_link = generate_affiliate_link(text, AFFILIATE_TAG)
            
            user_steps[message.chat.id] = {
                "title": product_data.get("title", "Oferta"),
                "original_price": product_data.get("price"),
                "final_link": aff_link,
                "raw_link": text
            }
            
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("📢 Geral", callback_data="grp_geral"), InlineKeyboardButton("👶 Mãe", callback_data="grp_mae"))
            markup.row(InlineKeyboardButton("🏠 Utilidades", callback_data="grp_util"), InlineKeyboardButton("❌ Cancelar", callback_data="cancel"))
            
            bot.edit_message_text(
                f"📦 **{product_data.get('title')}**\n"
                f"💰 {product_data.get('price')}\n\n"
                "**Onde publicar?** 👇",
                chat_id=message.chat.id,
                message_id=msg.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"❌ Erro na lógica do link: {e}", flush=True)
            bot.edit_message_text(f"❌ Erro interno: {e}", chat_id=message.chat.id, message_id=msg.message_id)
    else:
        print("   -> Texto ignorado (não parece link ML).", flush=True)

# --- CALLBACKS E PASSOS (Mantidos iguais, omitidos para brevidade se não mudaram) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("grp_") or call.data == "cancel")
def callback_group(call):
    if call.data == "cancel":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        return

    group_key = call.data.replace("grp_", "")
    target_id = GROUPS.get(group_key)
    print(f"👉 Grupo selecionado: {group_key} -> ID: {target_id}", flush=True)
    
    if not target_id:
        bot.answer_callback_query(call.id, "❌ ID do grupo não configurado no Render!")
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
        curr_price = user_steps[message.chat.id].get("original_price", "N/A")
        msg = bot.reply_to(message, f"💰 **Preço?** (Atual: {curr_price})\nDigite novo ou /skip")
        bot.register_next_step_handler(msg, step_get_price)

def step_get_price(message):
    txt = message.text
    if txt != "/skip" and message.chat.id in user_steps:
        user_steps[message.chat.id]["original_price"] = txt
    
    msg = bot.reply_to(message, "🎥 **Vídeo?** (Envie ou /skip)")
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
    
    print(f"🚀 Enviando para {target_group}...", flush=True)
    try:
        if message.content_type == 'video':
            bot.send_video(target_group, message.video.file_id, caption=final_text)
        elif message.content_type == 'photo':
            bot.send_photo(target_group, message.photo[-1].file_id, caption=final_text)
        else:
            bot.send_message(target_group, final_text, disable_web_page_preview=False)
        bot.reply_to(message, "✅ **Postado!**")
    except Exception as e:
        print(f"❌ Erro no envio final: {e}", flush=True)
        bot.reply_to(message, f"❌ Erro envio: {e}")
        
    user_steps.pop(message.chat.id, None)

# --- STARTUP WEBHOOK ---
def set_webhook_on_startup():
    time.sleep(3) # Dá tempo pro Flask subir
    bot.remove_webhook()
    time.sleep(1)
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    s = bot.set_webhook(url=webhook_url)
    if s: print(f"✅ Webhook setado: {webhook_url}", flush=True)
    else: print("❌ Falha no Webhook", flush=True)

t = Thread(target=set_webhook_on_startup)
t.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)