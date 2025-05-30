import streamlit as st
import pandas as pd
import numpy as np
import requests

st.set_page_config(layout="wide")
st.title("ETH Leverage Loop Simulator")

# --- ETH PRICE ---
st.header("Step 1: ETH Price")

if "eth_price" not in st.session_state:
    st.session_state.eth_price = None

def fetch_eth_price():
    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "ethereum", "vs_currencies": "usd"},
            timeout=5
        )
        res.raise_for_status()
        return res.json()["ethereum"]["usd"]
    except Exception:
        return None

if st.button("Refresh ETH Price from CoinGecko") or st.session_state.eth_price is None:
    price = fetch_eth_price()
    if price:
        st.session_state.eth_price = price

if st.session_state.eth_price:
    eth_price = st.session_state.eth_price
    st.markdown(f"**Real-Time ETH Price:** ${eth_price:,.2f}")
else:
    eth_price = st.number_input("Enter ETH Price ($)", min_value=100.0, value=3000.0, step=1.0)
    st.session_state.eth_price = eth_price

# --- LOOP 1 SETUP ---
st.header("Step 2: Configure Loop 1")

eth_collateral = st.number_input("Initial ETH Collateral", min_value=0.0, value=6.73, step=0.01)
loop1_ltv = st.slider("Loop 1 Borrow LTV (%)", min_value=10, max_value=50, value=40, step=1)

loop1_debt = eth_collateral * (loop1_ltv / 100) * eth_price
eth_gained_loop1 = loop1_debt / eth_price
eth_stack = eth_collateral + eth_gained_loop1
loop1_health = (eth_stack * eth_price) / loop1_debt if loop1_debt else float("inf")

# --- LOOP 1 SUMMARY ---
st.subheader("Loop 1 Summary")
st.markdown(f"- **Debt After Loop 1:** ${loop1_debt:,.2f}")
st.markdown(f"- **ETH Gained After Loop 1:** {eth_gained_loop1:.2f}")
st.markdown(f"- **ETH Stack After Loop 1:** {eth_stack:.2f}")
st.markdown(f"- **Loop 1 Health Score:** {loop1_health:.2f}")

# --- LOOP 2 SIMULATION ---
st.header("Step 3: Loop 2 Evaluation")

rows = []
for ltv2 in range(30, 51):  # 30–50 inclusive
    loop2_debt = eth_stack * (ltv2 / 100) * eth_price
    total_debt = loop1_debt + loop2_debt
    health = (eth_stack * eth_price) / total_debt
    liquidation_price = total_debt / eth_stack
    liquidation_pct = (eth_price - liquidation_price) / eth_price * 100

    rows.append({
        "LTV (%)": ltv2,
        "Health Score": round(health, 2),
        "Loan Amount ($)": f"${loop2_debt:,.2f}",
        "% to Liquidation": f"{liquidation_pct:.1f}%",
        "ETH Price at Liquidation": f"${liquidation_price:,.2f}"
    })

df = pd.DataFrame(rows)

# Show entire table with sorting/filtering via dataframe view
st.dataframe(df, use_container_width=True, hide_index=True)
