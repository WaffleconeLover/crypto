import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

st.set_page_config(layout="wide")

st.title("ETH Leverage Heatmap")

# --- Defaults ---
def reset_loop1():
    st.session_state.loop1_collateral = eth_stack
    st.session_state.loop1_ltv = 40

def reset_loop1_inputs():
    st.session_state.loop1_collateral = eth_stack
    st.session_state.loop1_ltv = 40

def reset_app():
    st.session_state.eth_price_input = eth_price_live
    reset_loop1()

# --- Fetch ETH Price ---
eth_price_live = 2600.00

try:
    import requests
    coingecko = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
    eth_price_live = coingecko.json()["ethereum"]["usd"]
except:
    st.warning("Unable to fetch live ETH price. Please enter it manually.")

eth_price = st.number_input("Manual ETH Price Input ($)", min_value=100.0, max_value=10000.0, value=float(st.session_state.get("eth_price_input", eth_price_live)), step=10.0)
st.session_state.eth_price_input = eth_price

eth_stack = st.slider("Current ETH Stack", 1.0, 50.0, value=6.73, step=0.01)

# --- Manual Loop 1 Setup ---
st.subheader("Manual Loop 1 Setup")

with st.expander("Manual Loop 1 Setup", expanded=True):
    loop1_collateral = st.number_input("ETH Supplied as Collateral (Loop 1)", value=st.session_state.get("loop1_collateral", eth_stack), step=0.01)
    loop1_ltv = st.slider("Target Loop 1 LTV (%)", 30, 60, value=st.session_state.get("loop1_ltv", 40))

    loop1_debt = (loop1_collateral * eth_price) * (loop1_ltv / 100)
    eth_gained_loop1 = loop1_debt / eth_price
    eth_stack_after_loop1 = loop1_collateral + eth_gained_loop1
    loop1_health = (loop1_collateral * eth_price) / loop1_debt if loop1_debt != 0 else 0

    st.session_state.loop1_collateral = loop1_collateral
    st.session_state.loop1_ltv = loop1_ltv

    st.markdown(f"**Debt After Loop 1:** ${loop1_debt:,.2f}")
    st.markdown(f"**ETH Gained After Loop 1:** {eth_gained_loop1:,.2f}")
    st.markdown(f"**ETH Stack After Loop 1:** {eth_stack_after_loop1:,.2f}")
    st.markdown(f"**Loop 1 Health Score:** {loop1_health:.2f}")

# --- LP Exit Simulation ---
st.subheader("LP Exit Simulation")

with st.expander("LP Exit Simulation", expanded=True):
    eth_from_lp = st.number_input("ETH Gained from LP", min_value=0.0, value=0.0, step=0.01)
    updated_stack = eth_stack + eth_from_lp
    st.markdown(f"**Updated ETH Stack after LP Exit: {updated_stack:.2f} ETH**")

# --- Heatmap Calculation ---
first_ltv_range = np.arange(40, 50.5, 0.5)
second_ltv_range = np.arange(30, 46.5, 0.5)

records = []
for first in first_ltv_range:
    for second in second_ltv_range:
        total_debt = loop1_debt + ((eth_stack_after_loop1 * eth_price) * (second / 100))
        total_eth = eth_stack_after_loop1 + (eth_stack_after_loop1 * (second / 100))
        health_score = (eth_stack_after_loop1 * eth_price) / total_debt if total_debt else 0
        final_value = (eth_stack_after_loop1 * (1 + second / 100)) * eth_price
        eth_growth = total_eth - eth_stack
        records.append({
            "First LTV": round(first, 1),
            "Second LTV": round(second, 1),
            "Final Health Score": round(health_score, 2),
            "Final Value": final_value,
            "% LTV": f"{second:.1f}% @ ${final_value:,.0f}",
            "ETH": round(total_eth, 2)
        })

heatmap_df = pd.DataFrame(records)
filtered = heatmap_df[heatmap_df["Final Health Score"] >= 1.6]

if filtered.empty:
    st.info("No results meet the criteria (Final Health Score ≥ 1.6). Adjust inputs or try again.")
else:
    heatmap_df["Label"] = filtered.apply(
        lambda row: f"{row['Final Health Score']:.2f}\n${row['Final Value']:,.0f}\n{row['% LTV']}\n{row['ETH']} ETH", axis=1
    )
    pivot_hs = filtered.pivot(index="Second LTV", columns="First LTV", values="Final Health Score")
    pivot_labels = filtered.pivot(index="Second LTV", columns="First LTV", values="Label")

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
    plt.xlabel("First LTV")
    plt.ylabel("Second LTV")
    st.pyplot(fig)

st.markdown("**Instructions:** Loop 1 is now manually set. Explore granular Loop 2 options with a minimum health score of 1.6.")
