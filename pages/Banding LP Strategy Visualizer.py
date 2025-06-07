import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
from datetime import datetime

st.set_page_config(page_title="Banding LP Strategy Visualizer", layout="wide")
st.title("Banding LP Chart Builder")

# === DO NOT DELETE THIS UI BLOCK ===
st.subheader("Paste Band 1 Block")
band_input = st.text_area("Band Data Input", height=150, label_visibility="collapsed")

col1, col2 = st.columns([1, 1])
with col1:
    generate = st.button("Generate Chart")
with col2:
    refresh_price = st.button("Refresh ETH Price")
# === END UI BLOCK ===

# === ETH PRICE FETCHING ===
@st.cache_data(show_spinner=False)
def fetch_eth_prices():
    url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
    params = {"vs_currency": "usd", "days": "3", "interval": "hourly"}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "prices" not in data:
            return pd.DataFrame(columns=["timestamp", "price"])
        prices = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
        prices["timestamp"] = pd.to_datetime(prices["timestamp"], unit="ms")
        return prices
    except Exception as e:
        print(f"Error fetching ETH prices: {e}")
        return pd.DataFrame(columns=["timestamp", "price"])

if refresh_price:
    eth_df = fetch_eth_prices()
    st.session_state["eth_df"] = eth_df

eth_df = st.session_state.get("eth_df", fetch_eth_prices())
if not eth_df.empty:
    st.write("Current ETH Price:", f"${eth_df['price'].iloc[-1]:.2f}")
else:
    st.error("CoinGecko API error. Try again later.")
    st.write("Current ETH Price: *Not Available*")

# === BAND PARSING ===
def parse_band_block(text):
    lines = text.strip().split("\n")
    bands = []
    current = {}
    for line in lines:
        if line.startswith("Band"):
            parts = line.split("|")
            for part in parts:
                if "Min" in part:
                    current["min"] = float(part.split("=")[1].strip())
                elif "Max" in part:
                    current["max"] = float(part.split("=")[1].strip())
                elif "Liq. Price" in part:
                    current["liq"] = float(part.split("=")[1].strip())
                elif "Drop %" in part:
                    current["drop"] = float(part.split("=")[1].strip())
        elif line.strip().endswith("%") is False and "Down" in line:
            parts = line.split("|")
            label = line.split("=")[0].strip()
            try:
                draw_price = float(parts[0].split("=")[1].strip())
                current.setdefault("drawdowns", []).append((label, draw_price))
            except:
                pass
    if current:
        bands.append(current)
    return bands

# === CHARTING ===
def draw_charts(eth_df, band):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Top chart: Band Range
    ax1.plot(eth_df["timestamp"], eth_df["price"], color="green", label="ETH Price")
    ax1.axhline(band["min"], linestyle="--", color="blue", label="Band Min")
    ax1.axhline(band["max"], linestyle="--", color="orange", label="Band Max")
    ax1.set_title("Band 1 Range Chart")
    ax1.set_ylabel("Price")
    ax1.legend()

    # Bottom chart: Drawdowns
    for label, level in band.get("drawdowns", []):
        ax2.axhline(level, linestyle="--", label=label, color="skyblue")
    ax2.set_title("Band 1 Drawdowns Chart")
    ax2.set_ylabel("Price")
    ax2.legend()

    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H'))
    fig.autofmt_xdate()
    st.pyplot(fig)

# === MAIN ACTION ===
if generate and band_input:
    parsed_bands = parse_band_block(band_input)
    if parsed_bands and not eth_df.empty:
        draw_charts(eth_df, parsed_bands[0])
    else:
        st.warning("Invalid band data or ETH prices unavailable.")
