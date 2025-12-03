import os
import time
import telebot
from threading import Thread
import schedule
from flask import Flask
import sys

# Garante que imports funcionem
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from queue_manager import init_db, add_to_queue, get_next_in_line, mark_as_sent, get_queue_stats
from extractor import extract_details
from affiliate import generate_affiliate_link

TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("TELEGRAM_CHAT_ID")
# ADMIN_ID removido temporariamente para teste

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot Online e Rodando!"

# --- MODO DEBUG TAGARELA ---
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    # Imprime no log IMEDIATAMENTE
    print(f"!!! MENSAGEM RECEBIDA !!! De: {message.from_user.id} | Texto: {message.text}", flush=True)

    text = message.text.strip()
    
    # Responde "Oi" só para sabermos que ele está vivo
    if text == "/ping":
        bot.reply_to(message, "🏓 PONG! Estou te ouvindo no Render!")
        return

    # Lógica original
    if "mercadolivre.com.br" in text or "mercado.li" in text:
        print(f"-> Link detectado: {text}", flush=True)
        bot.reply_to(message, "🔎 Analisando link...")
        
        try:
            data = extract_details(text)
            if data:
                if add_to_queue(text, data['title'], data['price'], data['image_url']):
                    count = get_queue_stats()
                    bot.reply_to(message, f"✅ **Na fila!**\n📦 {data['title']}\n📊 Posição: {count}")
                else:
                    bot.reply_to(message, "⚠️ Duplicado na fila.")
            else:
                bot.reply_to(message, "❌ Link válido, mas falha na extração.")
        except Exception as e:
            print(f"ERRO AO PROCESSAR: {e}", flush=True)
            bot.reply_to(message, "Erro interno ao processar.")

    elif text == "/fila":
        count = get_queue_stats()
        bot.reply_to(message, f"📊 Fila: {count}")
    
    else:
        bot.reply_to(message, "Mande um link do ML ou digite /ping")

def job_poster():
    print("[JOB] Verificando fila...", flush=True)
    item = get_next_in_line()
    if item:
        print(f"[JOB] Postando: {item['title']}", flush=True)
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
            print(f"Erro postagem: {e}", flush=True)

def run_scheduler():
    schedule.every(10).minutes.do(job_poster)
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_background_tasks():
    init_db()
    
    # Thread Agendador
    t_sched = Thread(target=run_scheduler)
    t_sched.daemon = True
    t_sched.start()
    
    # Thread Bot (Com loop de proteção)
    def bot_loop():
        print("--- THREAD DO BOT INICIADA ---", flush=True)
        while True:
            try:
                print("--- CONECTANDO AO TELEGRAM ---", flush=True)
                bot.polling(non_stop=True, timeout=60)
            except Exception as e:
                print(f"--- ERRO NO POLLING: {e} ---", flush=True)
                time.sleep(5)

    t_bot = Thread(target=bot_loop)
    t_bot.daemon = True
    t_bot.start()

start_background_tasks()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)