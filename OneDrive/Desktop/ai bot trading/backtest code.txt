import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- Config ---
TICKERS = ["AAPL", "TSLA", "BTC-USD", "ETH-USD"]
START = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
END = datetime.now().strftime("%Y-%m-%d")
INTERVAL = "15m"
BASE_BALANCE = 10000
RISK_PER_TRADE = 0.01  # 1% risk per trade
EMA_PERIOD = 50
ATR_PERIOD = 14
RSI_PERIOD = 7  # Faster RSI for scalping
VOLUME_SPIKE_MULTIPLIER = 2

# --- Indicators ---
def compute_rsi(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_atr(df, period):
    high_low = df["High"] - df["Low"]
    high_close = np.abs(df["High"] - df["Close"].shift())
    low_close = np.abs(df["Low"] - df["Close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def compute_indicators(df):
    df["EMA50"] = df["Close"].ewm(span=EMA_PERIOD, adjust=False).mean()
    df["RSI"] = compute_rsi(df["Close"], RSI_PERIOD)
    df["ema12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["ema26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema12"] - df["ema26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["ATR"] = compute_atr(df, ATR_PERIOD)
    df["vol_avg"] = df["Volume"].rolling(window=20).mean()
    return df.dropna()

# --- Pattern Recognition ---
def detect_bullish_engulfing(df):
    if len(df) < 2:
        return False
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    return (
        float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"].iloc[0]) if isinstance(prev["Close"], pd.Series) else float(prev["Close"]) < float(prev["Open"]) and
        float(curr["Close"]) > float(curr["Open"]) and
        float(curr["Close"]) > float(prev["Open"]) and
        float(curr["Open"]) < float(prev["Close"])
    )

def detect_bearish_engulfing(df):
    if len(df) < 2:
        return False
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    return (
        float(prev["Close"]) > float(prev["Open"]) and
        float(curr["Close"]) < float(curr["Open"]) and
        float(curr["Close"]) < float(prev["Open"]) and
        float(curr["Open"]) > float(prev["Close"])
    )

# --- Strategy Logic ---
def should_buy(df):
    if len(df) < 3:
        return False
    prev = df.iloc[-2]
    last = df.iloc[-1]
    rsi_crossed = float(prev["RSI"]) < 40 and float(last["RSI"]) >= 40
    macd_up = float(last["macd"]) > float(last["macd_signal"])
    above_ema50 = float(last["Close"]) > float(last["EMA50"])
    candle_confirmation = detect_bullish_engulfing(df)
    volume_spike = float(last["Volume"]) > float(last["vol_avg"]) * VOLUME_SPIKE_MULTIPLIER

    
    return rsi_crossed and macd_up and above_ema50 and candle_confirmation and volume_spike

def should_short(df):
    if len(df) < 3:
        return False
    prev = df.iloc[-2]
    last = df.iloc[-1]
    rsi_crossed = float(prev["RSI"]) > 60 and float(last["RSI"]) <= 60
    macd_down = float(last["macd"]) < float(last["macd_signal"])
    below_ema50 = float(last["Close"]) < float(last["EMA50"])
    candle_confirmation = detect_bearish_engulfing(df)
    volume_spike = float(last["Volume"]) > float(last["vol_avg"]) * VOLUME_SPIKE_MULTIPLIER

    
    return rsi_crossed and macd_down and below_ema50 and candle_confirmation and volume_spike

# --- Backtest ---
def backtest(ticker):
    df = yf.download(ticker, start=START, end=END, interval=INTERVAL)
    df = compute_indicators(df)

    balance = BASE_BALANCE
    position = 0
    entry_price = 0
    position_type = None
    trades = []
    returns = []
    peak = balance
    max_drawdown = 0

    for i in range(20, len(df)):
        row = df.iloc[i]
        price = float(row["Close"].iloc[0]) if isinstance(row["Close"], pd.Series) else float(row["Close"])
        atr = float(row["ATR"].iloc[0]) if isinstance(row["ATR"], pd.Series) else float(row["ATR"])
        risk_amount = balance * RISK_PER_TRADE
        position_size = risk_amount / (1.2 * atr) if atr > 0 else 0

        stop_loss_long = price - 1.2 * atr
        take_profit_long = price + 1.8 * atr
        stop_loss_short = price + 1.2 * atr
        take_profit_short = price - 1.8 * atr

        if position == 0:
            if should_buy(df.iloc[i - 2:i + 1]):
                position = position_size
                entry_price = price
                position_type = "LONG"
                balance -= position * price
                trades.append((ticker, "BUY", df.index[i], price))

            elif should_short(df.iloc[i - 2:i + 1]):
                position = position_size
                entry_price = price
                position_type = "SHORT"
                balance -= position * price
                trades.append((ticker, "SHORT", df.index[i], price))

        elif position > 0:
            if position_type == "LONG" and (price >= take_profit_long or price <= stop_loss_long):
                balance += position * price
                returns.append((price - entry_price) / entry_price)
                trades.append((ticker, "SELL", df.index[i], price))
                position = 0
                entry_price = 0

            elif position_type == "SHORT" and (price <= take_profit_short or price >= stop_loss_short):
                balance += position * (2 * entry_price - price)
                returns.append((entry_price - price) / entry_price)
                trades.append((ticker, "COVER", df.index[i], price))
                position = 0
                entry_price = 0

            peak = max(peak, balance)
            max_drawdown = min(max_drawdown, (balance - peak) / peak)

    if position > 0:
        final_price = float(df.iloc[-1]["Close"].iloc[0]) if isinstance(df.iloc[-1]["Close"], pd.Series) else float(df.iloc[-1]["Close"])
        if position_type == "LONG":
            balance += position * final_price
            returns.append((final_price - entry_price) / entry_price)
            trades.append((ticker, "SELL", df.index[-1], final_price))
        elif position_type == "SHORT":
            balance += position * (2 * entry_price - final_price)
            returns.append((entry_price - final_price) / entry_price)
            trades.append((ticker, "COVER", df.index[-1], final_price))

    total_return = (balance - BASE_BALANCE) / BASE_BALANCE
    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0
    profit_factor = sum(r for r in returns if r > 0) / abs(sum(r for r in returns if r < 0)) if any(r < 0 for r in returns) else float('inf')

    return trades, balance, total_return, sharpe_ratio, max_drawdown, profit_factor

import matplotlib.pyplot as plt

if __name__ == "__main__":
    all_trades = []
    for ticker in TICKERS:
        trades, balance, total_return, sharpe_ratio, max_drawdown, profit_factor = backtest(ticker)
        print(f"\n--- {ticker} Results ---")
        print(f"✅ Final Balance: ${balance:.2f}")
        print(f"📈 Total Return: {total_return * 100:.2f}%")
        print(f"📊 Sharpe Ratio: {sharpe_ratio:.2f}")
        print(f"📉 Max Drawdown: {max_drawdown * 100:.2f}%")
        print(f"💰 Profit Factor: {profit_factor:.2f}")
        all_trades.extend(trades)

    df_all_trades = pd.DataFrame(all_trades, columns=["Ticker", "Action", "Time", "Price"])
    print("\nAll Trades:")
    print(df_all_trades)

    # Export to CSV
    df_all_trades.to_csv("backtest_trades.csv", index=False)
    print("\n✅ Trade log exported to backtest_trades.csv")

    # Plot results
    ticker_equity_curves = {}
    for ticker in TICKERS:
        df_trades = df_all_trades[df_all_trades['Ticker'] == ticker].copy()
        if not df_trades.empty:
            df_trades.set_index("Time", inplace=True)
            df_trades.sort_index(inplace=True)
            
            # Price line with trade annotations
            plt.figure(figsize=(12, 5))
            plt.plot(df_trades.index, df_trades["Price"], marker='o', linestyle='-', label=f'{ticker} Trade Prices')
            for idx, row in df_trades.iterrows():
                color = 'green' if row['Action'] in ['BUY', 'COVER'] else 'red'
                plt.scatter(idx, row['Price'], color=color, label=row['Action'], s=50, zorder=5)
            plt.title(f"Trade Price Timeline for {ticker}")
            plt.xlabel("Time")
            plt.ylabel("Price")
            plt.grid(True)
            handles, labels = plt.gca().get_legend_handles_labels()
            if labels:
                plt.legend()
            plt.tight_layout()
            plt.savefig(f"{ticker}_trade_chart.png")  

            # Equity curve (realized profit-based version)
            equity = [BASE_BALANCE]
            balance_tracker = BASE_BALANCE
            trade_list = df_trades.reset_index()
            for i in range(1, len(trade_list), 2):
                entry = trade_list.iloc[i - 1]
                exit_ = trade_list.iloc[i]
                if entry["Action"] == "BUY" and exit_["Action"] == "SELL":
                    profit = (exit_["Price"] - entry["Price"]) * 100
                elif entry["Action"] == "SHORT" and exit_["Action"] == "COVER":
                    profit = (entry["Price"] - exit_["Price"]) * 100
                else:
                    profit = 0
                balance_tracker += profit
                equity.append(balance_tracker)

            times = trade_list.iloc[1::2]["Time"]  # exit times
            ticker_equity_curves[ticker] = (times, equity)
            ticker_equity_curves[ticker] = (df_trades.index, equity)

    # Plot multi-ticker equity curves
    plt.figure(figsize=(12, 6))
    for ticker, (times, equity) in ticker_equity_curves.items():
        plt.plot(times, equity, label=ticker)
    plt.title("Equity Curves by Ticker")
    plt.xlabel("Time")
    plt.ylabel("Equity")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("multi_ticker_equity_curve.png")
    print("📈 Multi-ticker equity chart saved to multi_ticker_equity_curve.png")
    print(f"📊 Chart saved to {ticker}_trade_chart.png")
