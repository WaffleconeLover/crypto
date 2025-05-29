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

# Session state defaults
if "eth_stack" not in st.session_state:
    st.session_state.eth_stack = 6.73
if "eth_price" not in st.session_state:
    st.session_state.eth_price = 2660
if "first_ltv" not in st.session_state:
    st.session_state.first_ltv = 40.0

# Reset Button
if st.button("🔄 Reset to Defaults"):
    st.session_state.eth_stack = 6.73
    st.session_state.eth_price = 2660
    st.session_state.first_ltv = 40.0
    st.rerun()

# User Inputs with Sliders
eth_stack = st.slider("Current ETH Stack", min_value=1.0, max_value=50.0, value=st.session_state.eth_stack, step=0.01, key="eth_stack")
eth_price = st.slider("Current ETH Price ($)", min_value=500, max_value=10000, value=st.session_state.eth_price, step=10, key="eth_price")
first_ltv_input = st.slider("First Loop LTV (%)", min_value=40.0, max_value=50.0, value=st.session_state.first_ltv, step=2.5, key="first_ltv")

# Simulate LP Exit and Top-Up Panel
st.markdown("### LP Exit Simulation")
eth_from_lp = st.number_input("ETH Gained from LP", min_value=0.0, value=0.0, step=0.01)
eth_stack += eth_from_lp
st.markdown(f"**Updated ETH Stack after LP Exit:** {eth_stack:.2f} ETH")

# Aave Health Indicator (based on 40% base LTV for illustration)
base_ltv = 0.40
collateral_value = eth_stack * eth_price
debt_value = collateral_value * base_ltv
health_score = collateral_value / debt_value if debt_value else 0
st.markdown(f"### 🛡️ Estimated Aave Health Score: **{health_score:.2f}** (based on 40% LTV)")

# LTV Ranges
first_loop_lvts = np.arange(40.0, 52.5, 2.5)
second_loop_lvts = np.arange(30.0, 51.0, 1.0)  # 1% increments from 30 to 50

# Calculate health score and ETH exposure (mock logic)
data = []
for s_ltv in second_loop_lvts:
    for f_ltv in first_loop_lvts:
        final_hs = 1.78 - ((f_ltv - 40) + (s_ltv - 30)) * 0.01
        loop2_usdc = round((eth_stack * eth_price) * (f_ltv / 100) * (s_ltv / 100), -2)
        total_eth = eth_stack + (loop2_usdc / eth_price)
        pct_gain = ((total_eth / eth_stack) - 1) * 100
        liq_drop = round((1 - (1 / final_hs)) * 100)
        liq_price = round(eth_price * (1 - liq_drop / 100))
        data.append({
            "Second LTV": s_ltv,
            "First LTV": f_ltv,
            "Final Health Score": final_hs,
            "Loop 2 USDC": loop2_usdc,
            "Total ETH": total_eth,
            "Label Base": f"HS: {final_hs:.2f} | ${loop2_usdc:,} | ↓{liq_drop}% @ ${liq_price:,} | {total_eth:.2f} ETH (+{int(pct_gain)}%)"

        })

# Filter top 10 by Total ETH with HS >= 1.66 and matching First LTV
safe_data = [d for d in data if d["Final Health Score"] >= 1.66 and d["First LTV"] == first_ltv_input]
sorted_safe_data = sorted(safe_data, key=lambda x: x["Total ETH"], reverse=True)
top_labels = { (d["First LTV"], d["Second LTV"]): rank+1 for rank, d in enumerate(sorted_safe_data[:10]) }

# Add ranks to labels
for entry in data:
    key = (entry["First LTV"], entry["Second LTV"])
    rank_label = f" | #{top_labels[key]}" if key in top_labels else ""
    entry["Label"] = entry["Label Base"] + rank_label

# Filter for current column view only
column_filtered_data = [d for d in data if d["First LTV"] == first_ltv_input]
filtered_df = pd.DataFrame(column_filtered_data)
pivot_hs = filtered_df.pivot(index="Second LTV", columns="First LTV", values="Final Health Score")
pivot_labels = filtered_df.pivot(index="Second LTV", columns="First LTV", values="Label")

# Display Heatmap
sns.set(font_scale=0.7)
fig, ax = plt.subplots(figsize=(8, 14))
sns.heatmap(pivot_hs, annot=pivot_labels, fmt="", cmap="RdYlGn", cbar_kws={'label': 'Final Health Score'}, ax=ax)
plt.title("ETH Leverage Setups with Exposure, Liquidation Risk, and Yield")
st.pyplot(fig)

st.markdown("---")
st.markdown("**Instructions:** Use this tool to explore safe LTV combinations and estimate ETH growth across leverage cycles.")
