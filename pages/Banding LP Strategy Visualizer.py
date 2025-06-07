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

# -- Convert to Heikin-Ashi candles --
def compute_heikin_ashi(df):
    ha_df = pd.DataFrame(index=df.index)
    ha_df["close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = [(df["open"].iloc[0] + df["close"].iloc[0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i - 1] + ha_df["close"].iloc[i - 1]) / 2)
    ha_df["open"] = ha_open
    ha_df["high"] = df[["high", "open", "close"]].max(axis=1)
    ha_df["low"] = df[["low", "open", "close"]].min(axis=1)
    return ha_df

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
                val = val.strip().replace("%", "")
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
                    val = val.strip().replace("%", "")
                    dd_parts[key] = float(val)
            label = line.split("=")[0].strip()
            dd_levels.append((label, dd_parts["Liq. Price"]))

        # -- Get data and convert to HA candles --
        df = fetch_eth_candles()
        df.set_index("timestamp", inplace=True)
        ha_df = compute_heikin_ashi(df)

        # -- Plot Charts --
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

        # Chart 1: Heikin-Ashi + Band Range
        ax1.plot(ha_df.index, ha_df["close"], label="ETH Price", color="green")
        ax1.axhline(band_min, color="orange", linestyle="--", label="Min")
        ax1.axhline(band_max, color="darkgreen", linestyle="--", label="Max")
        ax1.set_title("Band 1 Range")
        ax1.set_ylabel("Price")
        ax1.legend()

        # Chart 2: Drawdowns from ETH spot
        ax2.axhline(eth_price * 0.95, linestyle="--", label=f"5% Down = {int(eth_price * 0.95)}", color="skyblue")
        ax2.axhline(eth_price * 0.90, linestyle="--", label=f"10% Down = {int(eth_price * 0.90)}", color="skyblue")
        ax2.axhline(eth_price * 0.85, linestyle="--", label=f"15% Down = {int(eth_price * 0.85)}", color="skyblue")
        ax2.set_title("Band 1 Drawdowns")
        ax2.set_ylabel("Price")
        ax2.legend()

        st.pyplot(fig)

    except Exception as e:
        st.error(f"Failed to parse data or generate chart: {e}")
