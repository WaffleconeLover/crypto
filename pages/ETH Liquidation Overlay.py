# ETH Price with Liquidation Zones & LP Range (Live, 24h Heikin Ashi + Flush Scoring)
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

# Pull Binance 30-minute ETH/USDT klines (last 24h = 48 candles)
def get_binance_klines(symbol="ETHUSDT", interval="30m", limit=48):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        st.error("❌ Failed to fetch Binance data. API may be down or blocked by host.")
        st.stop()

    return pd.DataFrame(data, columns=[
        'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close Time', 'Quote Volume', 'Trades',
        'Taker Buy Base', 'Taker Buy Quote', 'Ignore'
    ])

# Get the klines
klines = get_binance_klines()

# Convert to proper format
for col in ['Open', 'High', 'Low', 'Close']:
    klines[col] = klines[col].astype(float)
klines['Time'] = pd.to_datetime(klines['Open Time'], unit='ms')

# Compute Heikin Ashi candles
klines['HA_Close'] = (klines['Open'] + klines['High'] + klines['Low'] + klines['Close']) / 4
ha_open = [(klines['Open'][0] + klines['Close'][0]) / 2]
for i in range(1, len(klines)):
    ha_open.append((ha_open[i-1] + klines['HA_Close'][i-1]) / 2)
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
    proximity_score = max(0, 1 - proximity * 20)  # full score if <5% away
    flush_score = round((size_score * 0.6 + proximity_score * 0.4), 2)
    flush_scores[price] = flush_score

# Plotting
fig, ax = plt.subplots(figsize=(12, 6))

# Plot Heikin Ashi price line
ax.plot(klines['Time'], klines['HA_Close'], label='ETH Price (Heikin Ashi)', color='black')

# Plot LP range
ax.axhspan(lp_range[0], lp_range[1], color='green', alpha=0.2, label=f'LP Range {lp_range[0]}–{lp_range[1]}')

# Plot liquidation clusters with flush scores
for level, value in liquidation_clusters.items():
    intensity = min(1.0, value / max_value)
    score = flush_scores[level]
    ax.axhspan(level - 1, level + 1, color='red', alpha=intensity * 0.4)
    ax.text(klines['Time'].iloc[0], level, f"${value:.1f}M\nScore: {score}", fontsize=8, color='darkred', va='center')

# Formatting
ax.set_title("ETH Price (Heikin Ashi) with Liquidation Zones, LP Range & Flush Scores")
ax.set_xlabel("Time")
ax.set_ylabel("Price")
ax.legend()
ax.grid(True)

# Display in Streamlit
st.pyplot(fig)
