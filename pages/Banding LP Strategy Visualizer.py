import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
from datetime import datetime

st.set_page_config(layout="wide")
st.title("Banding LP Chart Builder")

# ========== ETH DATA FETCH ==========
@st.cache_data(show_spinner=False)
def fetch_eth_prices():
    url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
    params = {"vs_currency": "usd", "days": "3", "interval": "hourly"}
    r = requests.get(url, params=params)
    data = r.json()
    if "prices" not in data:
        return pd.DataFrame(columns=["timestamp", "price"])
    prices = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    prices["timestamp"] = pd.to_datetime(prices["timestamp"], unit="ms")
    return prices

eth_df = fetch_eth_prices()

# ========== USER INPUT AREA ==========
st.subheader("Paste Band 1 Block")
band_text = st.text_area("", height=200)

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Generate Chart"):
        st.session_state.band_data = band_text
with col2:
    if st.button("Refresh ETH Price"):
        eth_df = fetch_eth_prices()

if not eth_df.empty:
    st.write("Current ETH Price:", f"${eth_df['price'].iloc[-1]:,.2f}")
else:
    st.write("Current ETH Price: *Not Available*")

# ========== PARSER ==========
def parse_band_block(text):
    blocks = []
    raw = text.strip().splitlines()
    for i, line in enumerate(raw):
        if line.startswith("Band"):
            parts = {kv.split(" = ")[0].strip(): kv.split(" = ")[1].strip() for kv in line.split(" | ") if "=" in kv}
            blocks.append({
                "band": parts.get("Band 1", f"Band {i+1}"),
                "min": float(parts["Min"]),
                "max": float(parts["Max"]),
                "liq": float(parts["Liq. Price"]),
                "drop": float(parts["Liq. Drop %"]),
            })
        elif "Down" in line:
            if not blocks:
                continue
            if "drawdowns" not in blocks[-1]:
                blocks[-1]["drawdowns"] = []
            p = {kv.split(" = ")[0].strip(): kv.split(" = ")[1].strip() for kv in line.split(" | ") if "=" in kv}
            blocks[-1]["drawdowns"].append({
                "level": float(p[list(p.keys())[0]]),
                "label": list(p.keys())[0]
            })
    return blocks

# ========== CHARTING ==========
def draw_band_charts(blocks):
    for band in blocks:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
        eth_df_sorted = eth_df.sort_values("timestamp")

        # Top Chart: Band with ETH line
        ax1.plot(eth_df_sorted["timestamp"], eth_df_sorted["price"], label="ETH Price", color="green")
        ax1.axhline(band["min"], color="blue", linestyle="--", label="Band Min")
        ax1.axhline(band["max"], color="orange", linestyle="--", label="Band Max")
        ax1.set_title(f"{band['band']} Range Chart")
        ax1.set_ylabel("Price")
        ax1.legend()

        # Bottom Chart: Drawdown levels only
        for d in band.get("drawdowns", []):
            ax2.axhline(d["level"], linestyle="--", color="skyblue", label=d["label"])
        ax2.set_title(f"{band['band']} Drawdowns Chart")
        ax2.set_ylabel("Price")
        ax2.legend()

        st.pyplot(fig)

# ========== MAIN ==========
band_data = st.session_state.get("band_data", "")
if band_data:
    parsed = parse_band_block(band_data)
    if parsed:
        draw_band_charts(parsed)
    else:
        st.warning("No valid band data found.")
