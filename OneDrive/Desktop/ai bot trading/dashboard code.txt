import streamlit as st
st.set_page_config(page_title="Trading Bot Dashboard", layout="wide")

import pandas as pd
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import altair as alt
from alpaca_trade_api.rest import REST
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("APCA_API_KEY_ID")
SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

api = REST(API_KEY, SECRET_KEY, BASE_URL)

# Auto-refresh every 30 seconds
st_autorefresh(interval=30 * 1000, limit=None, key="refresh")

# File paths
log_file = "trade_log.csv"
trail_file = "trailing_stops.csv"
unrealized_log_file = "unrealized_pl_log.csv"

st.title("📊 AI Trading Bot Dashboard")

# ---- OPEN POSITIONS ----
st.subheader("📈 Open Positions")
if os.path.exists(trail_file):
    df_trail = pd.read_csv(trail_file)
    df_trail["EntryTime"] = pd.to_datetime(df_trail["EntryTime"])
    held = datetime.now() - df_trail["EntryTime"]
    df_trail["Held For"] = (held.dt.total_seconds() // 60).astype(int).astype(str) + " min"
    st.dataframe(df_trail[["Symbol", "Qty", "Entry", "Highest", "Held For"]])
else:
    st.info("No open positions.")

# ---- UNREALIZED P/L ----
st.subheader("💸 Live Unrealized P/L")

total_unrealized = 0

try:
    positions = api.list_positions()
    if positions:
        unrealized_data = []

        for pos in positions:
            symbol = pos.symbol
            qty = float(pos.qty)
            current_price = float(pos.current_price)
            avg_price = float(pos.avg_entry_price)
            unrealized = (current_price - avg_price) * qty
            total_unrealized += unrealized
            unrealized_data.append({
                "Symbol": symbol,
                "Qty": qty,
                "Avg Price": round(avg_price, 2),
                "Current Price": round(current_price, 2),
                "Unrealized P/L": round(unrealized, 2)
            })

        df_unrealized = pd.DataFrame(unrealized_data)
        st.dataframe(df_unrealized)
        st.metric("📊 Total Unrealized P/L", f"${total_unrealized:.2f}")

        # ---- LOG UNREALIZED P/L ----
        now = datetime.now()
        log_entry = pd.DataFrame([{
            "Timestamp": now,
            "Unrealized_PnL": total_unrealized
        }])

        if os.path.exists(unrealized_log_file):
            old_log = pd.read_csv(unrealized_log_file)
            full_log = pd.concat([old_log, log_entry], ignore_index=True)
        else:
            full_log = log_entry

        full_log.to_csv(unrealized_log_file, index=False)

    else:
        st.info("No open positions currently generating unrealized P/L.")
except Exception as e:
    st.warning(f"Could not load Alpaca positions: {e}")

# ---- UNREALIZED P/L CHART ----
st.subheader("📉 Unrealized P/L Over Time")

try:
    if os.path.exists(unrealized_log_file) and os.path.getsize(unrealized_log_file) > 0:
        df_upl = pd.read_csv(unrealized_log_file)
        if df_upl.empty or "Timestamp" not in df_upl.columns:
            st.info("Unrealized P/L log file exists but is empty.")
        else:
            df_upl["Timestamp"] = pd.to_datetime(df_upl["Timestamp"])
            line_chart = alt.Chart(df_upl).mark_line(point=True).encode(
                x="Timestamp:T",
                y="Unrealized_PnL:Q",
                tooltip=["Timestamp", "Unrealized_PnL"]
            ).properties(
                title="📈 Unrealized P/L Trend",
                width=700,
                height=400
            )
            st.altair_chart(line_chart, use_container_width=True)
    else:
        st.info("No unrealized P/L history yet.")
except Exception as e:
    st.warning(f"Error loading unrealized P/L chart: {e}")

# ---- TRADE HISTORY ----
st.subheader("📜 Trade History")
if os.path.exists(log_file):
    df_log = pd.read_csv(log_file)
    df_log["Timestamp"] = pd.to_datetime(df_log["Timestamp"])
    df_log = df_log.sort_values("Timestamp", ascending=False)
    st.dataframe(df_log)
else:
    st.info("No trade log yet.")

# ---- SUMMARY STATS ----
st.subheader("📈 Summary Stats")

if os.path.exists(log_file):
    df = pd.read_csv(log_file)
    buys = df[df["Action"] == "BUY"]
    sells = df[df["Action"] == "SELL"]

    total_buys = buys.shape[0]
    total_sells = sells.shape[0]

    if total_buys and total_sells:
        merged = pd.merge(buys, sells, on="Symbol", suffixes=("_buy", "_sell"))
        merged["P/L"] = (merged["Price_sell"] - merged["Price_buy"]) * merged["Quantity_sell"]
        total_profit = merged["P/L"].sum()
        win_rate = (merged["P/L"] > 0).mean() * 100

        # Combined P/L
        realized_profit = merged["P/L"].sum()

        try:
            positions = api.list_positions()
            unrealized_total = sum(
                (float(p.current_price) - float(p.avg_entry_price)) * float(p.qty)
                for p in positions
            )
        except Exception:
            unrealized_total = 0

        combined_total = realized_profit + unrealized_total
        st.metric("🧾 Combined Total P/L", f"${combined_total:.2f}")
        st.metric("📊 Total Trades", total_sells)
        st.metric("💰 Net Profit", f"${total_profit:.2f}")
        st.metric("✅ Win Rate", f"{win_rate:.2f}%")

        # Bar chart: P/L by Symbol
        pl_by_symbol = merged.groupby("Symbol")["P/L"].sum().reset_index()
        chart = alt.Chart(pl_by_symbol).mark_bar().encode(
            x=alt.X("Symbol", sort="-y"),
            y="P/L",
            color=alt.condition(
                alt.datum["P/L"] > 0,
                alt.value("green"),
                alt.value("red")
            ),
            tooltip=["Symbol", "P/L"]
        ).properties(
            title="📊 P/L by Symbol",
            width=700,
            height=400
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Waiting for at least 1 buy and 1 sell to calculate performance.")
else:
    st.info("No stats available yet.")
