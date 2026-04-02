import warnings
warnings.filterwarnings("ignore")

import asyncio
import sys
import types
import requests
import socket
from datetime import datetime, timedelta

# =========================
# FIXES
# =========================
sys.modules['imghdr'] = types.ModuleType('imghdr')
socket.setdefaulttimeout(30)

from telegram import Bot

# =========================
# 🔐 YOUR VALUES
# =========================
TOKEN = "8704948433:AAH_4w_2yQbMejLXPXirir8nh_mhLN2hFMU"
CHAT_ID = "-1002497463613"

bot = Bot(token=TOKEN)

PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
TIMEFRAME = 2   # minutes
EXPIRY_MINUTES = 2


# =========================
# SAFE SEND
# =========================
async def safe_send(message):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print("Send error:", e)


# =========================
# GET DATA
# =========================
    def get_prices(pair):
    url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval=1m&limit=20"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        # 🔥 FIX 1: Check if Binance returned error
        if isinstance(data, dict):
            print("Binance API error:", data)
            return None

        # 🔥 FIX 2: Validate structure
        if not data or not isinstance(data, list):
            print("Invalid data format:", data)
            return None

        closes = []
        for candle in data:
            if len(candle) > 4:
                closes.append(float(candle[4]))

        # 🔥 FIX 3: Ensure enough data
        if len(closes) < 10:
            print("Not enough data")
            return None

        return closes

    except Exception as e:
        print("Binance fetch error:", e)
        return None


# =========================
# RSI
# =========================
def calculate_rsi(prices):
    gains, losses = [], []

    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))

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

    return direction, confidence, rsi, current_price


# =========================
# TIME CALCULATION (KEY FIX)
# =========================
def get_next_entry_time():
    now = datetime.now()

    # Round to next candle
    minute = (now.minute // TIMEFRAME + 1) * TIMEFRAME
    entry_time = now.replace(second=0, microsecond=0)

    if minute >= 60:
        entry_time = entry_time.replace(minute=0) + timedelta(hours=1)
    else:
        entry_time = entry_time.replace(minute=minute)

    return entry_time


def format_time(dt):
    return dt.strftime("%I:%M %p")


# =========================
# SEND SIGNAL
# =========================
async def send_signal(pair):
    direction, confidence, rsi, entry_price = analyze(pair)

    if direction is None or confidence < 75:
        return None, None

    entry_time = get_next_entry_time()
    signal_time = entry_time - timedelta(minutes=TIMEFRAME)  # 🔥 SEND EARLY

    expiry_time = entry_time + timedelta(minutes=EXPIRY_MINUTES)
    mg1 = expiry_time
    mg2 = expiry_time + timedelta(minutes=EXPIRY_MINUTES)

    signal = "🟩 HIGHER" if direction == "BUY" else "🟥 LOWER"

    message = f"""🚀 MARVEL-CORE AI SIGNAL

Pair: {pair}
Timeframe: {TIMEFRAME}m
Direction: {signal}

RSI: {round(rsi, 2)}
Confidence: {confidence}%

Signal Time: {format_time(signal_time)}
Entry Time: {format_time(entry_time)}
Expiry: {format_time(expiry_time)}

Martingale:
Level 1 -> {format_time(mg1)}
Level 2 -> {format_time(mg2)}

Entry Price: {entry_price}
"""

    await safe_send(message)

    return entry_price, direction


# =========================
# CHECK RESULT
# =========================
async def check_result(pair, entry_price, direction, entry_time):
    wait_time = (entry_time - datetime.now()).total_seconds()

    if wait_time > 0:
        await asyncio.sleep(wait_time)

    await asyncio.sleep(EXPIRY_MINUTES * 60)

    prices = get_prices(pair)
    if prices is None:
        return

    current_price = prices[-1]

    if direction == "BUY":
        result = "WIN ✅" if current_price > entry_price else "LOSS ❌"
    else:
        result = "WIN ✅" if current_price < entry_price else "LOSS ❌"

    message = f"""📊 RESULT

{pair}
Entry: {entry_price}
Exit: {current_price}

{result}
"""

    await safe_send(message)


# =========================
# MAIN LOOP
# =========================
async def main():
    print("Bot running with smart timing...")

    while True:
        try:
            for pair in PAIRS:
                entry_price, direction = await send_signal(pair)

            await asyncio.sleep(60)  # check every minute

        except Exception as e:
            print("Main loop error:", e)
            await asyncio.sleep(10)


asyncio.run(main())
