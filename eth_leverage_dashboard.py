import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# Streamlit Page Setup
st.set_page_config(page_title="ETH Leverage Strategy Dashboard", layout="wide")

# Add layout spacing controls
st.markdown("<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True)

st.title("ETH Leverage Heatmap")

# Reset Button
if st.button("🔄 Reset to Defaults"):
    st.experimental_rerun()

# User Inputs with Sliders
eth_stack = st.slider("Current ETH Stack", min_value=1.0, max_value=50.0, value=6.73, step=0.01)
eth_price = st.slider("Current ETH Price ($)", min_value=500, max_value=10000, value=2660, step=10)

# Simulate LP Exit and Top-Up Panel
st.markdown("### LP Exit Simulation")
eth_from_lp = st.number_input("ETH Gained from LP", min_value=0.0, value=0.0, step=0.01)
eth_stack += eth_from_lp
st.markdown(f"**Updated ETH Stack after LP Exit:** {eth_stack:.2f} ETH")

# Aave Health Indicator (based on 45% base LTV for illustration)
base_ltv = 0.45
collateral_value = eth_stack * eth_price
debt_value = collateral_value * base_ltv
health_score = collateral_value / debt_value if debt_value else 0
st.markdown(f"### 🛡️ Estimated Aave Health Score: **{health_score:.2f}** (based on 45% LTV)")

first_loop_lvts = np.arange(40.0, 52.5, 2.5)
second_loop_lvts = np.arange(30.0, 52.5, 2.5)

# Calculate health score and ETH exposure (mock logic)
data = []
for s_ltv in second_loop_lvts:
    for f_ltv in first_loop_lvts:
        final_hs = 1.78 - ((f_ltv - 40) + (s_ltv - 30)) * 0.01  # mock health score
        loop2_usdc = round((eth_stack * eth_price) * (f_ltv / 100) * (s_ltv / 100), -2)
        total_eth = eth_stack + (loop2_usdc / eth_price)
        pct_gain = ((total_eth / eth_stack) - 1) * 100
        liq_drop = round((1 - (1 / final_hs)) * 100)  # approximate
        liq_price = round(eth_price * (1 - liq_drop / 100))
        label = f"{final_hs:.2f}\n${loop2_usdc}\n\u2193{liq_drop}% @ ${liq_price}\n{total_eth:.2f} ETH (+{int(pct_gain)}%)"
        data.append({
            "Second LTV": s_ltv,
            "First LTV": f_ltv,
            "Final Health Score": final_hs,
            "Label": label
        })

# Build DataFrame
heatmap_df = pd.DataFrame(data)
pivot_hs = heatmap_df.pivot(index="Second LTV", columns="First LTV", values="Final Health Score")
pivot_labels = heatmap_df.pivot(index="Second LTV", columns="First LTV", values="Label")

# Display Heatmap
fig, ax = plt.subplots(figsize=(14, 10))
sns.heatmap(pivot_hs, annot=pivot_labels, fmt="", cmap="RdYlGn", cbar_kws={'label': 'Final Health Score'}, ax=ax)
plt.title("ETH Leverage Setups with Exposure, Liquidation Risk, and Yield")
st.pyplot(fig)

st.markdown("---")
st.markdown("**Instructions:** Use this tool to explore safe LTV combinations and estimate ETH growth across leverage cycles.")
