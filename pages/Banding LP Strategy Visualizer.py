import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Sample prices for the past 2 days, hourly resolution
now = datetime.utcnow()
times = pd.date_range(end=now, periods=48, freq='H')

# Simulate ETH prices trending upward to touch the band
prices = np.linspace(2515, 2545, 48) + np.random.normal(0, 3, 48)
eth_df = pd.DataFrame({"datetime": times, "price": prices})
eth_df.set_index("datetime", inplace=True)

# Define Band 1 parameters
band_min = 2518
band_max = 2543
liq_price = 1574
liq_drop_pct = 0.375

# Drawdown levels from Band Min
drawdowns = [0.05, 0.10, 0.15]  # 5%, 10%, 15%
drawdown_levels = [band_min * (1 - d) for d in drawdowns]

# Plotting
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

# Chart 1: Band 1 Range
ax1.set_title("Band 1 Range Chart")
ax1.plot(eth_df.index, eth_df['price'], label="ETH Price", color="green")
ax1.axhline(band_min, linestyle="--", color="blue", label="Band Min")
ax1.axhline(band_max, linestyle="--", color="orange", label="Band Max")
ax1.set_ylabel("Price")
ax1.legend()
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H'))
ax1.grid(True)

# Chart 2: Band 1 Drawdowns
ax2.set_title("Band 1 Drawdowns Chart")
for pct, lvl in zip(["5% Down", "10% Down", "15% Down"], drawdown_levels):
    ax2.axhline(lvl, linestyle="--", color="skyblue", label=pct)
ax2.set_ylim([min(drawdown_levels) - 50, band_max + 20])
ax2.set_ylabel("Price")
ax2.legend()
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H'))
ax2.grid(True)

st.pyplot(fig)
