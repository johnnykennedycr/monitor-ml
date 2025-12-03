import os
import time
import telebot
from threading import Thread
import schedule
from flask import Flask
import sys

# Garante que o Python encontre os arquivos vizinhos (queue_manager, etc)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from queue_manager import init_db, add_to_queue, get_next_in_line, mark_as_sent, get_queue_stats
from extractor import extract_details
from affiliate import generate_affiliate_link

TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("TELEGRAM_CHAT_ID")
ADMIN_ID = os.getenv("ADMIN_ID")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- ROTA DO SITE (PING PARA O RENDER) ---
@app.route('/')
def home():
    return "🤖 Bot Monitor ML está online e rodando!"

# --- LÓGICA DE MENSAGENS DO BOT ---
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    # Log imediato para debug no Render
    print(f"!!! MENSAGEM RECEBIDA !!! De: {message.from_user.id} | Texto: {message.text}", flush=True)

    # Verifica permissão (se ADMIN_ID estiver configurado)
    if ADMIN_ID and str(message.from_user.id) != str(ADMIN_ID):
        print(f"!!! ACESSO NEGADO !!! Usuário {message.from_user.id} não é o admin.", flush=True)
        return

    text = message.text.strip()
    
    # 1. Comando de teste
    if text == "/ping":
        bot.reply_to(message, "🏓 PONG! Estou te ouvindo no Render!")
        return

    # 2. Comando para ver tamanho da fila
    if text == "/fila":
        count = get_queue_stats()
        bot.reply_to(message, f"📊 Fila atual: {count} posts aguardando.")
        return

    # 3. Detector de Links (CORRIGIDO PARA ACEITAR LINKS MOBILE)
    # Aceita 'mercadolivre.com', 'mercadolivre.com.br', 'mercado.li', etc.
    if "mercadolivre" in text or "mercado.li" in text:
        print(f"-> Link detectado: {text}", flush=True)
        bot.reply_to(message, "🔎 Analisando link...")
        
        try:
            # Extrai Título, Preço e Foto
            data = extract_details(text)
            
            if data and data['title']:
                # Adiciona no Banco de Dados
                if add_to_queue(text, data['title'], data['price'], data['image_url']):
                    count = get_queue_stats()
                    bot.reply_to(message, f"✅ **Na fila!**\n📦 {data['title']}\n💰 {data['price']}\n📊 Posição: {count}")
                else:
                    bot.reply_to(message, "⚠️ Esse link já estava na fila.")
            else:
                bot.reply_to(message, "❌ Link válido, mas não consegui ler o Título/Preço. O anúncio está ativo?")
        
        except Exception as e:
            print(f"ERRO AO PROCESSAR: {e}", flush=True)
            bot.reply_to(message, "Erro interno ao processar link.")
    
    else:
        # Se mandou texto aleatório
        bot.reply_to(message, "Mande um link do Mercado Livre para eu postar.")

# --- TAREFA AGENDADA (POSTADOR) ---
def job_poster():
    print("[JOB] Verificando fila...", flush=True)
    item = get_next_in_line()
    
    if item:
        print(f"[JOB] Postando: {item['title']}", flush=True)
        try:
            # Gera link de afiliado
            aff_link = generate_affiliate_link(item['original_link'])
            
            caption = (
                f"🔥 <b>{item['title']}</b>\n\n"
                f"💰 <b>{item['price']}</b>\n\n"
                f"💳 <i>Verifique parcelamento</i>\n\n"
                f"👇 <b>GARANTA AQUI:</b>\n"
                f"<a href='{aff_link}'>🛒 IR PARA A LOJA</a>"
            )
            
            # Envia com foto se tiver, senão só texto
            if item['image_url']:
                bot.send_photo(GROUP_ID, item['image_url'], caption=caption, parse_mode="HTML")
            else:
                bot.send_message(GROUP_ID, caption, parse_mode="HTML")
            
            # Marca como enviado no banco
            mark_as_sent(item['id'])
            print("[JOB] Sucesso.", flush=True)
            
        except Exception as e:
            print(f"[JOB] Erro ao postar: {e}", flush=True)
    else:
        print("[JOB] Fila vazia.", flush=True)

# --- GERENCIADOR DE AGENDAMENTO ---
def run_scheduler():
    schedule.every(10).minutes.do(job_poster)
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- INICIALIZAÇÃO DE THREADS ---
def start_background_tasks():
    init_db()
    
    # Thread do Agendador (Roda a cada 10 min)
    t_sched = Thread(target=run_scheduler)
    t_sched.daemon = True
    t_sched.start()
    
    # Thread do Bot (Polling infinito com reconexão)
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

# Inicia tudo assim que o Gunicorn carrega o arquivo
start_background_tasks()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)