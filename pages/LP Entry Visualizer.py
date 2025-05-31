import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests
from datetime import datetime

st.set_page_config(page_title="LP Entry Visualizer", layout="wide")
st.title("LP Entry Trigger & Range Visualizer")

# === User-configurable Parameters ===
entry_drawdown_pct = st.sidebar.slider("Entry Drawdown %", 1, 10, 5)
range_multiplier = st.sidebar.slider("LP Upper Range Multiplier", 105, 120, 110) / 100
vol_window = st.sidebar.slider("Volume SMA Window", 5, 30, 20)
body_threshold = st.sidebar.slider("Min Candle Body %", 1, 10, 2)

# === Fetch Live ETH/USDC OHLCV Data from CoinGecko ===
@st.cache_data(ttl=300)
def get_eth_usd_ohlc(days=7):
    url = f"https://api.coingecko.com/api/v3/coins/ethereum/ohlc?vs_currency=usd&days={days}"
    r = requests.get(url)
    if r.status_code != 200:
        st.error("Failed to fetch data from CoinGecko")
        return pd.DataFrame()
    data = r.json()
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
    
    # Localize datetime to Pacific Time
    import pytz
    la_tz = pytz.timezone("America/Los_Angeles")
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms").dt.tz_localize("UTC").dt.tz_convert(la_tz)
    
    df = df.drop(columns=["timestamp"])
    df["volume"] = np.random.randint(100, 500, len(df))  # Simulated volume
    return df

# Get price data
df = get_eth_usd_ohlc()
if df.empty:
    st.stop()

# === Calculations ===
avg_volume = df['volume'].rolling(vol_window).mean()
df['is_bullish'] = df['close'] > df['open']
df['body_pct'] = abs(df['close'] - df['open']) / df['low'] * 100
df['is_big_body'] = df['body_pct'] >= body_threshold
df['is_high_volume'] = df['volume'] > avg_volume

# Local high logic
df['is_local_high'] = (df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(2))
df['impulse'] = df['is_bullish'] & df['is_big_body'] & df['is_high_volume'] & df['is_local_high']
df['impulse_close'] = np.where(df['impulse'], df['close'], np.nan)
df['impulse_close'] = df['impulse_close'].ffill()
df['entry_price'] = df['impulse_close'] * (1 - entry_drawdown_pct / 100)
df['entry_trigger'] = df['close'] <= df['entry_price']
df['lp_lower'] = np.where(df['entry_trigger'], df['entry_price'], np.nan)
df['lp_upper'] = np.where(df['entry_trigger'], df['impulse_close'] * range_multiplier, np.nan)
df['lp_lower'] = df['lp_lower'].ffill()
df['lp_upper'] = df['lp_upper'].ffill()
df['in_range'] = (df['close'] >= df['lp_lower']) & (df['close'] <= df['lp_upper'])

# === Plotting ===
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df['datetime'],
    open=df['open'], high=df['high'], low=df['low'], close=df['close'],
    name='Price'))

fig.add_trace(go.Scatter(
    x=df.loc[df['impulse'], 'datetime'],
    y=df.loc[df['impulse'], 'high'] + 10,
    mode='markers+text',
    text=['Impulse']*df['impulse'].sum(),
    textposition='top center',
    marker=dict(color='lime', size=10),
    name='Impulse'))

fig.add_trace(go.Scatter(
    x=df.loc[df['entry_trigger'], 'datetime'],
    y=df.loc[df['entry_trigger'], 'low'] - 10,
    mode='markers+text',
    text=['Entry']*df['entry_trigger'].sum(),
    textposition='bottom center',
    marker=dict(color='blue', size=10),
    name='Entry'))

fig.add_trace(go.Scatter(
    x=df['datetime'],
    y=df['lp_upper'],
    mode='lines',
    line=dict(color='green', width=1),
    name='LP Upper'))

fig.add_trace(go.Scatter(
    x=df['datetime'],
    y=df['lp_lower'],
    mode='lines',
    line=dict(color='red', width=1),
    name='LP Lower'))

fig.add_trace(go.Scatter(
    x=pd.concat([df['datetime'], df['datetime'][::-1]]),
    y=pd.concat([df['lp_upper'], df['lp_lower'][::-1]]),
    fill='toself',
    fillcolor='rgba(0,255,0,0.1)',
    line=dict(color='rgba(255,255,255,0)'),
    hoverinfo='skip',
    showlegend=False))

fig.update_layout(
    height=700,
    margin=dict(t=10, b=10),
    xaxis_rangeslider_visible=False
)

st.plotly_chart(fig, use_container_width=True)
