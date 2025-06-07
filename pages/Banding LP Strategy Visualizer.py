import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import requests
from datetime import datetime, timedelta
import io

st.set_page_config(layout="wide")
st.title("Banding LP Chart Builder")

# Text input
input_text = st.text_area("Paste Band Data Here:", height=300)
submit = st.button("Generate Chart")

# Price fetch and caching
@st.cache_data(ttl=300)
def get_eth_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        return r.json()['ethereum']['usd']
    except Exception as e:
        st.error("Failed to fetch ETH price.")
        return None

eth_price = get_eth_price()
if st.button("Refresh ETH Price"):
    get_eth_price.clear()
    eth_price = get_eth_price()

if eth_price:
    st.markdown(f"**Current ETH Price: ${eth_price}**")

# Heiken Ashi simulation (synthetic candles)
def get_heiken_ashi():
    end = datetime.utcnow()
    start = end - timedelta(hours=8)
    url = f"https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=1&interval=minute"
    r = requests.get(url)
    data = r.json()
    prices = data['prices']
    df = pd.DataFrame(prices, columns=["timestamp", "price"])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df.resample('15T').ohlc()['price']
    df.dropna(inplace=True)

    ha_df = df.copy()
    ha_df['Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_df['Open'] = df['open'].shift(1)
    ha_df['Open'].iloc[0] = df['open'].iloc[0]
    ha_df['Open'] = (ha_df['Open'] + ha_df['Close'].shift(1)) / 2
    ha_df['High'] = df[['high', 'Open', 'Close']].max(axis=1)
    ha_df['Low'] = df[['low', 'Open', 'Close']].min(axis=1)
    return ha_df.dropna()

# Main chart logic
if submit and input_text:
    lines = [line.strip() for line in input_text.splitlines() if line.strip()]
    bands = []
    for i in range(0, len(lines), 4):
        try:
            header = lines[i]
            lvls = lines[i+1:i+4]
            parts = header.split("|")
            band_name = parts[0].strip()
            min_price = float(parts[1].split("=")[1])
            max_price = float(parts[2].split("=")[1])
            liq_price = float(parts[4].split("=")[1])

            liq_lines = []
            for l in lvls:
                tokens = l.split("=")
                level = float(tokens[1].split("|")[0])
                liq_lines.append(level)

            bands.append({
                'name': band_name,
                'min': min_price,
                'max': max_price,
                'liq': liq_price,
                'zones': liq_lines
            })
        except Exception as e:
            st.error(f"Failed to parse block starting with: {lines[i]}")

    ha_df = get_heiken_ashi()

    fig, ax = plt.subplots(figsize=(14, 6))
    for band in bands:
        ax.axhspan(band['min'], band['max'], alpha=0.3, label=band['name'])
        for zone in band['zones']:
            ax.axhline(y=zone, color='red', linestyle='--', linewidth=1)

    for idx, row in ha_df.iterrows():
        color = 'green' if row['Close'] >= row['Open'] else 'red'
        ax.plot([idx, idx], [row['Low'], row['High']], color=color, linewidth=1)
        ax.add_patch(plt.Rectangle((idx - timedelta(minutes=3), row['Open']),
                                   timedelta(minutes=6), row['Close'] - row['Open'],
                                   color=color))

    all_prices = [p for b in bands for p in [b['min'], b['max']] + b['zones']]
    min_axis = min(all_prices)
    max_axis = max(all_prices)
    pad = (max_axis - min_axis) * 0.01
    ax.set_ylim(min_axis - pad, max_axis + pad)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    st.pyplot(fig)
