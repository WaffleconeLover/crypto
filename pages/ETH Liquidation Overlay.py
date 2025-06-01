import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import time

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

# Simulated liquidation clusters (price levels and $ values)
liquidation_clusters = {
    2660: 4.8,
    2630: 7.5,
    2605: 12.2,
    2580: 18.9,
    2550: 9.3,
    2525: 5.0
}

# Manual LP range input
lp_range = (2359, 2509)
lp_top = lp_range[1]

# Current ETH price from latest HA close
current_price = klines['HA_Close'].iloc[-1]

# Compute flush probability score for each cluster
max_value = max(liquidation_clusters.values())
flush_scores = {}
for price, value in liquidation_clusters.items():
    size_score = value / max_value
    proximity = abs(price - current_price) / current_price
    proximity_score = max(0, 1 - proximity * 20)
    flush_score = round((size_score * 0.6 + proximity_score * 0.4), 2)
    flush_scores[price] = flush_score

# Plotting
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(klines['Open Time'], klines['HA_Close'], label='ETH Price (Heikin Ashi)', color='black')

# Plot LP range
ax.axhspan(lp_range[0], lp_range[1], color='green', alpha=0.2, label=f'LP Range {lp_range[0]}–{lp_range[1]}')

# Plot only liquidation clusters below LP range top
for level, value in liquidation_clusters.items():
    if level <= lp_top:
        intensity = min(1.0, value / max_value)
        score = flush_scores[level]
        ax.axhspan(level - 1, level + 1, color='red', alpha=intensity * 0.4)
        ax.text(klines['Open Time'].iloc[0], level, f"${value:.1f}M\nScore: {score}", fontsize=8, color='darkred', va='center')

# Formatting
ax.set_title("ETH Price (Heikin Ashi) with Liquidation Zones (below LP top), LP Range & Flush Scores")
ax.set_xlabel("Time")
ax.set_ylabel("Price")
ax.legend()
ax.grid(True)

st.pyplot(fig)
