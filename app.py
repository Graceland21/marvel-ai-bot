import asyncio
import sys
import types
import requests
import socket
import os
from datetime import datetime, timedelta

# =========================
# FIXES FOR ANDROID/RENDER
# =========================
sys.modules['imghdr'] = types.ModuleType('imghdr')
socket.setdefaulttimeout(30)

from telegram import Bot

# =========================
# ENV VARIABLES (RENDER)
# =========================
TOKEN = os.getenv("8704948433:AAEmCjobJckYRnQUZ-cfVQT7VFFeSa9aAMA")
CHAT_ID = os.getenv("-1002497463613")

bot = Bot(token=TOKEN)

PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
TIMEFRAME = "2m"
EXPIRY_MINUTES = 2


# =========================
# SAFE SEND (NO TIMEOUT BUG)
# =========================
async def safe_send(message):
    for attempt in range(5):
        try:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=message
            )
            print("Message sent")
            return True

        except Exception as e:
            print(f"Send error: {e}")
            await asyncio.sleep(5 + attempt * 2)

    print("Failed to send message")
    return False


# =========================
# GET MARKET DATA (SAFE)
# =========================
def get_prices(pair):
    url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval=1m&limit=20"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        closes = [float(candle[4]) for candle in data]
        return closes

    except Exception as e:
        print(f"Binance error: {e}")
        return None


# =========================
# RSI CALCULATION
# =========================
def calculate_rsi(prices):
    gains = []
    losses = []

    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]

        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))

    avg_gain = sum(gains) / len(gains)
    avg_loss = sum(losses) / len(losses)

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# =========================
# TREND
# =========================
def get_trend(prices):
    return "UP" if prices[-1] > prices[-5] else "DOWN"


# =========================
# ANALYSIS
# =========================
def analyze(pair):
    prices = get_prices(pair)

    if prices is None:
        return None, 0, 0, 0

    rsi = calculate_rsi(prices)
    trend = get_trend(prices)
    current_price = prices[-1]

    support = min(prices[-10:])
    resistance = max(prices[-10:])

    direction = None
    confidence = 50

    if current_price <= support * 1.005 and rsi < 45 and trend == "UP":
        direction = "BUY"
        confidence = 90

    elif current_price >= resistance * 0.995 and rsi > 55 and trend == "DOWN":
        direction = "SELL"
        confidence = 90

    elif trend == "UP" and rsi < 55:
        direction = "BUY"
        confidence = 75

    elif trend == "DOWN" and rsi > 45:
        direction = "SELL"
        confidence = 75

    if direction == "BUY" and current_price < support:
        return None, 0, rsi, current_price

    if direction == "SELL" and current_price > resistance:
        return None, 0, rsi, current_price

    return direction, confidence, rsi, current_price


# =========================
# FORMAT TIME
# =========================
def format_time(dt):
    return dt.strftime("%I:%M %p")


# =========================
# SEND SIGNAL
# =========================
async def send_signal(pair):
    direction, confidence, rsi, entry_price = analyze(pair)

    if direction is None or confidence < 75:
        return None, None

    now = datetime.now()

    entry_time = now
    expiry_time = now + timedelta(minutes=EXPIRY_MINUTES)

    mg1 = expiry_time
    mg2 = expiry_time + timedelta(minutes=EXPIRY_MINUTES)

    message = f"""
MARVEL-CORE AI SIGNAL

Pair: {pair}
Timeframe: {TIMEFRAME}
Direction: {direction}

RSI: {round(rsi, 2)}
Confidence: {confidence}%

Entry: {format_time(entry_time)}
Expiry: {format_time(expiry_time)}
