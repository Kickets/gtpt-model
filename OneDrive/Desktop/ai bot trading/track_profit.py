import pandas as pd
from collections import defaultdict

# Load your trade log
df = pd.read_csv("trade_log.csv")

# Group trades by symbol
positions = defaultdict(list)
profits = []

for _, row in df.iterrows():
    action = row["Action"]
    symbol = row["Symbol"]
    qty = int(row["Quantity"])
    price = float(row["Price"])

    if action == "BUY":
        positions[symbol].append((qty, price))
    elif action == "SELL" and symbol in positions:
        remaining_qty = qty
        buys = positions[symbol]
        profit = 0

        while remaining_qty > 0 and buys:
            buy_qty, buy_price = buys[0]

            trade_qty = min(buy_qty, remaining_qty)
            trade_profit = trade_qty * (price - buy_price)
            profit += trade_profit

            if trade_qty == buy_qty:
                buys.pop(0)
            else:
                buys[0] = (buy_qty - trade_qty, buy_price)

            remaining_qty -= trade_qty

        profits.append((symbol, qty, round(profit, 2)))

# Output profits
print("\n📈 Profit Report")
print("----------------")
total = 0
for symbol, qty, profit in profits:
    print(f"{symbol} | {qty} shares | P&L: ${profit}")
    total += profit

print("----------------")
print(f"💰 Net Profit: ${round(total, 2)}")
