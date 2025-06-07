import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(layout="wide")

st.title("Banding LP Chart Builder")

# Load ETH OHLCV data from Binance for last 2 days at 15m interval
def load_eth_data():
    url = "https://api.binance.com/api/v3/klines"
    symbol = "ETHUSDT"
    interval = "15m"
    limit = 192  # 2 days of 15m candles
    response = requests.get(url, params={"symbol": symbol, "interval": interval, "limit": limit})
    data = response.json()
    df = pd.DataFrame(data, columns=["time", "open", "high", "low", "close", "volume", "close_time", "quote_asset_volume", "num_trades", "taker_buy_base", "taker_buy_quote", "ignore"])
    df = df[["time", "open", "high", "low", "close"]].astype(float)
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df.set_index("time", inplace=True)
    return df

# Heiken Ashi transformation
def heiken_ashi(df):
    ha_df = df.copy()
    ha_df["close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_df["open"] = (df["open"].shift(1) + df["close"].shift(1)) / 2
    ha_df["open"].iloc[0] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2
    ha_df["high"] = ha_df[["open", "close", "high"]].max(axis=1)
    ha_df["low"] = ha_df[["open", "close", "low"]].min(axis=1)
    return ha_df

eth_df = load_eth_data()
ha_df = heiken_ashi(eth_df)

# Paste Band 1 Block
band_input = st.text_area("Paste Band 1 Block", height=160)
if st.button("Generate Chart"):
    try:
        lines = [line.strip() for line in band_input.split("\n") if line.strip()]
        band_line = lines[0]
        band_parts = {part.strip().split(" = ")[0]: part.strip().split(" = ")[1] for part in band_line.split("|")}
        band_min = float(band_parts["Min"])
        band_max = float(band_parts["Max"])
        liq_price = float(band_parts["Liq. Price"])
        liq_drop = float(band_parts["Liq. Drop %"])

        zones = []
        for line in lines[1:]:
            if "Down =" in line:
                pct, lv = line.split("=", 1)
                pct_label = pct.strip()
                lv = lv.strip().split("|")[0].strip()
                zones.append((pct_label, float(lv)))

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})

        # Range Chart
        ax1.fill_between(ha_df.index, band_min, band_max, color='green', alpha=0.2)
        ax1.plot(ha_df.index, ha_df["close"], color='black', linewidth=1, label="ETH Spot")
        for i in range(1, len(ha_df)):
            color = 'green' if ha_df["close"].iloc[i] >= ha_df["open"].iloc[i] else 'red'
            ax1.plot([ha_df.index[i], ha_df.index[i]], [ha_df["low"].iloc[i], ha_df["high"].iloc[i]], color=color)
            ax1.plot([ha_df.index[i], ha_df.index[i]], [ha_df["open"].iloc[i], ha_df["close"].iloc[i]], color=color, linewidth=4)
        ax1.set_ylabel("ETH Price")
        ax1.set_title("Band 1 Range Chart")
        ax1.axhline(y=liq_price, linestyle="--", color="gray")
        ax1.legend()

        # Drawdowns Chart
        ax2.plot(ha_df.index, ha_df["close"], label="ETH Price", color='black')
        for label, level in zones:
            ax2.axhline(level, linestyle="--", label=label, color='skyblue')
        ax2.set_ylabel("ETH Price")
        ax2.set_title("Band 1 Drawdowns Chart")
        ax2.legend()

        st.pyplot(fig)
    except Exception as e:
        st.error(f"Failed to parse or generate chart: {e}")
