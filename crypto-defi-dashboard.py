import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("ETH Looping Dashboard")

# --- Loop 1 Inputs ---
st.header("Loop 1 Setup")
eth_price = st.number_input("ETH Price (live or manual)", value=2500.0, min_value=100.0, max_value=10000.0, step=10.0)
eth_collateral = st.number_input("ETH Collateral", value=6.73, min_value=0.0, step=0.01)
ltv_1 = st.slider("Target LTV for Loop 1", min_value=30.0, max_value=68.0, value=40.0, step=0.5)

# --- Loop 1 Calculations ---
debt_1 = eth_collateral * eth_price * ltv_1 / 100
eth_gained_1 = debt_1 / eth_price
eth_stack_1 = eth_collateral + eth_gained_1
health_score_1 = eth_stack_1 * eth_price / debt_1 if debt_1 else 0

st.markdown(f"**Debt After Loop 1:** ${debt_1:,.2f}")
st.markdown(f"**ETH Gained After Loop 1:** {eth_gained_1:.2f}")
st.markdown(f"**ETH Stack After Loop 1:** {eth_stack_1:.2f}")
st.markdown(f"**Loop 1 Health Score:** {health_score_1:.2f}")

# --- Loop 2 Grid ---
st.header("Loop 2 Grid")
ltv_2_range = np.arange(30, 51, 1)
health_scores = []

for ltv_2 in ltv_2_range:
    debt_2 = eth_stack_1 * eth_price * ltv_2 / 100
    health_score_2 = eth_stack_1 * eth_price / debt_2 if debt_2 else 0
    liquidation_price = (1 - ltv_2 / 100) * eth_price
    to_liquidation = 100 * (eth_price - liquidation_price) / eth_price
    health_scores.append({
        "Second Loop LTV (%)": ltv_2,
        "Final Health Score": round(health_score_2, 2),
        "USDC Loan": f"${debt_2:,.0f}",
        "% to Liquidation": f"{to_liquidation:.0f}%",
        "Liquidation Price": f"${liquidation_price:,.0f}"
    })

heatmap_df = pd.DataFrame(health_scores)
filtered_df = heatmap_df[heatmap_df["Final Health Score"] >= 1.6]

if filtered_df.empty:
    st.warning("No Loop 2 options meet the minimum health score of 1.6. Adjust LTV or ETH collateral.")
else:
    st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

st.button("Reset Inputs", on_click=lambda: st.experimental_rerun())
