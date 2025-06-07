import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from matplotlib.ticker import FuncFormatter
from mplfinance.original_flavor import candlestick_ohlc

st.set_page_config(layout="wide")
st.title("Banding LP Chart Builder")

# --------------------
# ETH Price Fetcher
# --------------------
def get_eth_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        return r.json()['ethereum']['usd']
    except:
        return None

eth_price = get_eth_price()
if eth_price:
    st.markdown(f"**Current ETH Price:** ${eth_price:,.2f}")
else:
    st.markdown("**Current ETH Price:** *Not Available*")
    st.error("Failed to retrieve ETH price data from CoinGecko.")

# --------------------
# Chart Data Input
# --------------------
st.markdown("**Paste Band Data Here:**")
user_input = st.text_area("", height=200)

# --------------------
# Parse Band and Zone Data
# --------------------
def parse_input(text):
    bands = []
    zones = []
    current_band = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        try:
            if line.startswith("Band"):
                parts = [p.strip() for p in line.split("|")]
                band = {}
                for part in parts:
                    if part.startswith("Band"):
                        band_num = int(part.split(" ")[1])
                        band["Band"] = band_num
                    else:
                        key, value = [p.strip() for p in part.split("=")]
                        if key == "Spread":
                            band[key] = float(value.replace("%", "")) / 100
                        elif key in ["Min", "Max", "Liq. Price"]:
                            band[key] = float(value)
                        elif key == "Liq. Drop %":
                            band[key] = float(value)
                bands.append(band)
                current_band = band_num

            elif line.startswith("5%") or line.startswith("10%") or line.startswith("15%"):
                parts = [p.strip() for p in line.split("|")]
                zone = {"Band": current_band}
                for part in parts:
                    key, value = [p.strip() for p in part.split("=")]
                    if key in ["5% Down", "10% Down", "15% Down"]:
                        zone["label"] = key
                        zone["level"] = float(value)
                    elif key == "Liq. Drop %":
                        zone[key] = float(value)
                    elif key in ["Liq. Price", "Dist. from Liq. Price"]:
                        zone[key] = float(value)
                zones.append(zone)
        except Exception as e:
            st.warning(f"Failed to parse line: {line} — {e}")

    return bands, zones

# --------------------
# Chart Generator
# --------------------
def get_heiken_ashi():
    end = datetime.now()
    start = end - timedelta(days=2)
    url = (
        f"https://api.coingecko.com/api/v3/coins/ethereum/market_chart/range"
        f"?vs_currency=usd&from={int(start.timestamp())}&to={int(end.timestamp())}"
    )
    r = requests.get(url).json()
    prices = r['prices']
    df = pd.DataFrame(prices, columns=["timestamp", "price"])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df['open'] = df['price'].shift(1)
    df['high'] = df[['open', 'price']].max(axis=1)
    df['low'] = df[['open', 'price']].min(axis=1)
    df['close'] = df['price']
    df = df.dropna()

    o = df['open']
    h = df['high']
    l = df['low']
    c = df['close']
    ha_open = (o + c) / 2
    ha_close = (o + h + l + c) / 4
    ha_high = df[['high', 'open', 'close']].max(axis=1)
    ha_low = df[['low', 'open', 'close']].min(axis=1)

    df_ha = pd.DataFrame({
        'timestamp': df.index,
        'open': ha_open,
        'high': ha_high,
        'low': ha_low,
        'close': ha_close
    })
    df_ha.reset_index(drop=True, inplace=True)
    df_ha['timestamp'] = mdates.date2num(df_ha['timestamp'])
    return df_ha

if st.button("Generate Chart"):
    bands, zones = parse_input(user_input)

    if not bands:
        st.warning("No valid band data found.")
    else:
        df_ha = get_heiken_ashi()

        for band in bands:
            band_zones = [z for z in zones if z['Band'] == band['Band']]
            ymin = min(band['Min'], band['Max']) * 0.99
            ymax = max(band['Min'], band['Max']) * 1.01

            # Band Chart
            fig, ax = plt.subplots(figsize=(12, 5))
            ax.set_title(f"Band {band['Band']} Range Chart")
            ax.set_ylabel("ETH Price")
            ax.set_ylim([ymin, ymax])

            ohlc = df_ha[['timestamp', 'open', 'high', 'low', 'close']].values
            candlestick_ohlc(ax, ohlc, width=0.02, colorup='green', colordown='red')

            ax.axhline(band['Min'], color='green', linestyle='--')
            ax.axhline(band['Max'], color='green', linestyle='--')
            ax.fill_between(df_ha['timestamp'], band['Min'], band['Max'], color='green', alpha=0.2)

            ax.text(df_ha['timestamp'].iloc[-1], band['Max'],
                    f"Band\n{band['Min']} - {band['Max']}\nLiq: ${band['Liq. Price']} ({band['Liq. Drop %']*100:.1f}%)",
                    ha='right', va='bottom')

            ax.xaxis_date()
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H'))
            st.pyplot(fig)

            # Drawdown Chart
            fig2, ax2 = plt.subplots(figsize=(12, 5))
            ax2.set_title(f"Band {band['Band']} Drawdowns Chart")
            ax2.set_ylabel("ETH Price")
            ax2.set_ylim([band['Liq. Price'] * 0.95, max(band['Min'], band['Max']) * 1.02])

            candlestick_ohlc(ax2, ohlc, width=0.02, colorup='green', colordown='red')

            for zone in band_zones:
                ax2.axhline(zone['level'], linestyle='dotted', color='crimson')
                ax2.text(df_ha['timestamp'].iloc[-1], zone['level'],
                        f"{zone['label']} = {zone['level']:.0f}", ha='right', va='bottom', color='crimson')

            ax2.xaxis_date()
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H'))
            st.pyplot(fig2)
