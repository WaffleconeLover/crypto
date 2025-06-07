import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import requests
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="Banding LP Chart Builder", layout="wide")
st.title("Banding LP Chart Builder")

# ETH price fetcher
def fetch_eth_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        response = requests.get(url)
        return response.json()['ethereum']['usd']
    except:
        return None

# Sample Heiken Ashi generator (15 min candles, mock data)
def get_heiken_ashi():
    end = datetime.now()
    start = end - timedelta(hours=24)
    dates = pd.date_range(start=start, end=end, freq='15min')
    close_prices = 2500 + np.sin(np.linspace(0, 10, len(dates))) * 30
    open_prices = close_prices + np.random.normal(0, 2, len(dates))
    high_prices = np.maximum(open_prices, close_prices) + np.random.normal(0, 3, len(dates))
    low_prices = np.minimum(open_prices, close_prices) - np.random.normal(0, 3, len(dates))

    ha_df = pd.DataFrame({
        'Date': dates,
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices
    })
    return ha_df

# Parser for band lines
def parse_input_lines(lines):
    bands = []
    zones = []
    current_band = None
    for line in lines:
        line = line.strip()
        if line.startswith("Band"):
            parts = line.split("|")
            band = {}
            for part in parts:
                if '=' in part:
                    k, v = part.split("=")
                    band[k.strip()] = v.strip()
            current_band = {
                'min': float(band['Min']),
                'max': float(band['Max']),
                'liq_price': float(band['Liq. Price']),
                'liq_drop': float(band['Liq. Drop %'])
            }
            bands.append(current_band)
        elif 'Down =' in line and current_band is not None:
            parts = line.split("|")
            zone = {}
            for part in parts:
                if '=' in part:
                    k, v = part.split("=")
                    zone[k.strip()] = v.strip()
            zone['level'] = float(zone['Liq. Price'])
            zone['label'] = line.split("|")[0].strip()
            zones.append(zone)
    return bands, zones

# App sidebar
eth_price = st.session_state.get("eth_price", None)
if st.button("Refresh ETH Price"):
    eth_price = fetch_eth_price()
    st.session_state.eth_price = eth_price

st.markdown(f"**Current ETH Price:** {f'${eth_price:,.2f}' if eth_price else '*Not Available*'}")

text_input = st.text_area("Paste Band Data Here:", height=200)

if st.button("Generate Chart"):
    lines = text_input.strip().splitlines()
    try:
        bands, zones = parse_input_lines(lines)
        ha = get_heiken_ashi()

        all_prices = [p for band in bands for p in [band['min'], band['max'], band['liq_price']]] + [z['level'] for z in zones]
        ymin = min(all_prices) * 0.99
        ymax = max(all_prices) * 1.01

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.set_ylim(ymin, ymax)
        ax.set_title("Liquidity Bands and Liquidation Zones")
        ax.set_ylabel("ETH Price")

        # Plot Heiken Ashi
        for i in range(len(ha)):
            color = 'green' if ha['Close'][i] >= ha['Open'][i] else 'red'
            ax.plot([ha['Date'][i], ha['Date'][i]], [ha['Low'][i], ha['High'][i]], color=color)
            ax.add_patch(plt.Rectangle((ha['Date'][i], min(ha['Open'][i], ha['Close'][i])),
                                       timedelta(minutes=15),
                                       abs(ha['Close'][i] - ha['Open'][i]),
                                       color=color))

        # Plot bands
        for band in bands:
            ax.axhspan(band['min'], band['max'], color='green', alpha=0.3)
            ax.axhline(band['liq_price'], color='gray', linestyle='dashed')
            ax.text(ha['Date'].iloc[-1], (band['min'] + band['max']) / 2,
                    f"Band\n{int(band['min'])} – {int(band['max'])}\nLiq: ${int(band['liq_price'])} ({band['liq_drop']:.1%})",
                    va='center', ha='left', fontsize=8)

        # Plot zones
        for zone in zones:
            ax.axhline(zone['level'], linestyle="dotted", color="crimson")
            ax.text(ha['Date'].iloc[-1], zone['level'], zone['label'], color="crimson", fontsize=7, va='bottom')

        st.pyplot(fig)
    except Exception as e:
        st.error(f"Failed to generate chart: {e}")
