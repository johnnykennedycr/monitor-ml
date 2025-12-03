import os
import time
import telebot
from threading import Thread
import schedule

from queue_manager import init_db, add_to_queue, get_next_in_line, mark_as_sent, get_queue_stats
from extractor import extract_details
from affiliate import generate_affiliate_link

TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("TELEGRAM_CHAT_ID")
# Seu ID pessoal (para o bot só aceitar links seus)
ADMIN_ID = os.getenv("ADMIN_ID") # Adicione isso nos Secrets!

bot = telebot.TeleBot(TOKEN)

# --- PARTE 1: RECEBER LINKS (OUVINTE) ---
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    # Segurança: Só aceita comandos seus
    # (Se não quiser filtrar, remova o if)
    if str(message.from_user.id) != str(ADMIN_ID) and ADMIN_ID:
        return

    text = message.text.strip()
    
    # Verifica se é um link do ML
    if "mercadolivre.com.br" in text or "mercado.li" in text:
        bot.reply_to(message, "🔎 Analisando link...")
        
        # Extrai dados
        data = extract_details(text)
        
        if data:
            # Salva na fila
            added = add_to_queue(text, data['title'], data['price'], data['image_url'])
            
            if added:
                count = get_queue_stats()
                bot.reply_to(message, f"✅ **Adicionado à fila!**\n\n📦 {data['title']}\n💰 {data['price']}\n\n📊 Posição na fila: {count}")
            else:
                bot.reply_to(message, "⚠️ Esse link já estava na fila.")
        else:
            bot.reply_to(message, "❌ Não consegui ler os dados desse produto. Tente outro.")
    
    elif text == "/fila":
        count = get_queue_stats()
        bot.reply_to(message, f"📊 Existem **{count}** posts aguardando na fila.")

# --- PARTE 2: POSTADOR AUTOMÁTICO (WORKER) ---
def job_poster():
    print("[JOB] Verificando fila...")
    item = get_next_in_line()
    
    if item:
        print(f"[JOB] Postando: {item['title']}")
        
        # Gera link de afiliado
        aff_link = generate_affiliate_link(item['original_link'])
        
        caption = (
            f"🔥 <b>{item['title']}</b>\n\n"
            f"💰 <b>{item['price']}</b>\n\n"
            f"💳 <i>Verifique parcelamento e frete</i>\n\n"
            f"👇 <b>GARANTA AQUI:</b>\n"
            f"<a href='{aff_link}'>🛒 IR PARA A LOJA</a>"
        )
        
        try:
            if item['image_url']:
                bot.send_photo(GROUP_ID, item['image_url'], caption=caption, parse_mode="HTML")
            else:
                bot.send_message(GROUP_ID, caption, parse_mode="HTML")
            
            mark_as_sent(item['id'])
            print("[JOB] Sucesso.")
            
        except Exception as e:
            print(f"[JOB] Erro ao postar: {e}")
    else:
        print("[JOB] Fila vazia.")

def run_scheduler():
    # Configura para rodar a cada 10 minutos
    schedule.every(10).minutes.do(job_poster)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    init_db()
    
    # Inicia o agendador em uma thread paralela
    t = Thread(target=run_scheduler)
    t.start()
    
    # Inicia o bot (Bloqueia o script aqui para ouvir mensagens)
    print("🤖 Bot rodando e aguardando links...")
    bot.polling()