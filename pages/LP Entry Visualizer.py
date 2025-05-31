import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="LP Entry Visualizer", layout="wide")
st.title("LP Entry Trigger & Range Visualizer")

# === Simulated price data (replace with live or API-connected data later) ===
dates = pd.date_range(end=pd.Timestamp.today(), periods=100, freq='4H')
prices = np.linspace(2400, 2700, 100) + np.random.normal(0, 20, 100)
open_prices = prices + np.random.normal(0, 10, 100)
high_prices = np.maximum(prices + 10, open_prices + 5)
low_prices = np.minimum(prices - 10, open_prices - 5)
close_prices = prices
volume = np.random.randint(100, 500, 100)

df = pd.DataFrame({
    "datetime": dates,
    "open": open_prices,
    "high": high_prices,
    "low": low_prices,
    "close": close_prices,
    "volume": volume
})

# === Parameters ===
entry_drawdown_pct = st.sidebar.slider("Entry Drawdown %", 1, 10, 5)
range_multiplier = st.sidebar.slider("LP Upper Range Multiplier", 105, 120, 110) / 100
vol_window = st.sidebar.slider("Volume SMA Window", 5, 30, 20)
body_threshold = st.sidebar.slider("Min Candle Body %", 1, 10, 2)

# === Impulse & Entry Logic ===
avg_volume = df['volume'].rolling(vol_window).mean()
df['is_bullish'] = df['close'] > df['open']
df['body_pct'] = abs(df['close'] - df['open']) / df['low'] * 100
df['is_big_body'] = df['body_pct'] >= body_threshold
df['is_high_volume'] = df['volume'] > avg_volume

# Local high check (simplified to last 3 bars)
df['is_local_high'] = (df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(2))
df['impulse'] = df['is_bullish'] & df['is_big_body'] & df['is_high_volume'] & df['is_local_high']

# Store impulse close and entry thresholds
df['impulse_close'] = np.where(df['impulse'], df['close'], np.nan)
df['impulse_close'] = df['impulse_close'].ffill()
df['entry_price'] = df['impulse_close'] * (1 - entry_drawdown_pct / 100)
df['entry_trigger'] = df['close'] <= df['entry_price']

# LP Range (set only at entry point)
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

# Impulse markers
fig.add_trace(go.Scatter(
    x=df.loc[df['impulse'], 'datetime'],
    y=df.loc[df['impulse'], 'high'] + 10,
    mode='markers+text',
    text=['Impulse']*df['impulse'].sum(),
    textposition='top center',
    marker=dict(color='lime', size=10),
    name='Impulse'))

# Entry markers
fig.add_trace(go.Scatter(
    x=df.loc[df['entry_trigger'], 'datetime'],
    y=df.loc[df['entry_trigger'], 'low'] - 10,
    mode='markers+text',
    text=['Entry']*df['entry_trigger'].sum(),
    textposition='bottom center',
    marker=dict(color='blue', size=10),
    name='Entry'))

# LP Range zone
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

# Background fill
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
