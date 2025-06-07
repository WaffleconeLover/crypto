import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf

# --- Helper functions ---
def fetch_eth_prices():
    try:
        df = yf.download("ETH-USD", period="2d", interval="15m")
        df.index = pd.to_datetime(df.index)
        df = df[['Open', 'High', 'Low', 'Close']].rename(columns=str.lower)
        return df
    except Exception as e:
        st.error("Failed to retrieve ETH price data from Yahoo Finance.")
        return pd.DataFrame()

def heiken_ashi(df):
    if df.empty:
        return pd.DataFrame()

    ha_df = df.copy()
    ha_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_df['open'] = 0.0
    ha_df['open'].iloc[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_df['open'].iloc[i] = (ha_df['open'].iloc[i-1] + ha_df['close'].iloc[i-1]) / 2
    ha_df['high'] = ha_df[['open', 'close', 'high']].max(axis=1)
    ha_df['low'] = ha_df[['open', 'close', 'low']].min(axis=1)
    return ha_df

def parse_band_block(block_text):
    lines = block_text.strip().split('\n')
    bands = []
    drawdowns = []

    band_data = {}
    for line in lines:
        if line.startswith("Band"):
            try:
                parts = line.split('|')
                band_data = {
                    'label': parts[0].strip(),
                    'min': float(parts[1].split('=')[1]),
                    'max': float(parts[2].split('=')[1]),
                }
                bands.append(band_data)
            except Exception as e:
                st.warning(f"Failed to parse line: {line} -- {e}")
        elif "% Down" in line:
            try:
                parts = line.split('|')
                drawdowns.append({
                    'label': parts[0].strip(),
                    'level': float(parts[0].split('=')[1])
                })
            except Exception as e:
                st.warning(f"Failed to parse drawdown line: {line} -- {e}")

    return bands, drawdowns

def plot_band_and_drawdowns(ha_df, bands, drawdowns):
    if ha_df.empty or not bands:
        st.warning("No valid chart data available.")
        return

    for i, band in enumerate(bands):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

        # Band Chart
        ax1.plot(ha_df.index, ha_df['close'], label='ETH Price', color='green')
        ax1.axhline(band['min'], color='blue', linestyle='dashed', label='Band Min')
        ax1.axhline(band['max'], color='orange', linestyle='dashed', label='Band Max')
        ax1.set_title(f"{band['label']} Range Chart")
        ax1.legend()

        # Drawdown Chart
        ax2.plot(ha_df.index, ha_df['close'], label='ETH Price', color='gray')
        for d in drawdowns:
            ax2.axhline(d['level'], linestyle='dashed', label=d['label'])
        ax2.set_title(f"{band['label']} Drawdowns Chart")
        ax2.legend()

        st.pyplot(fig)

# --- Streamlit Interface ---
st.title("Banding LP Chart Builder")

if "eth_price" not in st.session_state:
    st.session_state.eth_price = fetch_eth_prices()

if st.button("Refresh ETH Price"):
    st.session_state.eth_price = fetch_eth_prices()

eth_df = st.session_state.eth_price
if not eth_df.empty:
    st.write("Current ETH Price:", f"${eth_df['close'].iloc[-1]:.2f}")
else:
    st.write("Current ETH Price:", "*Not Available*")

block_text = st.text_area("Paste Band 1 Block", height=180)
if st.button("Generate Chart"):
    bands, drawdowns = parse_band_block(block_text)
    ha_df = heiken_ashi(eth_df)
    plot_band_and_drawdowns(ha_df, bands, drawdowns)
