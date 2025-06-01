# ETH Price with Liquidation Zones & LP Range (Live, 24h Heikin Ashi)
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from binance.client import Client
from datetime import datetime
import pytz

# Binance API setup (public access only)
client = Client()
symbol = "ETHUSDT"
interval = Client.KLINE_INTERVAL_30MIN

# Pull last 24 hours of 30m candles (48 candles total)
klines = client.get_klines(symbol=symbol, interval=interval, limit=48)

# Parse into DataFrame
data = pd.DataFrame(klines, columns=[
    'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
    'Close Time', 'Quote Asset Volume', 'Number of Trades',
    'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume', 'Ignore'
])

# Convert types
for col in ['Open', 'High', 'Low', 'Close']:
    data[col] = data[col].astype(float)
data['Time'] = pd.to_datetime(data['Open Time'], unit='ms')

# Compute Heikin Ashi candles
data['HA_Close'] = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4
ha_open = [(data['Open'][0] + data['Close'][0]) / 2]
for i in range(1, len(data)):
    ha_open.append((ha_open[i-1] + data['HA_Close'][i-1]) / 2)
data['HA_Open'] = ha_open

# Simulated liquidation clusters (price levels and $ values)
liquidation_clusters = {
    2660: 4.8,
    2630: 7.5,
    2605: 12.2,
    2580: 18.9,
    2550: 9.3,
    2525: 5.0
}

# Step 2: Manual LP range input
lp_range = (2575, 2595)

# Plotting
fig, ax = plt.subplots(figsize=(12, 6))

# Plot Heikin Ashi price line
ax.plot(data['Time'], data['HA_Close'], label='ETH Price (Heikin Ashi)', color='black')

# Plot LP range
ax.axhspan(lp_range[0], lp_range[1], color='green', alpha=0.2, label=f'LP Range {lp_range[0]}–{lp_range[1]}')

# Plot liquidation clusters
for level, value in liquidation_clusters.items():
    intensity = min(1.0, value / max(liquidation_clusters.values()))
    ax.axhspan(level - 1, level + 1, color='red', alpha=intensity * 0.4)
    ax.text(data['Time'].iloc[0], level, f"${value:.1f}M", fontsize=8, color='darkred', va='center')

# Formatting
ax.set_title("ETH Price (Heikin Ashi) with Liquidation Zones & LP Range")
ax.set_xlabel("Time")
ax.set_ylabel("Price")
ax.legend()
ax.grid(True)

# Display in Streamlit
st.pyplot(fig)
