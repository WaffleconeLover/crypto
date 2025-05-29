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

# Grid definitions
first_loop_lvts = np.arange(40.0, 52.5, 2.5)
second_loop_lvts = np.arange(30.0, 52.5, 2.5)

# Simulate combinations
data = []
for s_ltv in second_loop_lvts:
    for f_ltv in first_loop_lvts:
        # Loop 1
        loop1_debt = eth_stack * eth_price * (f_ltv / 100)
        eth_bought_1 = loop1_debt / eth_price
        new_eth_1 = eth_stack + eth_bought_1
        collateral_after_loop1 = new_eth_1 * eth_price
        hs_loop1 = (collateral_after_loop1 * 0.8) / loop1_debt

        # Loop 2
        loop2_debt = collateral_after_loop1 * (s_ltv / 100)
        eth_bought_2 = loop2_debt / eth_price
        total_eth = new_eth_1 + eth_bought_2
        total_collateral = total_eth * eth_price
        total_debt = loop1_debt + loop2_debt
        final_hs = (total_collateral * 0.8) / total_debt

        # Liquidation info
        liq_price = round((total_debt / (total_eth * 0.8)), 2)
        liq_drop_pct = round((1 - (liq_price / eth_price)) * 100)

        # Exposure gain
        pct_gain = ((total_eth / eth_stack) - 1) * 100

        # Label format
        label = f"{final_hs:.2f}\n${int(loop2_debt)}\n\u2193{liq_drop_pct}% @ ${liq_price}\n{total_eth:.2f} ETH (+{int(pct_gain)}%)"

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
