import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
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
def fetch_eth_candles(dummy_cache_buster=None):  # added param
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
        st.session_state.last_refresh = datetime.now().isoformat()  # set timestamp

eth_price = st.session_state.get("eth_price", fetch_eth_spot())
if eth_price:
    st.markdown(f"**Latest ETH Price:** ${eth_price:,.2f}")
else:
    st.error("Failed to fetch ETH price data.")

st.markdown("---")
st.subheader("2. Paste Band Data")
st.caption("Paste band and drawdown data below:")
band_input = st.text_area("Band Data Input", height=150)

# -- Chart rendering function --
def render_charts(input_text):
    lines = input_text.strip().split("\n")
    band_line = lines[0]
    dd_lines = lines[1:]

    try:
        # -- Parse Band --
        parts = {}
        band_label = band_line.split("|")[0].strip() if "|" in band_line else "Band"

        for kv in band_line.split("|"):
            if "=" in kv:
                key, val = kv.split("=")
                key = key.strip()
                val = val.strip().replace("%", "")
                parts[key] = float(val)

        band_min = parts["Min"]
        band_max = parts["Max"]

        # -- Parse Drawdowns from "X Down = Y" format --
        dd_levels = []
        for line in dd_lines:
            for kv in line.split("|"):
                if "Down" in kv and "=" in kv:
                    label, val = kv.split("=")
                    dd_levels.append((label.strip(), float(val.strip())))
                    break

        # -- Get data and convert to HA candles --
        df = fetch_eth_candles(st.session_state.get("last_refresh"))  # bust cache if needed
        df.set_index("timestamp", inplace=True)
        ha_df = compute_heikin_ashi(df)

        # -- mplfinance plot (candles) --
        ha_plot_df = ha_df[["open", "high", "low", "close"]].copy()
        ha_plot_df.index.name = "Date"

        ap_lines = [
            mpf.make_addplot([band_min] * len(ha_plot_df), color='orange', linestyle='--'),
            mpf.make_addplot([band_max] * len(ha_plot_df), color='green', linestyle='--')
        ]

        fig_mpf, _ = mpf.plot(
            ha_plot_df,
            type='candle',
            style='charles',
            ylabel="Price",
            title=f"{band_label} Range (Heikin-Ashi)",
            addplot=ap_lines,
            figsize=(10, 5),
            returnfig=True
        )
        st.pyplot(fig_mpf)

        # -- Drawdowns using actual pasted values --
        fig, ax2 = plt.subplots(figsize=(10, 3))
        for label, price in dd_levels:
            ax2.axhline(price, linestyle="--", label=f"{label} = {int(price)}", color="skyblue")
        ax2.set_title(f"{band_label} Drawdowns")
        ax2.set_ylabel("Price")
        ax2.legend()
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Failed to parse data or generate chart: {e}")

# -- On submit: store band input
if st.button("Submit Band Info") and band_input:
    st.session_state.band_input = band_input.strip()

# -- Re-render chart if band_input exists in session (e.g. after refresh)
if "band_input" in st.session_state:
    render_charts(st.session_state["band_input"])
