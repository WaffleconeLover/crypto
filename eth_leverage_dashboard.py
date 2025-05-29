import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# Page config
st.set_page_config(page_title="ETH Leverage Strategy Dashboard", layout="wide")
st.markdown("<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True)

st.title("ETH Leverage Heatmap")

# Session state defaults
if "eth_stack" not in st.session_state:
    st.session_state.eth_stack = 6.73
if "eth_price" not in st.session_state:
    st.session_state.eth_price = 2660.0
if "first_ltv" not in st.session_state:
    st.session_state.first_ltv = 40.0

# Reset button
if st.button("🔄 Reset to Defaults"):
    st.session_state.eth_stack = 6.73
    st.session_state.eth_price = 2660.0
    st.session_state.first_ltv = 40.0
    st.experimental_rerun()

# Sliders
eth_stack = st.slider("Current ETH Stack", min_value=1.0, max_value=50.0, value=st.session_state.eth_stack, step=0.01, key="eth_stack")
eth_price = st.slider("Current ETH Price ($)", min_value=500, max_value=10000, value=st.session_state.eth_price, step=10, key="eth_price")
first_ltv = st.slider("First Loop LTV (%)", min_value=40.0, max_value=50.0, value=st.session_state.first_ltv, step=2.5, key="first_ltv")

# LP exit simulation
st.markdown("### LP Exit Simulation")
eth_from_lp = st.number_input("ETH Gained from LP", min_value=0.0, value=0.0, step=0.01)
eth_stack += eth_from_lp
st.markdown(f"**Updated ETH Stack after LP Exit:** {eth_stack:.2f} ETH")

# Health indicator
base_ltv = 0.4
collateral_value = eth_stack * eth_price
debt_value = collateral_value * base_ltv
health_score = collateral_value / debt_value if debt_value else 0
st.markdown(f"### 🛡️ Estimated Aave Health Score: **{health_score:.2f}** (based on 40% LTV)")

# LTV ranges
second_loop_lvts = np.arange(30.0, 51.0, 1.0)
data = []

# Grid calculations
for s_ltv in second_loop_lvts:
    final_hs = 1.78 - ((first_ltv - 40) + (s_ltv - 30)) * 0.01
    loop2_usdc = round((eth_stack * eth_price) * (first_ltv / 100) * (s_ltv / 100), -2)
    total_eth = eth_stack + (loop2_usdc / eth_price)
    pct_gain = ((total_eth / eth_stack) - 1) * 100
    liq_drop = round((1 - (1 / final_hs)) * 100)
    liq_price = round(eth_price * (1 - liq_drop / 100))

    # Fully sanitize labels to remove special characters
    label = f"{final_hs:.2f} | ${loop2_usdc} | Drop {liq_drop}% @ ${liq_price} | {total_eth:.2f} ETH (+{int(pct_gain)}%)"
    label = label.replace("\\", "\\\\")  # escape any backslashes
    data.append({
        "Second LTV": s_ltv,
        "Final Health Score": final_hs,
        "Label": label,
        "ETH Total": total_eth
    })

# Top 10 markers
df = pd.DataFrame(data)
df_sorted = df.sort_values(by="ETH Total", ascending=False).reset_index(drop=True)
df_sorted["Top"] = df_sorted.index + 1
df_sorted.loc[df_sorted["Top"] > 10, "Top"] = ""
df_sorted["Label"] = df_sorted["Label"] + df_sorted["Top"].apply(lambda x: f" | #{x}" if x != "" else "")

# Heatmap prep
pivot_hs = df_sorted.pivot(index="Second LTV", columns="Final Health Score", values="Final Health Score")
pivot_labels = df_sorted.pivot(index="Second LTV", columns="Final Health Score", values="Label")

# Plot with full safety config
plt.rcParams['mathtext.default'] = 'regular'
fig, ax = plt.subplots(figsize=(12, 12))
sns.heatmap(pivot_hs, annot=pivot_labels, fmt="", cmap="RdYlGn", cbar_kws={'label': 'Final Health Score'}, ax=ax)
plt.title("ETH Leverage Setups with Exposure, Liquidation Risk, and Yield")
st.pyplot(fig)

st.markdown("---")
st.markdown("**Instructions:** Use this tool to explore safe LTV combinations and estimate ETH growth across leverage cycles.")
