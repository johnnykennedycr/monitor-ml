import sqlite3
import os
from datetime import datetime

DB_FILE = "src/bot_queue.db"

def init_db():
    """ Cria a tabela se não existir """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_link TEXT UNIQUE,
            title TEXT,
            price TEXT,
            image_url TEXT,
            added_at DATETIME,
            status TEXT DEFAULT 'pending' -- pending, sent, error
        )
    ''')
    conn.commit()
    conn.close()

def add_to_queue(link, title, price, image_url):
    """ Adiciona um novo link à fila """
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            INSERT INTO queue (original_link, title, price, image_url, added_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (link, title, price, image_url, datetime.now()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False # Link já existe na fila

def get_next_in_line():
    """ Pega o próximo item pendente (o mais antigo) """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM queue WHERE status='pending' ORDER BY id ASC LIMIT 1")
    item = c.fetchone()
    conn.close()
    return dict(item) if item else None

def mark_as_sent(item_id):
    """ Marca como enviado para não repetir """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE queue SET status='sent' WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def get_queue_stats():
    """ Retorna quantos itens tem na fila """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM queue WHERE status='pending'")
    count = c.fetchone()[0]
    conn.close()
    return count