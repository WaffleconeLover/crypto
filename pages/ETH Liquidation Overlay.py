import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import time
from PIL import Image
import pytesseract
import re

st.set_page_config(layout="wide")

# Cached OHLC fetch from CoinGecko
@st.cache_data(ttl=3600, show_spinner=False)
def get_coingecko_ohlc():
    url = "https://api.coingecko.com/api/v3/coins/ethereum/ohlc?vs_currency=usd&days=1"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data, columns=["timestamp", "Open", "High", "Low", "Close"])
    df["Open Time"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# Initialize session state
if "price_data" not in st.session_state or "last_refresh" not in st.session_state:
    st.session_state.price_data = get_coingecko_ohlc()
    st.session_state.last_refresh = time.time()

# Manual refresh button and timer display
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("🔄 Refresh Price"):
        st.session_state.price_data = get_coingecko_ohlc()
        st.session_state.last_refresh = time.time()

elapsed = int(time.time() - st.session_state.last_refresh)
col2.caption(f"⏱️ Last refreshed {elapsed} seconds ago")

# Work on the data
klines = st.session_state.price_data.copy()

# Compute Heikin Ashi candles
klines['HA_Close'] = (klines['Open'] + klines['High'] + klines['Low'] + klines['Close']) / 4
ha_open = [(klines['Open'][0] + klines['Close'][0]) / 2]
for i in range(1, len(klines)):
    ha_open.append((ha_open[i - 1] + klines['HA_Close'][i - 1]) / 2)
klines['HA_Open'] = ha_open

# Manual LP range input
lp_range = (2359, 2509)
lp_top = lp_range[1]

# Simulated default liquidation clusters
default_clusters = {
    2660: 4.8,
    2630: 7.5,
    2605: 12.2,
    2580: 18.9,
    2550: 9.3,
    2525: 5.0
}

# Current ETH price from latest HA close
current_price = klines['HA_Close'].iloc[-1]

# Placeholder for OCR clusters
cluster_dict = {}

# Compute flush scores for default clusters
def compute_scores(clusters):
    max_value = max(clusters.values()) if clusters else 1
    scores = {}
    for price, value in clusters.items():
        size_score = value / max_value
        proximity = abs(price - current_price) / current_price
        proximity_score = max(0, 1 - proximity * 20)
        flush_score = round((size_score * 0.6 + proximity_score * 0.4), 2)
        scores[price] = flush_score
    return scores

# Main plotting
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(klines['Open Time'], klines['HA_Close'], label='ETH Price (Heikin Ashi)', color='black')
ax.axhspan(lp_range[0], lp_range[1], color='green', alpha=0.2, label=f'LP Range {lp_range[0]}–{lp_range[1]}')

# Use default clusters first
flush_scores = compute_scores(default_clusters)
for level, value in default_clusters.items():
    if level <= lp_top:
        intensity = min(1.0, value / max(default_clusters.values()))
        score = flush_scores[level]
        ax.axhspan(level - 1, level + 1, color='red', alpha=intensity * 0.4)
        ax.text(klines['Open Time'].iloc[0], level, f"${value:.1f}M\nScore: {score}", fontsize=8, color='darkred', va='center')

# Format chart
ax.set_title("ETH Price (Heikin Ashi) with Liquidation Zones (below LP top), LP Range & Flush Scores")
ax.set_xlabel("Time")
ax.set_ylabel("Price")
ax.legend()
ax.grid(True)

# Display chart
st.pyplot(fig)

# OCR upload (centered below chart)
st.markdown("---")
st.markdown("<h4 style='text-align: center;'>📷 Upload CoinGlass Heatmap for OCR</h4>", unsafe_allow_html=True)
uploaded_file = st.file_uploader("Upload screenshot (PNG or JPG)", type=["png", "jpg", "jpeg"], label_visibility="collapsed")

# OCR extraction
if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Heatmap", use_column_width=True)

    with st.spinner("Extracting text with OCR..."):
        image = Image.open(uploaded_file)
        raw_text = pytesseract.image_to_string(image)

        dollar_matches = re.findall(r"\$?(\d{1,3}\.\d)M", raw_text)
        price_matches = re.findall(r"(\d{4})", raw_text)

        for price, value in zip(price_matches, dollar_matches):
            try:
                price_int = int(price)
                value_float = float(value)
                cluster_dict[price_int] = round(value_float, 1)
            except:
                continue

    if cluster_dict:
        st.success(f"✅ Extracted {len(cluster_dict)} liquidation zones")
        st.code(f"liquidation_clusters = {cluster_dict}", language="python")
        if st.checkbox("✅ Replace chart with extracted clusters"):
            st.rerun()
    else:
        st.warning("⚠️ No zones detected. Try zooming in or sharpening the screenshot.")
