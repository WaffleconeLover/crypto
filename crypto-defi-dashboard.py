import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import requests

st.set_page_config(page_title="ETH Leverage Heatmap", layout="wide")

# --- Initialize session state ---
def init_session_state():
    defaults = {
        "eth_price_input": 2600.0,
        "eth_stack": 6.73,
        "lp_eth_gain": 0.0,
        "eth_supplied_loop1": 6.73,
        "loop1_ltv_slider": 0.4,
        "loop1_debt": 11200.0,
        "loop1_eth": 10.4,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# --- Live ETH Price from CoinGecko ---
def fetch_eth_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        r.raise_for_status()
        return r.json()["ethereum"]["usd"]
    except Exception:
        return None

eth_price_live = fetch_eth_price()
if eth_price_live:
    st.session_state.eth_price_input = eth_price_live
    st.markdown(f"**Live ETH Price from CoinGecko:** ${eth_price_live:,.2f}")
else:
    st.warning("Unable to fetch live ETH price. Please enter it manually.")
    st.session_state.eth_price_input = st.number_input("Manual ETH Price Input ($)", min_value=100.0, max_value=10000.0, value=st.session_state.eth_price_input, step=10.0)

eth_price = st.session_state.eth_price_input

# --- Current ETH Stack Slider ---
st.session_state.eth_stack = st.slider("Current ETH Stack", 1.0, 50.0, st.session_state.eth_stack)

# --- Loop 1 Setup: Collateral + Target LTV Calculator ---
st.markdown("### Manual Loop 1 Setup")
with st.expander("Manual Loop 1 Setup", expanded=False):
    st.session_state.eth_supplied_loop1 = st.number_input("ETH Supplied as Collateral (Loop 1)", min_value=0.0, value=st.session_state.eth_supplied_loop1, step=0.1)
    st.session_state.loop1_ltv_slider = st.slider("Target Loop 1 LTV (%)", 30, 60, int(st.session_state.loop1_ltv_slider * 100)) / 100

    # Auto-calculated values
    st.session_state.loop1_debt = st.session_state.eth_supplied_loop1 * eth_price * st.session_state.loop1_ltv_slider
    st.session_state.loop1_eth = st.session_state.eth_supplied_loop1 + (st.session_state.loop1_debt / eth_price)

    st.number_input("Debt After Loop 1 ($)", value=round(st.session_state.loop1_debt, 2), disabled=True)
    st.number_input("ETH Stack After Loop 1", value=round(st.session_state.loop1_eth, 2), disabled=True)

# --- Health Score after Loop 1 ---
loop1_health_score = (st.session_state.eth_supplied_loop1 * eth_price) / st.session_state.loop1_debt if st.session_state.loop1_debt else 10.0
st.markdown(f"**Loop 1 Health Score:** {loop1_health_score:.2f}")

# --- LP Exit Simulator ---
st.markdown("### LP Exit Simulation")
with st.expander("LP Exit Simulation", expanded=False):
    st.session_state.lp_eth_gain = st.number_input("ETH Gained from LP", min_value=0.0, value=st.session_state.lp_eth_gain, step=0.01)
    updated_eth_stack = st.session_state.eth_stack + st.session_state.lp_eth_gain
    st.markdown(f"**Updated ETH Stack after LP Exit: {updated_eth_stack:.2f} ETH**")

# --- Loop 2 Grid Calculations ---
loop2_range = np.arange(30.0, 50.1, 1.0)  # Second loop LTV from 30% to 50% by 1%
loop1_ltv_fixed = round(st.session_state.loop1_ltv_slider * 100, 1)

records = []
for ltv2 in loop2_range:
    debt2 = st.session_state.loop1_eth * eth_price * (ltv2 / 100)
    eth_added = debt2 / eth_price
    total_eth = st.session_state.loop1_eth + eth_added
    total_debt = st.session_state.loop1_debt + debt2
    health_score = (total_eth * eth_price) / total_debt if total_debt else 10.0
    if health_score >= 1.6:
        records.append({
            "Second LTV": ltv2,
            "Total ETH": total_eth,
            "Debt": debt2,
            "Final Health Score": health_score
        })

heatmap_df = pd.DataFrame(records)

if heatmap_df.empty:
    st.info("No results meet the criteria (Final Health Score ≥ 1.6). Adjust inputs or try again.")
else:
    pivot_hs = heatmap_df.pivot(index="Second LTV", columns=None, values="Final Health Score")
    pivot_labels = heatmap_df.pivot(index="Second LTV", columns=None, values="Total ETH")

    fig, ax = plt.subplots(figsize=(5, 10))
    sns.heatmap(
        pivot_hs,
        annot=pivot_labels,
        fmt=".2f",
        cmap="RdYlGn",
        cbar_kws={'label': 'Final Health Score'},
        annot_kws={'fontsize': 7},
        ax=ax
    )
    plt.title("Top ETH Leverage Setups with Exposure, Liquidation Risk, and Yield")
    plt.xlabel("Loop 1 Fixed LTV")
    plt.ylabel("Second Loop LTV (%)")
    st.pyplot(fig)

st.markdown("**Instructions:** Loop 1 is now manually set. Explore granular Loop 2 options with a minimum health score of 1.6.")
