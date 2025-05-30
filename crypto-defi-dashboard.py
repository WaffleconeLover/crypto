import streamlit as st
import pandas as pd
import numpy as np
import requests

st.set_page_config(layout="wide")

st.title("ETH Leverage Loop Simulator")

# Initialize session state
if "eth_price" not in st.session_state:
    st.session_state.eth_price = None

# Fetch live ETH price
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

# Step 1: ETH Price Input
st.header("Step 1: ETH Price")
if st.button("Refresh ETH Price from CoinGecko") or st.session_state.eth_price is None:
    price = fetch_eth_price()
    if price:
        st.session_state.eth_price = price

if st.session_state.eth_price:
    eth_price = st.session_state.eth_price
    st.markdown(f"**Real-Time ETH Price:** ${eth_price:,.2f}")
else:
    eth_price = st.number_input("Enter ETH Price ($)", min_value=0.0, value=3000.0, step=1.0)
    st.session_state.eth_price = eth_price

# Step 2: Loop 1 Configuration
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

# Step 3: Loop 2 Evaluation
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

# Display interactive table
if results:
    df = pd.DataFrame(results)
    st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "LTV (%)": st.column_config.NumberColumn("LTV (%)", width="small"),
            "Health Score": st.column_config.NumberColumn("Health Score", width="small"),
            "Loan Amount ($)": st.column_config.TextColumn("Loan Amount ($)", width="medium"),
            "% to Liquidation": st.column_config.TextColumn("% to Liquidation", width="medium"),
            "ETH Price at Liquidation": st.column_config.TextColumn("ETH Price at Liquidation", width="medium"),
        },
        num_rows="fixed"
    )
else:
    st.warning("No Loop 2 options meet the 1.6 health score requirement. Try adjusting Loop 1 LTV.")
