import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(layout="wide")
st.title("ETH Liquidity Band Dashboard")

# -- Constants --
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/pairs/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
COINGECKO_API = "https://api.coingecko.com/api/v3/coins/ethereum/ohlc?vs_currency=usd&days=1"

# -- Fetch ETH price from Dexscreener --
@st.cache_data(ttl=60)
def fetch_eth_spot():
    try:
        r = requests.get(DEXSCREENER_API)
        r.raise_for_status()
        data = r.json()
        return float(data["pair"]["priceUsd"])
    except:
        return None

# -- Fetch OHLC data from CoinGecko for candles --
@st.cache_data(ttl=300)
def fetch_eth_candles():
    try:
        r = requests.get(COINGECKO_API)
        r.raise_for_status()
        raw = r.json()
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except:
        return None

# -- UI --
st.subheader("1. Refresh ETH Price")
col1, col2 = st.columns([2, 2])

with col1:
    if st.button("Refresh ETH Price"):
        st.session_state.eth_price = fetch_eth_spot()

eth_price = st.session_state.get("eth_price", fetch_eth_spot())
if eth_price:
    st.markdown(f"**Latest ETH Price:** ${eth_price:,.2f}")
else:
    st.error("Failed to fetch ETH price data.")

st.markdown("---")
st.subheader("2. Paste Band Data")
st.caption("Paste band and drawdown data below:")
band_input = st.text_area("Band Data Input", height=150)

if st.button("Submit Band Info") and band_input:
    lines = band_input.strip().split("\n")
    band_line = lines[0]
    dd_lines = lines[1:]

    try:
        # -- Parse Band --
        parts = {}
        for kv in band_line.split("|"):
            if "=" in kv:
                key, val = kv.split("=")
                key = key.strip()
                val = val.strip().replace("%", "")  # FIXED HERE
                parts[key] = float(val)

        band_min = parts["Min"]
        band_max = parts["Max"]

        # -- Parse Drawdowns --
        dd_levels = []
        for line in dd_lines:
            dd_parts = {}
            for kv in line.split("|"):
                if "=" in kv:
                    key, val = kv.split("=")
                    key = key.strip()
                    val = val.strip().replace("%", "")  # FIXED HERE
                    dd_parts[key] = float(val)
            label = line.split("=")[0].strip()
            dd_levels.append((label, dd_parts["Liq. Price"]))

        # -- Plot Charts --
        df = fetch_eth_candles()

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

        # Chart 1: Candlestick + Range
        if df is not None:
            ax1.plot(df["timestamp"], df["close"], label="ETH Price", color="green")
        ax1.axhline(band_min, color="orange", linestyle="--", label="Min")
        ax1.axhline(band_max, color="green", linestyle="--", label="Max")
        ax1.set_title("Band 1 Range")
        ax1.set_ylabel("Price")
        ax1.legend()

        # Chart 2: Drawdowns
        for label, price in dd_levels:
            ax2.axhline(price, linestyle="--", label=f"{label} = {int(price)}", color="skyblue")
        ax2.set_title("Band 1 Drawdowns")
        ax2.set_ylabel("Price")
        ax2.legend()

        st.pyplot(fig)

    except Exception as e:
        st.error(f"Failed to parse data or generate chart: {e}")
