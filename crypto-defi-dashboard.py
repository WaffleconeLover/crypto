import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("ETH Leverage Strategy Dashboard")

# --- Session State Defaults ---
if "eth_price" not in st.session_state:
    st.session_state.eth_price = 3500.00
if "collateral_eth" not in st.session_state:
    st.session_state.collateral_eth = 6.73

# --- Reset Button ---
if st.button("🔁 Reset All"):
    st.session_state.eth_price = 3500.00
    st.session_state.collateral_eth = 6.73
    st.experimental_rerun()

# --- Loop 1 Setup ---
st.header("Loop 1 Setup")
eth_price = st.number_input("Current ETH Price ($)", min_value=500.0, max_value=10000.0, value=st.session_state.eth_price, step=10.0)
collateral_eth = st.number_input("Current ETH Collateral", min_value=0.0, value=st.session_state.collateral_eth, step=0.1)
ltv1 = st.slider("Loop 1 Borrow LTV (%)", min_value=30, max_value=60, value=40, step=1)

st.session_state.eth_price = eth_price
st.session_state.collateral_eth = collateral_eth

# --- Loop 1 Calculations ---
collateral_usd = collateral_eth * eth_price
loop1_debt = (ltv1 / 100) * collateral_usd
eth_gained = loop1_debt / eth_price
eth_stack = collateral_eth + eth_gained
loop1_health_score = collateral_usd / loop1_debt if loop1_debt else np.inf

# --- Display Loop 1 Results ---
st.subheader("Loop 1 Results")
st.markdown(f"**Debt After Loop 1:** ${loop1_debt:,.2f}")
st.markdown(f"**ETH Gained After Loop 1:** {eth_gained:,.2f}")
st.markdown(f"**ETH Stack After Loop 1:** {eth_stack:,.2f}")
st.markdown(f"**Loop 1 Health Score:** {loop1_health_score:.2f}")

# --- Loop 2 Simulation ---
if loop1_health_score < 1.6:
    st.warning("Loop 1 Health Score is too low. Adjust LTV or collateral to explore Loop 2.")
else:
    st.header("Loop 2 Simulation")
    loop2_results = []

    for ltv2 in range(30, 51):
        loop2_debt = (ltv2 / 100) * eth_stack * eth_price
        total_debt = loop1_debt + loop2_debt
        liquidation_price = (total_debt / eth_stack) * 0.9
        health_score = (eth_stack * eth_price) / total_debt if total_debt else np.inf
        pct_to_liq = (1 - liquidation_price / eth_price) * 100

        if health_score >= 1.6:
            loop2_results.append({
                "LTV Loop 2 (%)": ltv2,
                "USDC Loan": loop2_debt,
                "Health Score": health_score,
                "% to Liquidation": pct_to_liq,
                "Price at Liquidation": liquidation_price
            })

    if not loop2_results:
        st.warning("No Loop 2 options meet the minimum health score of 1.6. Adjust LTV or ETH collateral.")
    else:
        df = pd.DataFrame(loop2_results)
        df["Score"] = df["Health Score"] * 1.5 + df["% to Liquidation"] * 1.2 + df["USDC Loan"] / 1000
        df["Rank"] = df["Score"].rank(ascending=False).astype(int)
        df = df.sort_values("Rank").reset_index(drop=True)

        # --- Format Display Columns ---
        df_display = df.drop(columns=["Score"])
        df_display["USDC Loan"] = df_display["USDC Loan"].apply(lambda x: f"${x:,.2f}")
        df_display["Health Score"] = df_display["Health Score"].apply(lambda x: f"{x:.2f}")
        df_display["% to Liquidation"] = df_display["% to Liquidation"].apply(lambda x: f"{x:.1f}%")
        df_display["Price at Liquidation"] = df_display["Price at Liquidation"].apply(lambda x: f"${x:,.2f}")

        st.dataframe(df_display, use_container_width=True, hide_index=True)
