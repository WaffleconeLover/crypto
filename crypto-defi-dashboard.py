# ETH Leverage LP Strategy Dashboard
# This version preserves all previous features and prepares for additional volatility overlays and trade management tools.

import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="ETH Leverage Loop Simulator", layout="wide")
st.title("ETH Leverage Loop Simulator")

# === Step 1: Real-time ETH price ===
def fetch_eth_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        return r.json()["ethereum"]["usd"]
    except:
        return 2600.00

if "eth_price" not in st.session_state:
    st.session_state.eth_price = fetch_eth_price()

if st.button("Refresh ETH Price from CoinGecko"):
    st.session_state.eth_price = fetch_eth_price()

eth_price = st.session_state.eth_price
st.markdown(f"**Real-Time ETH Price:** ${eth_price:,.2f}")

# === Step 2: Configure Loop 1 ===
st.header("Step 2: Configure Loop 1")
initial_collateral_eth = st.number_input("Initial ETH Collateral", value=6.73, step=0.01)
ltv1 = st.slider("Loop 1 Borrow LTV (%)", min_value=10, max_value=58, value=30)
expected_lp_days = st.slider("Expected LP Duration (Days)", min_value=1, max_value=30, value=7)

# --- Lock logic ---
if "loop1_locked" not in st.session_state:
    st.session_state.loop1_locked = False
if "locked_ltv1" not in st.session_state:
    st.session_state.locked_ltv1 = ltv1
if st.button("Lock Loop 1 Settings"):
    st.session_state.loop1_locked = True
    st.session_state.locked_ltv1 = ltv1
if st.button("Unlock Loop 1 Settings"):
    st.session_state.loop1_locked = False

if st.session_state.loop1_locked:
    ltv1 = st.session_state.locked_ltv1
    st.markdown(f"**Loop 1 LTV is Locked at:** {ltv1}%")

# --- Loop 1 Calculations ---
collateral_value_usd = initial_collateral_eth * eth_price
loop1_debt = collateral_value_usd * ltv1 / 100
eth_gained = loop1_debt / eth_price
eth_stack_after_loop1 = initial_collateral_eth + eth_gained
new_collateral_usd = eth_stack_after_loop1 * eth_price
loop1_health_score = (new_collateral_usd * 0.80) / loop1_debt
loop1_liquidation_price = (loop1_debt / eth_stack_after_loop1) / 0.80
loop1_pct_to_liquidation = 1 - (loop1_liquidation_price / eth_price)

# === Volatility ===
def get_eth_volatility(days):
    end = datetime.now()
    start = end - timedelta(days=90)
    df = yf.download("ETH-USD", start=start, end=end)
    df = df.dropna()
    df['returns'] = df['Adj Close'].pct_change()
    df['vol'] = df['returns'].rolling(window=days).std() * np.sqrt(365)
    return df

df_vol = get_eth_volatility(expected_lp_days)
latest_vol = df_vol['vol'].iloc[-1] * 100

if latest_vol < 20:
    regime = "Low"
elif latest_vol < 40:
    regime = "Medium"
else:
    regime = "High"

# === Loop 1 Summary ===
st.subheader("Loop 1 Summary")
st.markdown(f"- **Debt After Loop 1:** ${loop1_debt:,.2f}")
st.markdown(f"- **ETH Gained After Loop 1:** {eth_gained:.2f}")
st.markdown(f"- **ETH Stack After Loop 1:** {eth_stack_after_loop1:.2f}")
st.markdown(f"- **New Collateral After Loop 1:** ${new_collateral_usd:,.2f}")
st.markdown(f"- **Loop 1 Health Score:** {loop1_health_score:.2f}")
st.markdown(f"- **Loop 1 % to Liquidation:** {loop1_pct_to_liquidation:.1%}")
st.markdown(f"- **Loop 1 Liquidation Price:** ${loop1_liquidation_price:,.2f}")
st.markdown(f"- **Est. Annualized Volatility ({expected_lp_days}D Lookback):** {latest_vol:.2f}%")
st.markdown(f"- **Market Behavior:** {regime}")

# === Volatility Chart ===
st.subheader("Volatility Trend")
fig, ax1 = plt.subplots(figsize=(9, 4))
ax1.plot(df_vol.index, df_vol['Adj Close'], color='blue', label='ETH Price ($)')
ax1.set_ylabel("ETH Price ($)", color='blue')

ax2 = ax1.twinx()
ax2.plot(df_vol.index, df_vol['vol'] * 100, color='red', label='Volatility (%)')
ax2.set_ylabel("Annualized Volatility (%)", color='red')
st.pyplot(fig)

# === Step 3: Loop 2 Evaluation ===
st.header("Step 3: Loop 2 Evaluation")
ltv2_range = range(10, 30)
loop2_data = []

for ltv2 in ltv2_range:
    usdc_loan2 = new_collateral_usd * ltv2 / 100
    total_debt = loop1_debt + usdc_loan2
    hf2 = (new_collateral_usd * 0.80) / total_debt
    price_at_liq = total_debt / (eth_stack_after_loop1 * 0.80)
    pct_to_liq = 1 - (price_at_liq / eth_price)
    loop2_data.append({
        "LTV (%)": ltv2,
        "Health Score": round(hf2, 2),
        "Loan Amount ($)": f"${usdc_loan2:,.2f}",
        "% to Liquidation": f"{pct_to_liq:.1%}",
        "ETH Price at Liquidation": f"${price_at_liq:,.2f}"
    })

st.dataframe(pd.DataFrame(loop2_data), use_container_width=True)
