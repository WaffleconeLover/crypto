import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import re

st.set_page_config(layout="wide")
st.title("Banding LP Chart Builder")

# Sample data generation function for ETH prices (for simulation purposes)
def get_eth_price_data():
    now = datetime.now()
    times = pd.date_range(end=now, periods=100, freq='H')
    prices = np.linspace(2518, 2543, len(times)) + np.random.normal(0, 5, len(times))
    return pd.DataFrame({'datetime': times, 'close': prices})

# Function to convert standard OHLC to Heiken Ashi
def heiken_ashi(df):
    ha_df = df.copy()
    ha_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_df['open'] = (df['open'].shift(1) + df['close'].shift(1)) / 2
    ha_df['high'] = df[['high', 'open', 'close']].max(axis=1)
    ha_df['low'] = df[['low', 'open', 'close']].min(axis=1)
    ha_df.iloc[0, ha_df.columns.get_loc('open')] = (df.iloc[0]['open'] + df.iloc[0]['close']) / 2
    return ha_df

# Parse band input
band_input = st.text_area("Paste Band 1 Block Here:", height=160)
submit = st.button("Generate Chart")
refresh_price = st.button("Refresh ETH Price")

eth_df = get_eth_price_data()

if not eth_df.empty:
    st.write("Current ETH Price:", f"${eth_df['close'].iloc[-1]:.2f}")
else:
    st.write("Current ETH Price: Not Available")

if submit:
    lines = band_input.strip().splitlines()
    bands = []
    drawdowns = []

    for line in lines:
        line = line.strip()
        if line.startswith("Band"):
            try:
                pattern = r"Min = (\d+) \| Max = (\d+) \| Spread = ([\d.]+)% \| Liq. Price = (\d+) \| Liq. Drop % = ([\d.]+)"
                match = re.search(pattern, line)
                if match:
                    min_val, max_val, spread, liq_price, drop_pct = match.groups()
                    bands.append({
                        'min': int(min_val),
                        'max': int(max_val),
                        'spread': float(spread),
                        'liq_price': int(liq_price),
                        'liq_drop': float(drop_pct)
                    })
            except Exception as e:
                st.warning(f"Failed to parse line: {line} ({e})")
        elif "Down" in line:
            try:
                level_match = re.match(r"(\d+)% Down = (\d+)", line)
                if level_match:
                    pct, level = level_match.groups()
                    drawdowns.append({'label': f"{pct}% Down", 'level': int(level)})
            except Exception as e:
                st.warning(f"Failed to parse line: {line} ({e})")

    if not bands:
        st.warning("No valid band data found.")
    else:
        # Prepare ETH OHLC data
        eth_df['open'] = eth_df['close'].shift(1).fillna(method='bfill')
        eth_df['high'] = eth_df[['open', 'close']].max(axis=1) + np.random.normal(0, 1, len(eth_df))
        eth_df['low'] = eth_df[['open', 'close']].min(axis=1) - np.random.normal(0, 1, len(eth_df))
        ha_df = heiken_ashi(eth_df)

        # Plot Range Chart
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        ax1.set_title("Band 1 Range Chart")
        ax1.plot(ha_df['datetime'], ha_df['close'], label='ETH Price', color='green')
        ax1.axhline(bands[0]['min'], color='blue', linestyle='--', label='Band Min')
        ax1.axhline(bands[0]['max'], color='orange', linestyle='--', label='Band Max')
        ax1.legend()

        # Plot Drawdowns
        ax2.set_title("Band 1 Drawdowns Chart")
        ax2.plot(ha_df['datetime'], ha_df['close'], label='ETH Price', color='black')
        for zone in drawdowns:
            ax2.axhline(zone['level'], linestyle='--', label=zone['label'], color='skyblue')
        ax2.legend()

        st.pyplot(fig)
