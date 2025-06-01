import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import requests
import time

st.set_page_config(layout="wide")

# Cached ETH OHLC data
@st.cache_data(ttl=3600)
def get_coingecko_ohlc():
    url = "https://api.coingecko.com/api/v3/coins/ethereum/ohlc?vs_currency=usd&days=1"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data, columns=["timestamp", "Open", "High", "Low", "Close"])
    df["Open Time"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# Initialize session state
if "price_data" not in st.session_state:
    st.session_state.price_data = get_coingecko_ohlc()
    st.session_state.last_refresh = time.time()
if "custom_clusters" not in st.session_state:
    st.session_state.custom_clusters = {}
if "lp_range" not in st.session_state:
    st.session_state.lp_range = (2500, 2600)

# Price refresh + timer
col1, col2 = st.columns([1, 6])
with col1:
    if st.button("🔄 Refresh Price"):
        st.session_state.price_data = get_coingecko_ohlc()
        st.session_state.last_refresh = time.time()

elapsed = int(time.time() - st.session_state.last_refresh)
with col1:
    st.caption(f"⏱️ Last refreshed {elapsed} seconds ago")

# Data prep
klines = st.session_state.price_data.copy()
klines['HA_Close'] = (klines['Open'] + klines['High'] + klines['Low'] + klines['Close']) / 4
ha_open = [(klines['Open'][0] + klines['Close'][0]) / 2]
for i in range(1, len(klines)):
    ha_open.append((ha_open[i - 1] + klines['HA_Close'][i - 1]) / 2)
klines['HA_Open'] = ha_open

current_price = klines['HA_Close'].iloc[-1]

# Manual LP range
with st.sidebar.expander("📘 LP Range Input", expanded=True):
    lp_low = st.number_input("LP Range Start", value=st.session_state.lp_range[0])
    lp_high = st.number_input("LP Range End", value=st.session_state.lp_range[1])
    if lp_low < lp_high:
        st.session_state.lp_range = (lp_low, lp_high)
    else:
        st.warning("Start must be less than end")

# Manual liquidation cluster input
with st.sidebar.expander("🔥 Add Liquidation Clusters", expanded=True):
    price = st.number_input("Cluster Price", step=1)
    value = st.number_input("Cluster $M", step=0.1)
    if st.button("Add Cluster"):
        st.session_state.custom_clusters[int(price)] = round(value, 1)

# Delete cluster(s)
if st.session_state.custom_clusters:
    with st.sidebar.expander("🗑️ Remove Clusters"):
        to_delete = st.multiselect("Select price levels to remove", list(st.session_state.custom_clusters.keys()))
        if st.button("Remove Selected"):
            for p in to_delete:
                st.session_state.custom_clusters.pop(p, None)

# Filter clusters below LP range
filtered_clusters = {p: v for p, v in st.session_state.custom_clusters.items() if p <= st.session_state.lp_range[1]}

# Flush score logic
flush_scores = {}
if filtered_clusters:
    max_value = max(filtered_clusters.values())
    for price, value in filtered_clusters.items():
        size_score = value / max_value
        proximity = abs(price - current_price) / current_price
        proximity_score = max(0, 1 - proximity * 20)
        flush_score = round((size_score * 0.6 + proximity_score * 0.4), 2)
        flush_scores[price] = flush_score

# Plot
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(klines['Open Time'], klines['HA_Close'], label='ETH Price (Heikin Ashi)', color='black')

# LP Range
lp_low, lp_high = st.session_state.lp_range
ax.axhspan(lp_low, lp_high, color='green', alpha=0.2, label=f'LP Range {lp_low}–{lp_high}')

# Liquidation zones
if filtered_clusters:
    max_value = max(filtered_clusters.values())
    for level, value in filtered_clusters.items():
        intensity = min(1.0, value / max_value)
        score = flush_scores.get(level, 0)
        ax.axhspan(level - 1, level + 1, color='red', alpha=intensity * 0.4)
        ax.text(klines['Open Time'].iloc[0], level, f"${value:.1f}M\nScore: {score}", fontsize=8, color='darkred', va='center')

# Final touches
ax.set_title("ETH Price (Heikin Ashi) with LP Range + Liquidation Zones")
ax.set_xlabel("Time")
ax.set_ylabel("Price")
ax.legend()
ax.grid(True)
st.pyplot(fig)
