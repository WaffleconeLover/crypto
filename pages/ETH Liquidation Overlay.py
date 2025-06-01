# Step 1: Prototype overlay with synthetic ETH price + cluster bands
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Generate synthetic ETH price data (time vs price)
np.random.seed(42)
time = pd.date_range(start="2025-06-01 00:00", periods=48, freq="30min")
price = 2600 + np.cumsum(np.random.randn(len(time)) * 10)  # Simulate ETH price

# Simulated liquidation clusters (price levels and $ values)
liquidation_clusters = {
    2660: 4.8,
    2630: 7.5,
    2605: 12.2,
    2580: 18.9,
    2550: 9.3,
    2525: 5.0
}

# Step 2: Add manual LP range
lp_range = (2575, 2595)  # Example LP range

# Plotting
fig, ax = plt.subplots(figsize=(12, 6))

# Plot ETH price
ax.plot(time, price, label='ETH Price', color='black')

# Plot LP range band
ax.axhspan(lp_range[0], lp_range[1], color='green', alpha=0.2, label=f'LP Range {lp_range[0]}–{lp_range[1]}')

# Plot liquidation cluster bands
for level, value in liquidation_clusters.items():
    color_intensity = min(1.0, value / max(liquidation_clusters.values()))
    ax.axhspan(level - 1, level + 1, color='red', alpha=color_intensity * 0.4)
    ax.text(time[0], level, f"${value:.1f}M", verticalalignment='center', fontsize=8, color='darkred')

# Formatting
ax.set_title("ETH Price with Liquidation Zones & LP Range")
ax.set_xlabel("Time")
ax.set_ylabel("Price")
ax.legend()
ax.grid(True)

# Render the plot in Streamlit
st.pyplot(fig)
