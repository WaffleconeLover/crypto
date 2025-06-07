import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from datetime import datetime

st.set_page_config(layout="wide")

# ---------------- LOCKED UI ELEMENTS ---------------- #
st.title("Banding LP Chart Builder")
st.markdown("### Paste Band 1 Block")
band_input = st.text_area("Band Data Input", height=150)

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Generate Chart"):
        st.session_state["band_data"] = band_input
with col2:
    refresh_price = st.button("Refresh ETH Price")

# ---------------- ETH PRICE FETCH ---------------- #
@st.cache_data(ttl=3600)
def fetch_eth_prices():
    url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
    params = {"vs_currency": "usd", "days": "3", "interval": "hourly"}
    response = requests.get(url, params=params)

    try:
        data = response.json()
        if "prices" not in data:
            st.error("CoinGecko API error. Try again later.")
            return pd.DataFrame()
        prices = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
        prices["timestamp"] = pd.to_datetime(prices["timestamp"], unit="ms")
        return prices
    except Exception as e:
        st.error(f"Failed to parse ETH price data: {e}")
        return pd.DataFrame()

if refresh_price or "eth_df" not in st.session_state:
    st.session_state["eth_df"] = fetch_eth_prices()

eth_df = st.session_state.get("eth_df", pd.DataFrame())
if not eth_df.empty:
    st.write("Current ETH Price:", f"${eth_df['price'].iloc[-1]:.2f}")
else:
    st.markdown("_Current ETH Price: Not Available_")

# ---------------- PARSING BAND DATA ---------------- #
def parse_band_block(text):
    lines = text.split("\n")
    band_data = {}
    try:
        for line in lines:
            line = line.strip()
            if line.startswith("Band"):
                parts = line.split("|")
                for part in parts:
                    k, v = part.strip().split("=", 1)
                    band_data[k.strip()] = float(v.strip().replace("%", "")) if "Drop" in k else float(v.strip())
            elif "% Down" in line:
                pct = line.split("% Down")[0].strip()
                val = float(line.split("=")[1].split("|")[0].strip())
                band_data[f"{pct}% Down"] = val
    except Exception as e:
        st.error(f"Error parsing band input: {e}")
    return band_data

# ---------------- CHARTING ---------------- #
def draw_charts(prices_df, band):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    # Band 1 Range Chart
    ax1.plot(prices_df["timestamp"], prices_df["price"], label="ETH Price", color="green")
    ax1.axhline(band["Min"], linestyle="--", color="blue", label="Band Min")
    ax1.axhline(band["Max"], linestyle="--", color="orange", label="Band Max")
    ax1.set_title("Band 1 Range Chart")
    ax1.set_ylabel("Price")
    ax1.legend()

    # Band 1 Drawdowns Chart
    ax2.axhline(band.get("5% Down", 0), linestyle="--", color="skyblue", label="5% Down")
    ax2.axhline(band.get("10% Down", 0), linestyle="--", color="skyblue", label="10% Down")
    ax2.axhline(band.get("15% Down", 0), linestyle="--", color="skyblue", label="15% Down")
    ax2.set_title("Band 1 Drawdowns Chart")
    ax2.set_ylabel("Price")
    ax2.legend()

    st.pyplot(fig)

# ---------------- PROCESS ---------------- #
band_text = st.session_state.get("band_data", "")
if band_text and not eth_df.empty:
    band_dict = parse_band_block(band_text)
    if band_dict:
        draw_charts(eth_df, band_dict)
