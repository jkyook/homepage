from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import ccxt
from database import init_db, add_price, get_prices

app = Flask(__name__)

def fetch_bitcoin_price():
    exchange = ccxt.binance()
    ticker = exchange.fetch_ticker('BTC/USDT')
    price = ticker['last']
    add_price(price)

scheduler = BackgroundScheduler()
# scheduler.add_job(func=fetch_bitcoin_price, trigger="interval", seconds=1)
scheduler.add_job(func=fetch_bitcoin_price, trigger="interval", seconds=5, max_instances=1)
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/prices')
def prices():
    return jsonify(get_prices())

if __name__ == '__main__':
    init_db()
    app.run(debug=True)