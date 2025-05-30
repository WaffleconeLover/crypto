import streamlit as st
import pandas as pd
import numpy as np
import requests

st.set_page_config(page_title="ETH Leverage Loop Simulator", layout="wide")

# -----------------------------
# Real-Time ETH Price
# -----------------------------
def fetch_eth_price():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        return response.json()['ethereum']['usd']
    except:
        return None

if 'eth_price' not in st.session_state:
    st.session_state.eth_price = fetch_eth_price()

st.title("ETH Leverage Loop Simulator")

st.header("Step 1: ETH Price")
if st.button("Refresh ETH Price from CoinGecko"):
    st.session_state.eth_price = fetch_eth_price()

eth_price = st.session_state.eth_price
if eth_price:
    st.markdown(f"**Real-Time ETH Price:** ${eth_price:,.2f}")
else:
    eth_price = st.number_input("Manual ETH Price Input ($)", min_value=100.0, max_value=10000.0, value=2600.0, step=10.0)

# -----------------------------
# Loop 1 Setup
# -----------------------------
st.header("Step 2: Configure Loop 1")
eth_collateral = st.number_input("Initial ETH Collateral", min_value=0.01, value=6.73, step=0.01)
ltv1 = st.slider("Loop 1 Borrow LTV (%)", min_value=10, max_value=58, value=40)

# Loop 1 Calculations
debt1 = eth_collateral * eth_price * (ltv1 / 100)
eth_gained1 = debt1 / eth_price
eth_stack1 = eth_collateral + eth_gained1
health1 = eth_stack1 * eth_price / debt1 if debt1 else np.nan

st.subheader("Loop 1 Summary")
st.markdown(f"- **Debt After Loop 1:** ${debt1:,.2f}")
st.markdown(f"- **ETH Gained After Loop 1:** {eth_gained1:,.2f}")
st.markdown(f"- **ETH Stack After Loop 1:** {eth_stack1:,.2f}")
st.markdown(f"- **Loop 1 Health Score:** {health1:.2f}")

# -----------------------------
# Loop 2 Grid
# -----------------------------
st.header("Step 3: Loop 2 Evaluation")

loop2_data = []
for ltv2 in range(30, 51):
    loan2 = eth_stack1 * eth_price * (ltv2 / 100)
    total_debt = debt1 + loan2
    health2 = eth_stack1 * eth_price / total_debt if total_debt else np.nan
    liquidation_pct = 1 - (0.85 / health2) if health2 > 0 else 0
    liquidation_price = eth_price * (1 - liquidation_pct) if liquidation_pct > 0 else 0
    loop2_data.append({
        "LTV (%)": ltv2,
        "Health Score": round(health2, 2),
        "Loan Amount ($)": f"${loan2:,.2f}",
        "% to Liquidation": f"{liquidation_pct * 100:.1f}%" if liquidation_pct > 0 else "-",
        "ETH Price at Liquidation": f"${liquidation_price:,.2f}" if liquidation_price > 0 else "-"
    })

loop2_df = pd.DataFrame(loop2_data)

st.dataframe(loop2_df, use_container_width=True)
