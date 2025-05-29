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
    st.session_state.eth_stack = 6.73
    st.session_state.eth_price = 2660
    st.session_state.eth_from_lp = 0.0
    st.session_state.first_ltv = 40.0
    st.experimental_rerun()

# User Inputs with Sliders
if "eth_stack" not in st.session_state:
    st.session_state.eth_stack = 6.73
if "eth_price" not in st.session_state:
    st.session_state.eth_price = 2660
if "eth_from_lp" not in st.session_state:
    st.session_state.eth_from_lp = 0.0
if "first_ltv" not in st.session_state:
    st.session_state.first_ltv = 40.0

eth_stack = st.slider("Current ETH Stack", min_value=1.0, max_value=50.0, value=st.session_state.eth_stack, step=0.01, key="eth_stack")
eth_price = st.slider("Current ETH Price ($)", min_value=500, max_value=10000, value=st.session_state.eth_price, step=10, key="eth_price")
first_ltv_input = st.slider("First Loop LTV (%)", min_value=40.0, max_value=50.0, value=st.session_state.first_ltv, step=0.5, key="first_ltv")

# Simulate LP Exit and Top-Up Panel
st.markdown("### LP Exit Simulation")
eth_from_lp = st.number_input("ETH Gained from LP", min_value=0.0, value=st.session_state.eth_from_lp, step=0.01, key="eth_from_lp")
eth_stack += eth_from_lp
st.markdown(f"**Updated ETH Stack after LP Exit:** {eth_stack:.2f} ETH")

# Aave Health Indicator (based on 40% base LTV)
base_ltv = 0.40
collateral_value = eth_stack * eth_price
debt_value = collateral_value * base_ltv
health_score = collateral_value / debt_value if debt_value else 0
st.markdown(f"### 🛡️ Estimated Aave Health Score: **{health_score:.2f}** (based on 40% LTV)")

# Define LTV ranges
first_loop_lvts = np.arange(40.0, 52.5, 2.5)
second_loop_lvts = np.arange(30.0, 52.5, 2.5)

# Prepare data
data = []
for s_ltv in second_loop_lvts:
    for f_ltv in first_loop_lvts:
        final_hs = 1.78 - ((f_ltv - 40) * 0.01 + (s_ltv - 30) * 0.01)
        loop1_usdc = round(collateral_value * (f_ltv / 100), 2)
        loop2_usdc = round(loop1_usdc * (s_ltv / 100), 2)
        total_debt = loop1_usdc + loop2_usdc
        total_eth = eth_stack + (loop2_usdc / eth_price)
        pct_gain = ((total_eth / eth_stack) - 1) * 100
        liq_drop = round((1 - (1 / final_hs)) * 100)
        liq_price = round(eth_price * (1 - liq_drop / 100))
        label = f"{final_hs:.2f}\n${int(loop2_usdc)}\n\u2193{liq_drop}% @ ${liq_price}\n{total_eth:.2f} ETH (+{int(pct_gain)}%)"
        data.append({
            "Second LTV": s_ltv,
            "First LTV": f_ltv,
            "Final Health Score": final_hs,
            "Label": label,
            "Total ETH": total_eth
        })

# Rank Top 10
df = pd.DataFrame(data)
df_sorted = df.sort_values(by="Total ETH", ascending=False).reset_index(drop=True)
df_sorted["Rank"] = df_sorted.index + 1
df_top10 = df_sorted[df_sorted.Rank <= 10][["First LTV", "Second LTV", "Rank"]]

def add_rank_to_label(row):
    match = df_top10[(df_top10["First LTV"] == row["First LTV"]) & (df_top10["Second LTV"] == row["Second LTV"])].Rank
    if not match.empty:
        return row["Label"] + f"\n#{match.values[0]}"
    return row["Label"]

# Add rank to labels
df["Label"] = df.apply(add_rank_to_label, axis=1)

# Build DataFrame
pivot_hs = df.pivot(index="Second LTV", columns="First LTV", values="Final Health Score")
pivot_labels = df.pivot(index="Second LTV", columns="First LTV", values="Label")

# Display Heatmap
fig, ax = plt.subplots(figsize=(16, 12))
sns.heatmap(pivot_hs, annot=pivot_labels, fmt="", cmap="RdYlGn", cbar_kws={'label': 'Final Health Score'}, ax=ax)
plt.title("ETH Leverage Setups with Exposure, Liquidation Risk, and Yield")
st.pyplot(fig)

st.markdown("---")
st.markdown("**Instructions:** Use this tool to explore safe LTV combinations and estimate ETH growth across leverage cycles.")
