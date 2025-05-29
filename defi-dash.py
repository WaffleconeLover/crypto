import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# Streamlit config
st.set_page_config(page_title="ETH Leverage Heatmap", layout="wide")

st.title("ETH Leverage Heatmap")

# Input sliders
eth_stack = st.slider("Current ETH Stack", min_value=1.0, max_value=50.0, value=6.73, step=0.01)
eth_price = st.slider("Current ETH Price ($)", min_value=500, max_value=10000, value=2660, step=10)

# Base LTV for Aave Health Score Estimation
base_ltv = 0.40
collateral_value = eth_stack * eth_price
debt_value = collateral_value * base_ltv
health_score = collateral_value / debt_value if debt_value else 0
st.markdown(f"### \U0001F6E1\ufe0f Estimated Aave Health Score: **{health_score:.2f}** (based on {int(base_ltv * 100)}% LTV)")

# Grid definitions
first_loop_lvts = np.arange(40.0, 52.5, 2.5)
second_loop_lvts = np.arange(30.0, 52.5, 2.5)

# Simulate combinations
data = []
for s_ltv in second_loop_lvts:
    for f_ltv in first_loop_lvts:
        final_hs = 1.78 - ((f_ltv - 40) + (s_ltv - 30)) * 0.01
        loop2_usdc = round((eth_stack * eth_price) * (f_ltv / 100) * (s_ltv / 100), -2)
        total_eth = eth_stack + (loop2_usdc / eth_price)
        pct_gain = ((total_eth / eth_stack) - 1) * 100
        liq_drop = round((1 - (1 / final_hs)) * 100)
        liq_price = round(eth_price * (1 - liq_drop / 100))
        label = f"{final_hs:.2f}\n${loop2_usdc}\n\u2193{liq_drop}% @ ${liq_price}\n{total_eth:.2f} ETH (+{int(pct_gain)}%)"
        data.append({
            "Second LTV": s_ltv,
            "First LTV": f_ltv,
            "Final Health Score": final_hs,
            "Label": label
        })

# DataFrame and pivot
heatmap_df = pd.DataFrame(data)
pivot_hs = heatmap_df.pivot(index="Second LTV", columns="First LTV", values="Final Health Score")
pivot_labels = heatmap_df.pivot(index="Second LTV", columns="First LTV", values="Label")

# Plot heatmap
fig, ax = plt.subplots(figsize=(12, 9))
sns.heatmap(pivot_hs, annot=pivot_labels, fmt="", cmap="RdYlGn", cbar_kws={'label': 'Final Health Score'}, ax=ax)
plt.title("Top ETH Leverage Setups with Exposure, Liquidation Risk, and Yield")
plt.xlabel("First Loop LTV (%)")
plt.ylabel("Second Loop LTV (%)")
st.pyplot(fig)

st.markdown("**Instructions:** Use this tool to explore safe LTV combinations and estimate ETH growth across leverage cycles.")
