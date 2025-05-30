import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import requests

# Streamlit config
st.set_page_config(page_title="ETH Leverage Heatmap", layout="wide")

st.title("ETH Leverage Heatmap")

# Try real-time ETH price
eth_price_default = 2660
try:
    eth_response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
    eth_price_live = eth_response.json().get("ethereum", {}).get("usd", eth_price_default)
    st.markdown(f"**Live ETH Price from CoinGecko: ${eth_price_live:.2f}**")
except:
    eth_price_live = eth_price_default
    st.warning("Unable to fetch live ETH price, using default.")

# Input sliders
eth_stack = st.slider("Current ETH Stack", min_value=1.0, max_value=50.0, value=6.73, step=0.01)
eth_price = st.slider("Current ETH Price ($)", min_value=500, max_value=10000, value=int(eth_price_live), step=10)

# Estimated Aave health score
st.markdown(f"### Estimated Aave Health Score: {(eth_stack * eth_price * 0.8) / (eth_stack * eth_price * 0.4):.2f} (based on 40% LTV)")

# LP Exit Simulator
st.markdown("### LP Exit Simulation")
eth_gained = st.number_input("ETH Gained from LP", min_value=0.0, value=0.0, step=0.01)
updated_eth_stack = eth_stack + eth_gained
st.markdown(f"**Updated ETH Stack after LP Exit: {updated_eth_stack:.2f} ETH**")

# Grid definitions (fixed Loop 1 at 40%)
first_loop_ltv = 40.0
second_loop_lvts = np.arange(30.0, 52.0, 1.0)  # more granular loop 2 range

# Simulate combinations
data = []
for s_ltv in second_loop_lvts:
    loop1_debt = eth_stack * eth_price * (first_loop_ltv / 100)
    eth_bought_1 = loop1_debt / eth_price
    new_eth_1 = eth_stack + eth_bought_1
    collateral_after_loop1 = new_eth_1 * eth_price
    hs_loop1 = (collateral_after_loop1 * 0.8) / loop1_debt

    loop2_debt = collateral_after_loop1 * (s_ltv / 100)
    eth_bought_2 = loop2_debt / eth_price
    total_eth = new_eth_1 + eth_bought_2
    total_collateral = total_eth * eth_price
    total_debt = loop1_debt + loop2_debt
    final_hs = (total_collateral * 0.8) / total_debt

    liq_price = round((total_debt / (total_eth * 0.8)), 2)
    liq_drop_pct = round((1 - (liq_price / eth_price)) * 100)

    pct_gain = ((total_eth / eth_stack) - 1) * 100

    data.append({
        "Second LTV": s_ltv,
        "First LTV": first_loop_ltv,
        "Final Health Score": final_hs,
        "Loop 2 Debt": int(loop2_debt),
        "Liq Price": liq_price,
        "Liq Drop %": liq_drop_pct,
        "Total ETH": total_eth,
        "ETH Gain %": pct_gain
    })

heatmap_df = pd.DataFrame(data)

# Filter to minimum health threshold
heatmap_df = heatmap_df[heatmap_df["Final Health Score"] >= 1.6].copy()

# Rebalanced scoring
heatmap_df["Score"] = (
    heatmap_df["Final Health Score"] * 40 +
    heatmap_df["Liq Drop %"] * 0.4 +
    heatmap_df["ETH Gain %"] * 0.2 +
    heatmap_df["Loop 2 Debt"] * 0.015
)

# Rank all rows by score
heatmap_df = heatmap_df.sort_values("Score", ascending=False).copy()
heatmap_df["Rank"] = range(1, len(heatmap_df) + 1)

# Label formatting
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

# Pivot for display
pivot_hs = heatmap_df.pivot(index="Second LTV", columns="First LTV", values="Final Health Score")
pivot_labels = heatmap_df.pivot(index="Second LTV", columns="First LTV", values="Label")

fig, ax = plt.subplots(figsize=(6, 14))  # narrow width, taller layout
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

st.markdown("**Instructions:** First loop is fixed at 40%. Explore granular Loop 2 options with a minimum health score of 1.6.")
