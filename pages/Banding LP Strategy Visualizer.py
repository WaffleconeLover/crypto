import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import requests
from datetime import datetime, timedelta
import mplfinance as mpf
import numpy as np

st.set_page_config(layout="wide")
st.title("Banding LP Chart Builder")

# --------------------
# Helper: CoinGecko ETH price
# --------------------
def get_eth_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['ethereum']['usd']
    except:
        return None

# --------------------
# Helper: Heiken Ashi candles
# --------------------
def get_heiken_ashi():
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=48)

    url = (
        f"https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=2"
    )
    r = requests.get(url)
    data = r.json()

    prices = data['prices']
    df = pd.DataFrame(prices, columns=['timestamp', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df.resample('15T').ohlc()['price']

    ha_df = pd.DataFrame(index=df.index, columns=['Open', 'High', 'Low', 'Close'])
    for i in range(len(df)):
        o = df['open'].iloc[i]
        h = df['high'].iloc[i]
        l = df['low'].iloc[i]
        c = df['close'].iloc[i]
        if i == 0:
            ha_open = o
        else:
            ha_open = (ha_df['Open'].iloc[i - 1] + ha_df['Close'].iloc[i - 1]) / 2
        ha_close = (o + h + l + c) / 4
        ha_high = max(h, ha_open, ha_close)
        ha_low = min(l, ha_open, ha_close)
        ha_df.iloc[i] = [ha_open, ha_high, ha_low, ha_close]

    return ha_df.dropna()

# --------------------
# Helper: Parse input
# --------------------
def parse_band_blocks(text):
    bands = []
    blocks = text.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if not lines:
            continue
        try:
            band_line = lines[0].strip()
            band = {}
            parts = band_line.split("|")
            for part in parts:
                k, v = part.strip().split("=", 1)
                band[k.strip()] = v.strip()

            band_data = {
                'label': band_line,
                'min': float(band['Min']),
                'max': float(band['Max']),
                'liq_price': float(band['Liq. Price']),
                'liq_drop_pct': float(band['Liq. Drop %'])
            }

            drawdowns = []
            for dd_line in lines[1:]:
                if 'Down' not in dd_line:
                    continue
                try:
                    zone = {}
                    parts = dd_line.split("|")
                    for part in parts:
                        k, v = part.strip().split("=", 1)
                        zone[k.strip()] = v.strip()
                    drawdowns.append({
                        'label': dd_line.strip(),
                        'level': float(zone['5% Down' if '5% Down' in zone else '10% Down' if '10% Down' in zone else '15% Down'] if '5% Down' in zone or '10% Down' in zone or '15% Down' in zone else zone['Liq. Price'])
                    })
                except:
                    continue

            band_data['drawdowns'] = drawdowns
            bands.append(band_data)

        except Exception as e:
            st.warning(f"Failed to parse line: {band_line} — {e}")
    return bands

# --------------------
# Main Chart Generator
# --------------------
def plot_band_and_drawdowns(band, eth_price, ha):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw={'height_ratios': [3, 1]})

    # Top chart: Band range and candles
    ax1.set_title("Band 1 Range Chart")
    ax1.set_ylabel("ETH Price")
    ax1.axhspan(band['min'], band['max'], color='green', alpha=0.2)
    ax1.text(ha.index[-1], band['max'], f"Band\n{band['min']} – {band['max']}\nLiq: ${band['liq_price']} ({float(band['liq_drop_pct'])*100:.1f}%)",
             va='top', ha='right', fontsize=8)

    mpf.plot(ha, type='candle', ax=ax1, style='charles', ylabel='')

    # Bottom chart: Drawdowns
    ax2.set_title("Band 1 Drawdowns Chart")
    ax2.set_ylabel("ETH Price")
    ax2.set_ylim(
        min([z['level'] for z in band['drawdowns']]) * 0.99,
        max([z['level'] for z in band['drawdowns']]) * 1.01,
    )
    for zone in band['drawdowns']:
        ax2.axhline(zone['level'], linestyle="dotted", color="crimson")
        ax2.text(ha.index[-1], zone['level'], zone['label'], color="crimson", fontsize=8, va='bottom', ha='right')

    return fig

# --------------------
# UI
# --------------------
if 'eth_price' not in st.session_state:
    st.session_state['eth_price'] = get_eth_price()

if st.button("Refresh ETH Price"):
    price = get_eth_price()
    if price:
        st.session_state['eth_price'] = price
    else:
        st.error("Failed to retrieve ETH price data from CoinGecko.")

eth_price = st.session_state['eth_price']

st.markdown(f"**Current ETH Price:** ${eth_price if eth_price else '*Not Available*'}")

user_input = st.text_area("Paste Band Data Here:", height=180)

if st.button("Generate Chart"):
    bands = parse_band_blocks(user_input)
    if bands:
        ha = get_heiken_ashi()
        chart = plot_band_and_drawdowns(bands[0], eth_price, ha)
        st.pyplot(chart)
    else:
        st.warning("No valid band data found.")
