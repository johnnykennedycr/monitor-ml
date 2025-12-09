import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread
import time

# Importa nossas ferramentas
from link_utils import get_ml_data, generate_affiliate_link

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # Seu ID para segurança
AFFILIATE_TAG = "tepa6477885"

# IDs dos Grupos (Configure no Render ou coloque direto aqui se souber)
GROUPS = {
    "geral": os.getenv("GROUP_GERAL"),
    "mae": os.getenv("GROUP_MAE"),
    "util": os.getenv("GROUP_UTIL")
}

# Estado temporário para guardar as respostas (Passo a passo)
# Estrutura: {chat_id: {'link': '...', 'group': '...', 'msg': '...', 'cupom': '...'}}
user_steps = {}

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- WEB SERVER (PING) ---
@app.route('/')
def home():
    return "🤖 Bot Publicador Ativo!"

# --- AJUDA PARA DESCOBRIR IDS ---
@bot.message_handler(commands=['ids'])
def get_id(message):
    bot.reply_to(message, f"🆔 ID deste chat: `{message.chat.id}`", parse_mode="Markdown")

# --- PASSO 1: RECEBER O LINK ---
@bot.message_handler(func=lambda m: True)
def start_publishing(message):
    # Segurança: Só aceita você
    if str(message.from_user.id) != str(ADMIN_ID):
        return # Ignora estranhos

    text = message.text.strip()
    
    # Verifica se é link do ML
    if "mercadolivre" in text or "mercado.li" in text:
        msg = bot.reply_to(message, "🔎 **Analisando link e extraindo dados...**", parse_mode="Markdown")
        
        # 1. Extrai dados e Gera Link
        product_data = get_ml_data(text)
        aff_link = generate_affiliate_link(text, AFFILIATE_TAG)
        
        # Salva no estado
        user_steps[message.chat.id] = {
            "title": product_data["title"],
            "original_price": product_data.get("price"), # Preço que o scraper achou
            "final_link": aff_link,
            "raw_link": text
        }
        
        # 2. Pergunta o Grupo
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📢 Promoções Gerais", callback_data="grp_geral"))
        markup.row(InlineKeyboardButton("👶 Mãe e Bebê", callback_data="grp_mae"))
        markup.row(InlineKeyboardButton("🏠 Utilidades", callback_data="grp_util"))
        markup.row(InlineKeyboardButton("❌ Cancelar", callback_data="cancel"))
        
        bot.edit_message_text(
            f"📦 **Produto:** {product_data['title']}\n"
            f"💰 **Preço Detectado:** {product_data['price']}\n\n"
            "**Onde vamos publicar?** 👇",
            chat_id=message.chat.id,
            message_id=msg.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )

# --- PASSO 2: ESCOLHER GRUPO ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("grp_") or call.data == "cancel")
def callback_group(call):
    if call.data == "cancel":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        user_steps.pop(call.message.chat.id, None)
        return

    group_key = call.data.replace("grp_", "")
    target_id = GROUPS.get(group_key)
    
    if not target_id:
        bot.answer_callback_query(call.id, "❌ ID desse grupo não configurado!")
        return

    # Salva grupo escolhido
    user_steps[call.message.chat.id]["target_id"] = target_id
    
    # Pergunta Mensagem Adicional
    msg = bot.edit_message_text(
        "📝 **Digite a Headline (Título Chamativo)**\n"
        "Ex: _VAI TE SALVAR NO CALOR_\n\n"
        "Ou digite /skip para deixar em branco.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, step_get_message)

# --- PASSO 3: MENSAGEM ADICIONAL ---
def step_get_message(message):
    txt = message.text
    if txt == "/skip": txt = ""
    
    user_steps[message.chat.id]["custom_msg"] = txt
    
    msg = bot.reply_to(message, 
        "🎟 **Tem Cupom?** Digite o código.\n"
        "Ex: `DOMINGOU`\n\n"
        "Ou digite /skip se não tiver.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, step_get_coupon)

# --- PASSO 4: CUPOM ---
def step_get_coupon(message):
    txt = message.text
    if txt == "/skip": txt = None
    
    user_steps[message.chat.id]["coupon"] = txt
    
    # Pergunta PREÇO (Opcional editar o que o scraper achou)
    detected = user_steps[message.chat.id].get("original_price", "Não detectado")
    msg = bot.reply_to(message, 
        f"💰 **Preço da Oferta**\n"
        f"Detectado: {detected}\n\n"
        "Digite o valor correto (Ex: `R$ 1.200`) ou /skip para usar o detectado.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, step_get_price)

# --- PASSO 5: PREÇO ---
def step_get_price(message):
    txt = message.text
    if txt != "/skip":
        user_steps[message.chat.id]["original_price"] = txt
    
    msg = bot.reply_to(message,
        "🎥 **Tem Vídeo?**\n"
        "Envie o arquivo de vídeo agora, ou digite /skip para enviar sem vídeo.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(message, step_get_video)

# --- PASSO 6: VÍDEO E DISPARO FINAL ---
def step_get_video(message):
    data = user_steps.get(message.chat.id)
    if not data: return # Erro de estado

    # Monta a Mensagem Final
    # Padrão solicitado:
    # HEADLINE
    # ❄️ Título
    # 🔥 Preço
    # 🎟 Cupom
    # 🔗 Link
    
    headline = data['custom_msg'].upper() if data['custom_msg'] else ""
    title = f"📦 {data['title']}"
    price = f"🔥 {data['original_price']}" if data['original_price'] else "🔥 VER PREÇO NO SITE"
    coupon = f"\n🎟 CUPOM: {data['coupon']}" if data['coupon'] else ""
    link = f"\n🔗 {data['final_link']}"
    
    final_text = f"{headline}\n\n{title}\n\n{price}{coupon}\n{link}"
    
    target_group = data['target_id']
    
    try:
        # Envia para o Grupo
        if message.content_type == 'video':
            bot.send_video(target_group, message.video.file_id, caption=final_text)
        elif message.content_type == 'photo':
            bot.send_photo(target_group, message.photo[-1].file_id, caption=final_text)
        else:
            bot.send_message(target_group, final_text, disable_web_page_preview=False)
            
        bot.reply_to(message, "✅ **Postado com Sucesso!**")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao postar: {e}")
        
    # Limpa estado
    user_steps.pop(message.chat.id, None)

# --- INICIALIZAÇÃO ---
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_bot)
    t.start()
    app.run(host='0.0.0.0', port=8080)