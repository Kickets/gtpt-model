from alpaca_trade_api.rest import REST
from dotenv import load_dotenv
import os
from datetime import datetime

# Load .env
load_dotenv()
API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

api = REST(API_KEY, SECRET_KEY, BASE_URL)

def track_real_time_profit():
    positions = api.list_positions()
    if not positions:
        print("No open positions.")
        return

    print(f"\n📊 Real-Time P/L Report ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print("--------------------------------------------------")
    total_pl = 0

    for pos in positions:
        symbol = pos.symbol
        qty = float(pos.qty)
        avg_entry = float(pos.avg_entry_price)
        current_price = float(pos.current_price)
        unrealized_pl = float(pos.unrealized_pl)

        print(f"{symbol}: {qty} shares | Avg: ${avg_entry:.2f} | Now: ${current_price:.2f} | P/L: ${unrealized_pl:.2f}")
        total_pl += unrealized_pl

    print("--------------------------------------------------")
    print(f"💰 Total Unrealized P/L: ${total_pl:.2f}\n")

if __name__ == "__main__":
    track_real_time_profit()
