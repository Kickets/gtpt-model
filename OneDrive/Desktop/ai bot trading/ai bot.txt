import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from alpaca_trade_api.rest import REST, TimeFrame
from dotenv import load_dotenv

# Load API credentials from .env
load_dotenv()
API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

api = REST(API_KEY, SECRET_KEY, BASE_URL)

# Config
TICKERS = ["AAPL", "TSLA", "AMD", "NVDA", "MSFT", "GOOGL", "META", "NFLX", "BABA", "INTC", "BA", "SHOP", "PYPL"]
INVEST_PER_TRADE = 200  # Amount in USD per trade
TAKE_PROFIT = 1.03       # 3% profit
STOP_LOSS = 0.97         # 3% loss

import csv

TRAILING_STOP_FILE = "trailing_stops.csv"

def update_trailing_stop(symbol, entry_price, current_price, qty):
    import csv

    file_exists = os.path.isfile(TRAILING_STOP_FILE)
    rows = []

    now = datetime.now().isoformat()

    # Load existing rows
    if file_exists:
        with open(TRAILING_STOP_FILE, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                rows.append(row)

    # Update or add row
    updated = False
    for row in rows:
        if row["Symbol"] == symbol:
            row["Highest"] = str(max(float(row["Highest"]), current_price))
            updated = True
            break

    if not updated:
        rows.append({
            "Symbol": symbol,
            "Entry": str(entry_price),
            "Highest": str(current_price),
            "Qty": str(qty),
            "EntryTime": now
        })

    # Save back
    with open(TRAILING_STOP_FILE, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["Symbol", "Entry", "Highest", "Qty", "EntryTime"])
        writer.writeheader()
        writer.writerows(rows)

def log_trade(action, symbol, qty, price):
    file_exists = os.path.isfile("trade_log.csv")
    with open("trade_log.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "Action", "Symbol", "Quantity", "Price"])
        writer.writerow([datetime.now(), action, symbol, qty, price])

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_price_data(ticker):
    data = yf.download(ticker, period="10d", interval="30m")
    return data


def is_bullish_candle(df):
    body = df["Close"] - df["Open"]
    wick_top = df["High"] - df[["Close", "Open"]].max(axis=1)
    wick_bottom = df[["Close", "Open"]].min(axis=1) - df["Low"]

    prev_body = df["Close"].shift(1) - df["Open"].shift(1)
    engulfing = (body > abs(prev_body)) & ((body > 0) & (prev_body < 0))

    hammer = (
        (body > 0) &
        (wick_bottom > body * 2) &
        (wick_top < body)
    )

    return (engulfing | hammer).iloc[-1]


def should_buy(ticker):
    df = yf.download(ticker, period="10d", interval="30m")
    if df.empty or len(df) < 35:
        return False

    df['ma20'] = df['Close'].rolling(window=20).mean()
    df['rsi'] = compute_rsi(df['Close'], 14)
    df['ema12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['ema26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema12'] - df['ema26']
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['avg_volume'] = df['Volume'].rolling(window=20).mean()

    current_price = float(df['Close'].iloc[-1].item())
    ma20_val = float(df['ma20'].iloc[-1].item())
    rsi_val = float(df['rsi'].iloc[-1].item())
    macd = float(df['macd'].iloc[-1].item())
    macd_signal = float(df['macd_signal'].iloc[-1].item())
    volume = float(df['Volume'].iloc[-1].item())
    avg_volume = float(df['avg_volume'].iloc[-1].item())

    df_1h = yf.download(ticker, period="10d", interval="60m")
    if df_1h.empty or len(df_1h) < 35:
        return False

    df_1h['ema12'] = df_1h['Close'].ewm(span=12, adjust=False).mean()
    df_1h['ema26'] = df_1h['Close'].ewm(span=26, adjust=False).mean()
    df_1h['macd'] = df_1h['ema12'] - df_1h['ema26']
    df_1h['macd_signal'] = df_1h['macd'].ewm(span=9, adjust=False).mean()
    macd_1h = float(df_1h["macd"].iloc[-1].item())
    macd_sig_1h = float(df_1h["macd_signal"].iloc[-1].item())

    return (
        current_price > ma20_val and
        30 < rsi_val < 70 and
        macd > macd_signal and
        macd_1h > macd_sig_1h and
        volume > avg_volume and
        is_bullish_candle(df)
    )


def place_trade(ticker):
    try:
        current_price = yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
        qty = int(INVEST_PER_TRADE / current_price)
        if qty < 1:
            print(f"Not enough funds to trade {ticker}")
            return

        # Submit a LIMIT order slightly above market to guarantee a fill
        order = api.submit_order(
            symbol=ticker,
            qty=qty,
            side="buy",
            type="limit",
            time_in_force="day",
            limit_price=round(current_price + 1, 2),
            extended_hours=True
        )

        # Wait and confirm order was filled
        import time
        time.sleep(2)  # Give Alpaca time to process

        order_status = api.get_order(order.id)
        if order_status.filled_at:
            update_trailing_stop(ticker, current_price, current_price, qty)
            log_trade("BUY", ticker, qty, round(current_price, 2))
            print(f"[{datetime.now()}] Bought {qty} shares of {ticker} at ${current_price:.2f}")
        else:
            print(f"[{datetime.now()}] Order for {ticker} was submitted but not filled.")
    except Exception as e:
        print(f"Error placing trade for {ticker}: {e}")

def sell_positions():
    import csv
    trailing_data = {}

    # Load trailing stop data
    if os.path.isfile(TRAILING_STOP_FILE):
        with open(TRAILING_STOP_FILE, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                trailing_data[row["Symbol"]] = row

    positions = api.list_positions()
    for pos in positions:
        symbol = pos.symbol
        qty = int(float(pos.qty))
        current_price = float(api.get_latest_trade(symbol).price)

        if symbol in trailing_data:
            entry = float(trailing_data[symbol]["Entry"])
            highest = float(trailing_data[symbol]["Highest"])
            entry_time = datetime.fromisoformat(trailing_data[symbol]["EntryTime"])
            time_held = datetime.now() - entry_time

            # Time-dependent trailing stop
            if time_held >= timedelta(hours=6):
                reason = "Timed Exit (6hr max hold)"
                exit_triggered = True
            else:
                new_high = max(highest, current_price)
                trailing_data[symbol]["Highest"] = str(new_high)
                drop_pct = current_price / new_high

                if time_held >= timedelta(hours=3):
                    trailing_threshold = 0.985  # tighter: 1.5%
                else:
                    trailing_threshold = 0.97  # standard: 3%

                exit_triggered = drop_pct <= trailing_threshold
                reason = f"Trailing Stop {round((1 - trailing_threshold) * 100, 1)}%"

            if exit_triggered:
                try:
                    order = api.submit_order(
                        symbol=symbol,
                        qty=qty,
                        side="sell",
                        type="market",
                        time_in_force="day",
                        extended_hours=True
                    )

                    time.sleep(2)
                    order_status = api.get_order(order.id)

                    if order_status.filled_at:
                        log_trade("SELL", symbol, qty, round(current_price, 2))
                        print(f"[{datetime.now()}] Sold {qty} shares of {symbol} at ${current_price:.2f} ({reason})")
                        del trailing_data[symbol]
                except Exception as e:
                    print(f"Error selling {symbol}: {e}")

    # Save updated trailing data
    with open(TRAILING_STOP_FILE, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["Symbol", "Entry", "Highest", "Qty", "EntryTime"])
        writer.writeheader()
        for row in trailing_data.values():
            writer.writerow(row)

def run_bot():
    print(f"[{datetime.now()}] Starting bot...")
    sell_positions()
    for ticker in TICKERS:
        if should_buy(ticker):
            place_trade(ticker)
    print(f"[{datetime.now()}] Bot finished.")

if __name__ == "__main__":
    run_bot()
