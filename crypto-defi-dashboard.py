import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import requests

# Streamlit config
st.set_page_config(page_title="ETH Leverage Heatmap", layout="wide")
st.title("ETH Leverage Heatmap")

# Session state setup
defaults = {
    "eth_stack": 6.73,
    "eth_price_input": 2660,
    "eth_gained": 0.0,
    "loop1_eth": 10.4,
    "loop1_debt": 11200.0
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

col1, col2 = st.columns(2)
with col1:
    if st.button("🔁 Reset App (keep Loop 1)"):
        st.session_state.eth_stack = 6.73
        st.session_state.eth_price_input = 2660
        st.session_state.eth_gained = 0.0
with col2:
    if st.button("❌ Reset Loop 1 Inputs"):
        st.session_state.loop1_eth = 10.4
        st.session_state.loop1_debt = 11200.0

# ETH price logic
eth_price_live = None
try:
    response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
    eth_price_live = response.json().get("ethereum", {}).get("usd")
except:
    eth_price_live = None

if eth_price_live:
    st.markdown(f"**Live ETH Price from CoinGecko: ${eth_price_live:.2f}**")
    eth_price = eth_price_live
else:
    st.warning("Unable to fetch live ETH price. Please enter it manually.")
    eth_price = st.number_input("Manual ETH Price Input ($)", min_value=100.0, max_value=10000.0,
                                value=float(st.session_state.eth_price_input), step=10.0)
    st.session_state.eth_price_input = eth_price

eth_stack = st.slider("Current ETH Stack", 1.0, 50.0, st.session_state.eth_stack, step=0.01)
st.session_state.eth_stack = eth_stack

# Loop 1 Setup
st.markdown("### Manual Loop 1 Setup")
loop1_eth = st.number_input("ETH Stack After Loop 1", min_value=0.0, value=st.session_state.loop1_eth, step=0.01)
loop1_debt = st.number_input("Debt After Loop 1 ($)", min_value=0.0, value=float(st.session_state.loop1_debt), step=10.0)
st.session_state.loop1_eth = loop1_eth
st.session_state.loop1_debt = loop1_debt

loop1_health = (loop1_eth * eth_price * 0.8) / loop1_debt if loop1_debt > 0 else 0
st.markdown(f"**Loop 1 Health Score: {loop1_health:.2f}**")

# LP Exit Simulation
st.markdown("### LP Exit Simulation")
eth_gained = st.number_input("ETH Gained from LP", min_value=0.0, value=st.session_state.eth_gained, step=0.01)
st.session_state.eth_gained = eth_gained
updated_eth_stack = eth_stack + eth_gained
st.markdown(f"**Updated ETH Stack after LP Exit: {updated_eth_stack:.2f} ETH**")

# Loop 2 Calculations
second_loop_lvts = np.arange(30.0, 52.0, 1.0)
first_loop_eth = loop1_eth
first_loop_debt = loop1_debt
first_loop_collateral = first_loop_eth * eth_price

data = []
for s_ltv in second_loop_lvts:
    loop2_debt = first_loop_collateral * (s_ltv / 100)
    eth_bought_2 = loop2_debt / eth_price
    total_eth = first_loop_eth + eth_bought_2
    total_collateral = total_eth * eth_price
    total_debt = first_loop_debt + loop2_debt
    final_hs = (total_collateral * 0.8) / total_debt if total_debt > 0 else 0
    liq_price = round((total_debt / (total_eth * 0.8)), 2) if total_eth > 0 else 0
    liq_drop_pct = round((1 - (liq_price / eth_price)) * 100) if eth_price > 0 else 0
    pct_gain = ((total_eth / eth_stack) - 1) * 100 if eth_stack > 0 else 0

    data.append({
        "Second LTV": s_ltv,
        "First LTV": "Input",
        "Final Health Score": final_hs,
        "Loop 2 Debt": int(loop2_debt),
        "Liq Price": liq_price,
        "Liq Drop %": liq_drop_pct,
        "Total ETH": total_eth,
        "ETH Gain %": pct_gain
    })

heatmap_df = pd.DataFrame(data)
heatmap_df = heatmap_df[heatmap_df["Final Health Score"] >= 1.6].copy()

# Drop any rows that are incomplete
heatmap_df = heatmap_df.dropna()

# Ensure no NaNs before labeling
required_cols = ["Final Health Score", "Loop 2 Debt", "Liq Drop %", "Liq Price", "Total ETH", "ETH Gain %", "Rank"]
heatmap_df = heatmap_df.dropna(subset=required_cols)

# Add formatted label safely
def format_label(row):
    try:
        return (
            f"{strip_zero(row['Final Health Score'])}\n"
            f"${row['Loop 2 Debt']}\n"
            f"↓{int(row['Liq Drop %'])}% @ ${strip_zero(row['Liq Price'])}\n"
            f"{strip_zero(row['Total ETH'])} ETH (+{int(row['ETH Gain %'])}%)\n"
            f"#{int(row['Rank'])}"
        )
    except:
        return ""

heatmap_df["Label"] = heatmap_df.apply(format_label, axis=1)

heatmap_df = heatmap_df.sort_values("Score", ascending=False).copy()
heatmap_df["Rank"] = range(1, len(heatmap_df) + 1)

def strip_zero(val):
    return f"{val:.2f}".rstrip("0").rstrip(".")

heatmap_df["Label"] = heatmap_df.apply(
    lambda row: (
        f"{strip_zero(row['Final Health Score'])}\n"
        f"${row['Loop 2 Debt']}\n"
        f"↓{row['Liq Drop %']}% @ ${strip_zero(row['Liq Price'])}\n"
        f"{strip_zero(row['Total ETH'])} ETH (+{int(row['ETH Gain %'])}%)\n"
        f"#{int(row['Rank'])}"
    ),
    axis=1
)

# Pivot and plot
pivot_hs = heatmap_df.pivot(index="Second LTV", columns="First LTV", values="Final Health Score")
pivot_labels = heatmap_df.pivot(index="Second LTV", columns="First LTV", values="Label")

fig, ax = plt.subplots(figsize=(6, 14))
sns.heatmap(
    pivot_hs,
    annot=pivot_labels,
    fmt="",
    cmap="RdYlGn",
    cbar_kws={'label': 'Final Health Score'},
    annot_kws={'fontsize': 7},
    ax=ax
)
plt.title("Top ETH Leverage Setups with Exposure, Liquidation Risk, and Yield")
plt.xlabel("First Loop LTV (%)")
plt.ylabel("Second Loop LTV (%)")
st.pyplot(fig)

st.markdown("**Instructions:** Loop 1 is now manually set. Explore granular Loop 2 options with a minimum health score of 1.6.")
