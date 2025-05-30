import streamlit as st
import pandas as pd
import numpy as np
import requests

st.set_page_config(page_title="ETH Leverage Loop Simulator", layout="wide")
st.title("ETH Leverage Loop Simulator")

# ---------- Fetch ETH Price ----------
def fetch_eth_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()["ethereum"]["usd"]
    except:
        return None

if "eth_price" not in st.session_state:
    st.session_state.eth_price = fetch_eth_price() or 2500.0

if st.button("Refresh ETH Price from CoinGecko"):
    st.session_state.eth_price = fetch_eth_price() or st.session_state.eth_price

eth_price = st.session_state.eth_price
st.markdown(f"**Real-Time ETH Price:** ${eth_price:,.2f}")

# ---------- Loop 1 Configuration ----------
st.header("Step 2: Configure Loop 1")
eth_collateral = st.number_input("Initial ETH Collateral", min_value=0.01, value=6.73, step=0.01)
ltv1 = st.slider("Loop 1 Borrow LTV (%)", min_value=10, max_value=50, value=40, step=1)

loop1_debt = eth_collateral * eth_price * (ltv1 / 100)
eth_gained = loop1_debt / eth_price
eth_stack = eth_collateral + eth_gained
health1 = (eth_stack * eth_price) / loop1_debt if loop1_debt > 0 else 0

# ---------- Loop 1 Summary ----------
st.subheader("Loop 1 Summary")
st.markdown(f"- **Debt After Loop 1:** ${loop1_debt:,.2f}")
st.markdown(f"- **ETH Gained After Loop 1:** {eth_gained:,.2f}")
st.markdown(f"- **ETH Stack After Loop 1:** {eth_stack:,.2f}")
st.markdown(f"- **Loop 1 Health Score:** {health1:.2f}")

# ---------- Loop 2 Evaluation ----------
st.header("Step 3: Loop 2 Evaluation")
ltv2_range = range(30, 51)
data = []
for ltv2 in ltv2_range:
    loan2 = eth_stack * eth_price * (ltv2 / 100)
    total_debt = loop1_debt + loan2
    health2 = (eth_stack * eth_price) / total_debt if total_debt > 0 else 0
    liq_pct = 1 - (1 / health2) if health2 > 0 else 0
    liq_price = eth_price * liq_pct
    data.append({
        "LTV (%)": ltv2,
        "Health Score": round(health2, 2),
        "Loan Amount ($)": f"${loan2:,.2f}",
        "% to Liquidation": f"{liq_pct:.1%}",
        "ETH Price at Liquidation": f"${liq_price:,.2f}"
    })

results_df = pd.DataFrame(data)
st.dataframe(results_df, use_container_width=True)
