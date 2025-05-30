import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import requests

# Streamlit config
st.set_page_config(page_title="ETH Leverage Heatmap", layout="wide")

st.title("ETH Leverage Heatmap")

# Session state setup for reset and manual loop 1
for key, default in {
    "eth_stack": 6.73,
    "eth_price_input": 2660,
    "eth_gained": 0.0,
    "loop1_eth": 10.4,
    "loop1_debt": 11200.0
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

col1, col2 = st.columns(2)
with col1:
    if st.button("🔁 Reset App (keep Loop 1)"):
        st.session_state.eth_stack = 6.73
        st.session_state.eth_price_input = 2660
        st.session_state.eth_gained = 0.0
with col2:
    if st.button("❌ Reset Loop 1 Inputs"):
        st.session_state.loop1_eth = 10.4
        st.session_state.loop1_debt = 11200

# Try to fetch real-time ETH price
eth_price_default = 2660
eth_price_live = None
try:
    eth_response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
    eth_price_live = eth_response.json().get("ethereum", {}).get("usd")
except:
    eth_price_live = None

if eth_price_live:
    st.markdown(f"**Live ETH Price from CoinGecko: ${eth_price_live:.2f}**")
    eth_price = eth_price_live
else:
    st.warning("Unable to fetch live ETH price. Please enter it manually.")
    eth_price = st.number_input("Manual ETH Price Input ($)", min_value=100.0, max_value=10000.0, value=float(st.session_state.eth_price_input), step=10.0)", min_value=100.0, max_value=10000.0, value=st.session_state.eth_price_input, step=10.0)
    st.session_state.eth_price_input = eth_price

# Input sliders
eth_stack = st.slider("Current ETH Stack", min_value=1.0, max_value=50.0, value=st.session_state.eth_stack, step=0.01)
st.session_state.eth_stack = eth_stack

# Loop 1 setup
st.markdown("### Manual Loop 1 Setup")
loop1_eth = st.number_input("ETH Stack After Loop 1", min_value=0.0, value=st.session_state.loop1_eth, step=0.01)
loop1_debt = st.number_input("Debt After Loop 1 ($)", min_value=0.0, value=float(st.session_state.loop1_debt), step=10.0)
st.session_state.loop1_eth = loop1_eth
st.session_state.loop1_debt = loop1_debt

loop1_health = (loop1_eth * eth_price * 0.8) / loop1_debt if loop1_debt > 0 else 0
st.markdown(f"**Loop 1 Health Score: {loop1_health:.2f}**")

# LP Exit Simulator
st.markdown("### LP Exit Simulation")
eth_gained = st.number_input("ETH Gained from LP", min_value=0.0, value=st.session_state.eth_gained, step=0.01)
st.session_state.eth_gained = eth_gained
updated_eth_stack = eth_stack + eth_gained
st.markdown(f"**Updated ETH Stack after LP Exit: {updated_eth_stack:.2f} ETH**")

# Grid definitions (loop1 fixed from input)
first_loop_eth = loop1_eth
first_loop_debt = loop1_debt
first_loop_collateral = first_loop_eth * eth_price
second_loop_lvts = np.arange(30.0, 52.0, 1.0)

# Simulate combinations
data = []
for s_ltv in second_loop_lvts:
    loop2_debt = first_loop_collateral * (s_ltv / 100)
    eth_bought_2 = loop2_debt / eth_price
    total_eth = first_loop_eth + eth_bought_2
    total_collateral = total_eth * eth_price
    total_debt = first_loop_debt + loop2_debt
    final_hs = (total_collateral * 0.8) / total_debt if total_debt > 0 else 0

    liq_price = round((total_debt / (total_eth * 0.8)), 2) if total_eth > 0 else 0
    liq_drop_pct = round((1 - (liq_price / eth_price)) * 100) if eth_price > 0 else 0

    pct_gain = ((total_eth / eth_stack) - 1) * 100 if eth_stack > 0 else 0

    data.append({
        "Second LTV": s_ltv,
        "First LTV": "Input",
        "Final Health Score": final_hs,
        "Loop 2 Debt": int(loop2_debt),
        "Liq Price": liq_price,
        "Liq Drop %": liq_drop_pct,
        "Total ETH": total_eth,
        "ETH Gain %": pct_gain
    })

heatmap_df = pd.DataFrame(data)

# Filter to minimum health threshold
heatmap_df = heatmap_df[heatmap_df["Final Health Score"] >= 1.6].copy()

# Rebalanced scoring
heatmap_df["Score"] = (
    heatmap_df["Final Health Score"] * 40 +
    heatmap_df["Liq Drop %"] * 0.4 +
    heatmap_df["ETH Gain %"] * 0.2 +
    heatmap_df["Loop 2 Debt"] * 0.015
)

# Rank all rows by score
heatmap_df = heatmap_df.sort_values("Score", ascending=False).copy()
heatmap_df["Rank"] = range(1, len(heatmap_df) + 1)

# Label formatting
def strip_zero(val):
    return f"{val:.2f}".rstrip("0").rstrip(".")

heatmap_df["Label"] = heatmap_df.apply(
    lambda row: (
        f"{strip_zero(row['Final Health Score'])}
"
        f"${row['Loop 2 Debt']}
"
        f"↓{row['Liq Drop %']}% @ ${strip_zero(row['Liq Price'])}
"
        f"{strip_zero(row['Total ETH'])} ETH (+{int(row['ETH Gain %'])}%)
"
        f"#{int(row['Rank'])}"
    ),
    axis=1
)
