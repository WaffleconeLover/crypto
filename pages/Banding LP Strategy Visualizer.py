import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from datetime import datetime

@st.cache_data(ttl=300)
def get_eth_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        response = requests.get(url)
        return response.json()['ethereum']['usd']
    except:
        return None

@st.cache_data(ttl=300)
def get_eth_ohlc():
    url = "https://api.coingecko.com/api/v3/coins/ethereum/ohlc?vs_currency=usd&days=1"
    try:
        df = pd.DataFrame(requests.get(url).json(), columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp').resample('15min').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
        }).dropna()
        return df
    except:
        return pd.DataFrame()

def compute_heikin_ashi(df):
    ha_df = pd.DataFrame(index=df.index)
    ha_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_df['open'] = 0.0
    ha_df.iloc[0, ha_df.columns.get_loc('open')] = (df.iloc[0]['open'] + df.iloc[0]['close']) / 2
    for i in range(1, len(df)):
        ha_df.iloc[i, ha_df.columns.get_loc('open')] = (
            ha_df.iloc[i - 1]['open'] + ha_df.iloc[i - 1]['close']) / 2
    ha_df['high'] = ha_df[['open', 'close']].join(df['high']).max(axis=1)
    ha_df['low'] = ha_df[['open', 'close']].join(df['low']).min(axis=1)
    return ha_df

# Sidebar: ETH price controls
st.sidebar.title("Chart Controls")
refresh_mode = st.sidebar.radio("ETH Price Refresh", ["Manual", "Every 5 min"], index=0)
if refresh_mode == "Manual" and st.sidebar.button("Refresh ETH Price"):
    st.cache_data.clear()

eth_price = get_eth_price()
st.sidebar.markdown(f"**Current ETH Price:** ${eth_price}")

# Main UI
st.title("Banding LP Strategy Visualizer")
raw_input = st.text_area("Paste Band Chart Setups Text", height=300)
run_button = st.button("Generate Chart")

bands = []
liq_lines = []

if run_button and raw_input:
    for line in raw_input.splitlines():
        line = line.strip()
        parts = [p.strip() for p in line.split('|') if '=' in p]
        try:
            if line.lower().startswith("band"):
                band_id = parts[0].split()[1]
                band_min = float(parts[1].split('=')[1].strip())
                band_max = float(parts[2].split('=')[1].strip())
                liq_price = float(parts[4].split('=')[1].strip())
                liq_drop = float(parts[5].split('=')[1].replace('%', '').strip())
                bands.append({
                    "Band": f"Band {band_id}",
                    "Min": band_min,
                    "Max": band_max,
                    "Liq Price": liq_price,
                    "Liq Drop %": liq_drop
                })
            elif "% Down" in line:
                label = parts[0].split('=')[0].strip()
                value = float(parts[0].split('=')[1].strip())
                liq_lines.append((label, value))
        except Exception as e:
            st.warning(f"Failed to parse line: {line} — {e}")

if bands:
    df_bands = pd.DataFrame(bands)
    df_ohlc = get_eth_ohlc()
    ha = compute_heikin_ashi(df_ohlc)

    fig, ax = plt.subplots(figsize=(12, 6))

    for i in range(len(ha)):
        color = 'green' if ha.iloc[i]['close'] >= ha.iloc[i]['open'] else 'red'
        ax.plot([ha.index[i], ha.index[i]], [ha.iloc[i]['low'], ha.iloc[i]['high']], color=color, linewidth=1)
        ax.add_patch(plt.Rectangle((ha.index[i], min(ha.iloc[i]['open'], ha.iloc[i]['close'])),
                                   width=pd.Timedelta(minutes=12),
                                   height=abs(ha.iloc[i]['close'] - ha.iloc[i]['open']),
                                   color=color, alpha=0.6))

    ax.axhline(eth_price, color='gray', linestyle='--', label=f"ETH Spot = ${eth_price:.2f}")

    for _, row in df_bands.iterrows():
        ax.axhline(row['Liq Price'], color='red', linestyle=':', linewidth=1)
        ax.fill_betweenx([row['Min'], row['Max']], ha.index[0], ha.index[-1], color='green', alpha=0.3)
        ax.text(ha.index[int(len(ha)*0.95)], (row['Min'] + row['Max']) / 2,
                f"{row['Band']}\n${row['Min']} - ${row['Max']}\nLiq: ${row['Liq Price']} ({row['Liq Drop %']}%)",
                va='center', fontsize=8)

    for label, price in liq_lines:
        ax.axhline(price, color='crimson', linestyle='--', linewidth=1.2)
        ax.text(ha.index[0], price, label, va='center', ha='left', fontsize=8, color='crimson')

    min_y = min(df_bands['Min'].min(), ha['low'].min()) * 0.99
    max_y = max(df_bands['Max'].max(), ha['high'].max()) * 1.01
    ax.set_ylim(min_y, max_y)
    ax.set_xlim(ha.index[0], ha.index[-1])
    ax.set_title("Liquidity Bands and Liquidation Zones")
    ax.set_ylabel("ETH Price")
    ax.legend()
    st.pyplot(fig)
elif run_button:
    st.info("Paste your Band Chart Setups to visualize the ranges.")
