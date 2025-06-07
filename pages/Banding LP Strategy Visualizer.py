import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime
import requests

# =======================
# LOCKED UI BLOCK - DO NOT REMOVE
st.title("Banding LP Chart Builder")
st.markdown("**Paste Band 1 Block**")
user_input = st.text_area("", height=200)
col1, col2 = st.columns([1, 1])
generate_chart = col1.button("Generate Chart")
refresh_price = col2.button("Refresh ETH Price")
st.markdown("<style>button {margin-right: 10px !important;}</style>", unsafe_allow_html=True)
# =======================

@st.cache_data

def fetch_eth_prices():
    url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
    params = {"vs_currency": "usd", "days": "3", "interval": "hourly"}
    response = requests.get(url, params=params)
    data = response.json()
    prices = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    prices["timestamp"] = pd.to_datetime(prices["timestamp"], unit="ms")
    return prices

# Drawdown levels from band input
def parse_band_data(text):
    bands = []
    current = {}
    for line in text.splitlines():
        if line.startswith("Band"):
            current = {}
            parts = [x.strip() for x in line.split("|")]
            for part in parts:
                if "=" in part:
                    key, val = [x.strip() for x in part.split("=")]
                    current[key] = float(val.replace("%", "")) if "%" in val else float(val)
            bands.append(current)
    return bands

if refresh_price:
    st.session_state["eth_df"] = fetch_eth_prices()

eth_df = st.session_state.get("eth_df", fetch_eth_prices())
if not eth_df.empty:
    st.write("Current ETH Price:", f"${eth_df['price'].iloc[-1]:.2f}")
else:
    st.write("Current ETH Price: _Not Available_")

if generate_chart and user_input:
    bands = parse_band_data(user_input)
    if not bands:
        st.warning("No valid band data found.")
    else:
        band = bands[0]
        min_price = band["Min"]
        max_price = band["Max"]
        liq_price = band["Liq. Price"]
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

        # Top chart - range
        ax1.plot(eth_df["timestamp"], eth_df["price"], label="ETH Price", color="green")
        ax1.axhline(min_price, color="blue", linestyle="--", label="Band Min")
        ax1.axhline(max_price, color="orange", linestyle="--", label="Band Max")
        ax1.legend()
        ax1.set_title("Band 1 Range Chart")
        ax1.set_ylabel("Price")

        # Bottom chart - drawdowns
        drop_levels = [0.05, 0.10, 0.15]
        for drop in drop_levels:
            level = eth_df["price"].iloc[-1] * (1 - drop)
            ax2.axhline(level, linestyle="--", color="skyblue", label=f"{int(drop*100)}% Down")

        handles, labels = ax2.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax2.legend(by_label.values(), by_label.keys())
        ax2.set_title("Band 1 Drawdowns Chart")
        ax2.set_ylabel("Price")
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H'))
        fig.autofmt_xdate()

        st.pyplot(fig)
