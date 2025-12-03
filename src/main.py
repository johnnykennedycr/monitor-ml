import os
import time
import telebot
from threading import Thread
import schedule
from flask import Flask
import sys

# --- CORREÇÃO DO ERRO DE IMPORTAÇÃO ---
# Adiciona a pasta 'src' ao caminho do Python para ele achar os arquivos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Agora as importações vão funcionar
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
    return "🤖 Bot Monitor ML está online e rodando com Gunicorn!"

# --- LÓGICA DO BOT ---
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    # Proteção: Só responde a você
    if ADMIN_ID and str(message.from_user.id) != str(ADMIN_ID):
        return

    text = message.text.strip()
    
    # Verifica link do ML
    if "mercadolivre.com.br" in text or "mercado.li" in text:
        bot.reply_to(message, "🔎 Lendo link...")
        
        # Extrai dados usando o extractor
        data = extract_details(text)
        
        if data:
            # Adiciona na fila
            if add_to_queue(text, data['title'], data['price'], data['image_url']):
                count = get_queue_stats()
                bot.reply_to(message, f"✅ **Adicionado à fila!**\n📦 {data['title']}\n💰 {data['price']}\n📊 Posição na fila: {count}")
            else:
                bot.reply_to(message, "⚠️ Esse link já estava na fila.")
        else:
            bot.reply_to(message, "❌ Não consegui ler os dados. O link é válido?")
    
    elif text == "/fila":
        count = get_queue_stats()
        bot.reply_to(message, f"📊 Existem **{count}** posts na fila.")

# --- TAREFA DE POSTAGEM ---
def job_poster():
    print("[JOB] Verificando fila...")
    item = get_next_in_line()
    
    if item:
        print(f"[JOB] Postando: {item['title']}")
        try:
            # Gera link de afiliado
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
            print("[JOB] Sucesso.")
            
        except Exception as e:
            print(f"[JOB] Erro ao postar: {e}")

def run_scheduler():
    schedule.every(10).minutes.do(job_poster)
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_background_tasks():
    # Inicializa banco de dados
    init_db()
    
    # Inicia Agendador
    t_sched = Thread(target=run_scheduler)
    t_sched.daemon = True
    t_sched.start()
    
    # Inicia Bot
    t_bot = Thread(target=bot.polling, kwargs={"non_stop": True})
    t_bot.daemon = True
    t_bot.start()
    print("✅ Tarefas de fundo iniciadas!")

# Dispara as threads assim que o Gunicorn carregar este arquivo
start_background_tasks()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)