import os
import time
import telebot
from threading import Thread
import schedule
from flask import Flask

# Seus módulos
from queue_manager import init_db, add_to_queue, get_next_in_line, mark_as_sent, get_queue_stats
from extractor import extract_details
from affiliate import generate_affiliate_link

TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("TELEGRAM_CHAT_ID")
ADMIN_ID = os.getenv("ADMIN_ID")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- ROTA DO SITE (PING) ---
@app.route('/')
def home():
    return "🤖 Bot Monitor ML está online!"

# --- LÓGICA DO BOT ---
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    if ADMIN_ID and str(message.from_user.id) != str(ADMIN_ID):
        return

    text = message.text.strip()
    if "mercadolivre.com.br" in text or "mercado.li" in text:
        bot.reply_to(message, "🔎 Lendo...")
        data = extract_details(text)
        if data:
            if add_to_queue(text, data['title'], data['price'], data['image_url']):
                count = get_queue_stats()
                bot.reply_to(message, f"✅ Fila: {count}\n📦 {data['title']}")
            else:
                bot.reply_to(message, "⚠️ Duplicado.")
        else:
            bot.reply_to(message, "❌ Erro leitura.")
    elif text == "/fila":
        count = get_queue_stats()
        bot.reply_to(message, f"📊 Fila: {count}")

def job_poster():
    print("[JOB] Verificando fila...")
    item = get_next_in_line()
    if item:
        try:
            aff_link = generate_affiliate_link(item['original_link'])
            caption = (
                f"🔥 <b>{item['title']}</b>\n\n"
                f"💰 <b>{item['price']}</b>\n\n"
                f"👇 <b>GARANTA AQUI:</b>\n"
                f"<a href='{aff_link}'>🛒 IR PARA A LOJA</a>"
            )
            if item['image_url']:
                bot.send_photo(GROUP_ID, item['image_url'], caption=caption, parse_mode="HTML")
            else:
                bot.send_message(GROUP_ID, caption, parse_mode="HTML")
            mark_as_sent(item['id'])
        except Exception as e:
            print(f"Erro postagem: {e}")

def run_scheduler():
    schedule.every(10).minutes.do(job_poster)
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_background_tasks():
    init_db()
    # Thread do Agendador
    t_sched = Thread(target=run_scheduler)
    t_sched.daemon = True
    t_sched.start()
    
    # Thread do Bot (Polling)
    # Importante: Thread daemon morre quando o site desliga
    t_bot = Thread(target=bot.polling, kwargs={"non_stop": True})
    t_bot.daemon = True
    t_bot.start()
    print("✅ Tarefas de fundo iniciadas!")

# --- A MÁGICA ACONTECE AQUI ---
# Executamos isso no nível global para o Gunicorn pegar
start_background_tasks()

if __name__ == "__main__":
    # Apenas para teste local no seu PC
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))