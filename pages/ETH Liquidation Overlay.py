import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

# Pull ETH/USDT OHLC data from Moralis (last 24h = 48 candles)
def get_moralis_ohlcv(symbol="ethusdt", interval="30m", limit=48):
    api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjgyMDNmNDlmLTMzOWMtNDc5YS04Y2U4LTM0YzI5M2IzODU3YyIsIm9yZ0lkIjoiNDMwOTg5IiwidXNlcklkIjoiNDQzMzM1IiwidHlwZUlkIjoiMmVlOTUxYjAtOTk4ZC00NjRmLWFmZTEtM2FlZDVlNjhhMzE3IiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3MzkzNzI3NTUsImV4cCI6NDg5NTEzMjc1NX0.8GWca9PdAXaJ5ReNTdCKnMQkQ3GdEGPOj67yTw19krM"
    url = f"https://deep-index.moralis.io/api/v2/market-data/ohlcv/{symbol}?interval={interval}&limit={limit}"
    headers = {
        "X-API-Key": api_key
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json().get("result", [])
        df = pd.DataFrame(data)
        df['Open Time'] = pd.to_datetime(df['timestamp'])
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        return df
    except Exception as e:
        st.error("❌ Moralis OHLC fetch failed.")
        st.stop()

# Fetch data
klines = get_moralis_ohlcv()

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
    proximity_score = max(0, 1 - proximity * 20)  # full score if <5% away
    flush_score = round((size_score * 0.6 + proximity_score * 0.4), 2)
    flush_scores[price] = flush_score

# Plotting
fig, ax = plt.subplots(figsize=(12, 6))

# Plot Heikin Ashi price line
ax.plot(klines['Open Time'], klines['HA_Close'], label='ETH Price (Heikin Ashi)', color='black')

# Plot LP range
ax.axhspan(lp_range[0], lp_range[1], color='green', alpha=0.2, label=f'LP Range {lp_range[0]}–{lp_range[1]}')

# Plot liquidation clusters with flush scores
for level, value in liquidation_clusters.items():
    intensity = min(1.0, value / max_value)
    score = flush_scores[level]
    ax.axhspan(level - 1, level + 1, color='red', alpha=intensity * 0.4)
    ax.text(klines['Open Time'].iloc[0], level, f"${value:.1f}M\nScore: {score}", fontsize=8, color='darkred', va='center')

# Formatting
ax.set_title("ETH Price (Heikin Ashi) with Liquidation Zones, LP Range & Flush Scores")
ax.set_xlabel("Time")
ax.set_ylabel("Price")
ax.legend()
ax.grid(True)

# Display in Streamlit
st.pyplot(fig)
