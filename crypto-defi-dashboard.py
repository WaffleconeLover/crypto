import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import requests

st.set_page_config(layout="wide")

# Initialize session state
def init_session_state():
    defaults = {
        "eth_stack": 6.73,
        "eth_price_input": 2600.0,
        "loop1_collateral": 6.73,
        "loop1_ltv_slider": 40,
        "eth_from_lp": 0.0,
        "loop1_health_score": 2.50,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

st.title("ETH Leverage Heatmap")

col1, col2 = st.columns([2, 3])
with col1:
    if st.button("Reset App (keep Loop 1)"):
        for key in ["eth_price_input", "eth_stack", "eth_from_lp"]:
            st.session_state[key] = 0.0

with col2:
    if st.button("Reset Loop 1 Inputs"):
        st.session_state.loop1_collateral = 6.73
        st.session_state.loop1_ltv_slider = 40
        st.session_state.eth_from_lp = 0.0

# Try to fetch ETH price
try:
    price_req = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
    price_req.raise_for_status()
    eth_price_live = price_req.json()['ethereum']['usd']
    st.session_state.eth_price_input = eth_price_live
    st.markdown(f"**Live ETH Price from CoinGecko: ${eth_price_live:,.2f}**")
except:
    st.warning("Unable to fetch live ETH price. Please enter it manually.")
    eth_price_live = st.number_input("Manual ETH Price Input ($)", min_value=100.0, max_value=10000.0, 
                                      value=float(st.session_state.eth_price_input), step=10.0)
    st.session_state.eth_price_input = eth_price_live

# ETH stack
st.session_state.eth_stack = st.slider("Current ETH Stack", 1.0, 50.0, float(st.session_state.eth_stack))

# --- Manual Loop 1 Setup --- #
with st.expander("Manual Loop 1 Setup", expanded=True):
    st.session_state.loop1_collateral = st.number_input("ETH Supplied as Collateral (Loop 1)", 
                                                        value=float(st.session_state.loop1_collateral), 
                                                        step=0.01)

    st.session_state.loop1_ltv_slider = st.slider("Target Loop 1 LTV (%)", 30, 60, 
                                                  int(st.session_state.loop1_ltv_slider))

    loop1_ltv = st.session_state.loop1_ltv_slider / 100
    loop1_debt = loop1_ltv * st.session_state.loop1_collateral * st.session_state.eth_price_input
    eth_after_loop1 = st.session_state.loop1_collateral + (loop1_debt / st.session_state.eth_price_input)
    loop1_health = (1 / loop1_ltv) * 0.75 if loop1_ltv != 0 else 100

    st.session_state.loop1_health_score = round(loop1_health, 2)

    st.markdown(f"**Debt After Loop 1 ($):** ${loop1_debt:,.2f}")
    st.markdown(f"**ETH Stack After Loop 1:** {eth_after_loop1:.2f}")
    st.markdown(f"**Loop 1 Health Score:** {loop1_health:.2f}")

# --- LP Exit Simulation --- #
with st.expander("LP Exit Simulation", expanded=True):
    st.session_state.eth_from_lp = st.number_input("ETH Gained from LP", 
                                                   value=float(st.session_state.eth_from_lp), step=0.01)
    updated_stack = round(float(st.session_state.eth_stack) + float(st.session_state.eth_from_lp), 2)
    st.markdown(f"**Updated ETH Stack after LP Exit: {updated_stack} ETH**")

# --- Loop 2 Heatmap --- #
eth_stack_loop2 = updated_stack
eth_price = float(st.session_state.eth_price_input)

# Construct grid for Loop 2
first_ltv = st.session_state.loop1_ltv_slider
second_ltv_range = list(range(30, 61))

data = []
for second_ltv in second_ltv_range:
    ltv_ratio = second_ltv / 100
    debt = ltv_ratio * eth_stack_loop2 * eth_price
    total_eth = eth_stack_loop2 + (debt / eth_price)
    health = (1 / ltv_ratio) * 0.75 if ltv_ratio != 0 else 100

    if health >= 1.6:
        label = f"{health:.2f}\n${debt:,.0f}\n{ltv_ratio*100:.1f}% @ ${debt / eth_stack_loop2:,.0f}\n{total_eth:.2f} ETH"
        data.append({
            "Second LTV": second_ltv,
            "First LTV": first_ltv,
            "Final Health Score": round(health, 2),
            "Label": label
        })

heatmap_df = pd.DataFrame(data)

if heatmap_df.empty:
    st.info("No results meet the criteria (Final Health Score ≥ 1.6). Adjust inputs or try again.")
else:
    try:
        pivot_hs = heatmap_df.pivot(index="Second LTV", columns="First LTV", values="Final Health Score")
        pivot_labels = heatmap_df.pivot(index="Second LTV", columns="First LTV", values="Label")

        fig, ax = plt.subplots(figsize=(6, 12))
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
        plt.xlabel("First LTV (%)")
        plt.ylabel("Second LTV (%)")
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Heatmap error: {e}")

st.markdown("""
**Instructions:** Loop 1 is now manually set. Explore granular Loop 2 options with a minimum health score of 1.6.
""")
