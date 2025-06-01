import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import time
import mplfinance as mpf

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
with col1:
    st.caption(f"⏱️ Last refreshed {elapsed} seconds ago")

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
lp_range = (2575, 2595)

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

# Prepare data for mplfinance Heikin Ashi chart
mpf_data = klines[['Open Time', 'HA_Open', 'High', 'Low', 'HA_Close']].copy()
mpf_data.rename(columns={
    'Open Time': 'Date',
    'HA_Open': 'Open',
    'HA_Close': 'Close'
}, inplace=True)
mpf_data.set_index('Date', inplace=True)

# Add horizontal lines for liquidation clusters
liquidation_lines = []
for level, value in liquidation_clusters.items():
    line = mpf.make_addplot(
        [level] * len(mpf_data),
        type='line',
        color='red',
        width=0.5,
        panel=0,
        alpha=min(1.0, value / max_value) * 0.4
    )
    liquidation_lines.append(line)

# Build figure with overlays
fig, axlist = mpf.plot(
    mpf_data,
    type='candle',
    style='yahoo',
    addplot=liquidation_lines,
    ylabel='ETH Price',
    title='ETH Heikin Ashi with Liquidation Zones, LP Range & Flush Scores',
    fill_between=dict(y1=lp_range[0], y2=lp_range[1], color='lightgreen', alpha=0.2),
    returnfig=True,
    figsize=(12, 6)
)

# Annotate with flush score labels
ax = axlist[0]
for level, value in liquidation_clusters.items():
    score = flush_scores[level]
    ax.text(mpf_data.index[0], level, f"${value:.1f}M\nScore: {score}", fontsize=8, color='darkred', va='center')

# Display in Streamlit
st.pyplot(fig)
