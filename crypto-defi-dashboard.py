import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import requests

st.set_page_config(layout="wide")

st.title("ETH Leverage Loop Simulator")

# Initialize session state
if "eth_price" not in st.session_state:
    st.session_state.eth_price = None

# Function to fetch ETH price
def fetch_eth_price():
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "ethereum", "vs_currencies": "usd"},
            timeout=5
        )
        response.raise_for_status()
        return response.json()["ethereum"]["usd"]
    except Exception:
        return None

# ETH Price logic
st.header("Step 1: ETH Price")
refresh_price = st.button("Refresh ETH Price from CoinGecko")
if refresh_price or st.session_state.eth_price is None:
    live_price = fetch_eth_price()
    if live_price:
        st.session_state.eth_price = live_price

if st.session_state.eth_price:
    st.markdown(f"**Real-Time ETH Price:** ${st.session_state.eth_price:,.2f}")
    eth_price = st.session_state.eth_price
else:
    eth_price = st.number_input("Enter ETH Price ($)", min_value=0.0, value=3000.0, step=1.0)
    st.session_state.eth_price = eth_price

# Loop 1 Setup
st.header("Step 2: Configure Loop 1")

eth_collateral = st.number_input("Initial ETH Collateral", min_value=0.0, value=6.73, step=0.01)
loop1_ltv = st.slider("Loop 1 Borrow LTV (%)", min_value=10, max_value=50, value=40, step=1)

loop1_debt = eth_collateral * (loop1_ltv / 100) * eth_price
eth_gained_loop1 = loop1_debt / eth_price
eth_stack = eth_collateral + eth_gained_loop1
loop1_health = (eth_stack * eth_price) / loop1_debt if loop1_debt else float("inf")

st.subheader("Loop 1 Summary")
st.markdown(f"- **Debt After Loop 1:** ${loop1_debt:,.2f}")
st.markdown(f"- **ETH Gained After Loop 1:** {eth_gained_loop1:.2f}")
st.markdown(f"- **ETH Stack After Loop 1:** {eth_stack:.2f}")
st.markdown(f"- **Loop 1 Health Score:** {loop1_health:.2f}")

# Loop 2 Simulation
st.header("Step 3: Loop 2 Evaluation")

results = []
for loop2_ltv in range(30, 51):
    loop2_debt = eth_stack * (loop2_ltv / 100) * eth_price
    final_debt = loop1_debt + loop2_debt
    final_health = (eth_stack * eth_price) / final_debt if final_debt else float("inf")
    liquidation_price = final_debt / eth_stack if eth_stack else 0
    percent_to_liquidation = ((eth_price - liquidation_price) / eth_price) * 100

    if final_health >= 1.6:
        results.append({
            "LTV (%)": loop2_ltv,
            "Health Score": round(final_health, 2),
            "Loan Amount ($)": f"${loop2_debt:,.2f}",
            "% to Liquidation": f"{percent_to_liquidation:.1f}%",
            "ETH Price at Liquidation": f"${liquidation_price:,.2f}"
        })

# Display Table
if results:
    df = pd.DataFrame(results)
    df = df.sort_values(by="Health Score", ascending=False).reset_index(drop=True)
    st.dataframe(df, use_container_width=True)
else:
    st.warning("No Loop 2 options meet the 1.6 health score requirement. Try adjusting Loop 1 LTV.")
