import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("ETH Leverage Strategy Dashboard")

# --- Session State Setup ---
if "eth_price" not in st.session_state:
    st.session_state.eth_price = 3500.00  # default fallback price
if "collateral_eth" not in st.session_state:
    st.session_state.collateral_eth = 6.73  # default ETH collateral

# --- Reset Button ---
if st.button("🔄 Reset All"):
    st.session_state.eth_price = 3500.00
    st.session_state.collateral_eth = 6.73
    st.experimental_rerun()

# --- Input Section ---
st.header("Loop 1 Setup")

eth_price = st.number_input("Current ETH Price ($)", min_value=500.0, max_value=10000.0,
                            value=st.session_state.eth_price, step=10.0)
st.session_state.eth_price = eth_price

collateral_eth = st.number_input("Current ETH Collateral", min_value=0.0,
                                 value=st.session_state.collateral_eth, step=0.1)
st.session_state.collateral_eth = collateral_eth

ltv1 = st.slider("Loop 1 Borrow LTV (%)", min_value=30, max_value=60, value=40, step=1)

# --- Loop 1 Calculations ---
collateral_usd = collateral_eth * eth_price
loop1_debt = (ltv1 / 100) * collateral_usd
eth_gained = loop1_debt / eth_price
eth_stack = collateral_eth + eth_gained
loop1_health_score = collateral_usd / loop1_debt if loop1_debt else np.inf

st.subheader("Loop 1 Results")
st.markdown(f"**Debt After Loop 1:**  ${loop1_debt:,.2f}")
st.markdown(f"**ETH Gained After Loop 1:**  {eth_gained:,.2f}")
st.markdown(f"**ETH Stack After Loop 1:**  {eth_stack:,.2f}")
st.markdown(f"**Loop 1 Health Score:**  {loop1_health_score:.2f}")

# --- Loop 2 Simulation (Only show if Loop 1 health score is healthy) ---
if loop1_health_score < 1.6:
    st.warning("Loop 1 Health Score is too low. Adjust LTV or collateral.")
else:
    st.header("Loop 2 Simulation")

    results = []
    for ltv2 in range(30, 51):
        loop2_debt = (ltv2 / 100) * eth_stack * eth_price
        total_debt = loop1_debt + loop2_debt
        liquidation_price = (total_debt / eth_stack) * 0.9  # Example logic
        health_score = (eth_stack * eth_price) / total_debt if total_debt else np.inf
        pct_to_liquidation = (1 - liquidation_price / eth_price) * 100

        if health_score >= 1.6:
            results.append({
                "LTV Loop 2 (%)": ltv2,
                "USDC Loan": loop2_debt,
                "Health Score": health_score,
                "% to Liquidation": pct_to_liquidation,
                "Price at Liquidation": liquidation_price
            })

    if not results:
        st.warning("No viable Loop 2 options found with current settings.")
    else:
        df = pd.DataFrame(results)
        df["Score"] = df["Health Score"] * 1.5 + df["% to Liquidation"] * 1.2 + df["USDC Loan"] / 1000
        df["Rank"] = df["Score"].rank(ascending=False).astype(int)
        df = df.sort_values("Rank")

        # --- Style Function ---
        def style_loop2_table(df):
            return df.style \
                .background_gradient(subset=["Health Score"], cmap="RdYlGn") \
                .background_gradient(subset=["% to Liquidation"], cmap="YlGnBu") \
                .background_gradient(subset=["USDC Loan"], cmap="Blues") \
                .highlight_min(subset=["Rank"], color="lightyellow") \
                .format({
                    "USDC Loan": "${:,.2f}",
                    "Health Score": "{:.2f}",
                    "% to Liquidation": "{:.1f}%",
                    "Price at Liquidation": "${:,.2f}"
                })

        styled_df = style_loop2_table(df.drop(columns=["Score"]).reset_index(drop=True))
        st.dataframe(styled_df, use_container_width=True)
