import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('bitcoin_prices.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS prices
                 (timestamp TEXT, price REAL)''')
    conn.commit()
    conn.close()

def add_price(price):
    conn = sqlite3.connect('bitcoin_prices.db')
    c = conn.cursor()
    c.execute("INSERT INTO prices VALUES (?, ?)", (datetime.now().isoformat(), price))
    conn.commit()
    conn.close()

def get_prices():
    conn = sqlite3.connect('bitcoin_prices.db')
    c = conn.cursor()
    c.execute("SELECT * FROM prices ORDER BY timestamp DESC LIMIT 100")
    prices = [{"timestamp": row[0], "price": row[1]} for row in c.fetchall()]
    conn.close()
    return prices