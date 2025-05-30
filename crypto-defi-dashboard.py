import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# --- Setup ---
st.set_page_config(layout="wide")
st.title("ETH Leverage Heatmap")

# Initialize session state
if "eth_price_input" not in st.session_state:
    st.session_state.eth_price_input = 2600.0
if "eth_stack" not in st.session_state:
    st.session_state.eth_stack = 6.73
if "loop1_collateral" not in st.session_state:
    st.session_state.loop1_collateral = st.session_state.eth_stack
if "loop1_ltv" not in st.session_state:
    st.session_state.loop1_ltv = 40

# --- Reset Buttons ---
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🔄 Reset App (keep Loop 1)"):
        st.experimental_rerun()
with col2:
    if st.button("❌ Reset Loop 1 Inputs"):
        st.session_state.loop1_collateral = st.session_state.eth_stack
        st.session_state.loop1_ltv = 40

# --- ETH Price Input ---
try:
    import requests
    eth_price_live = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd").json()["ethereum"]["usd"]
    st.session_state.eth_price_input = eth_price_live
    st.markdown(f"**Live ETH Price from CoinGecko:** ${eth_price_live:,.2f}")
except:
    st.warning("Unable to fetch live ETH price. Please enter it manually.")
    st.session_state.eth_price_input = st.number_input("Manual ETH Price Input ($)", min_value=100.0, max_value=10000.0, value=float(st.session_state.eth_price_input), step=10.0)

# --- ETH Stack Input ---
st.session_state.eth_stack = st.slider("Current ETH Stack", min_value=1.0, max_value=50.0, value=st.session_state.eth_stack, step=0.01)

# --- Loop 1 Inputs ---
st.subheader("Manual Loop 1 Setup")
with st.expander("Manual Loop 1 Setup", expanded=True):
    st.session_state.loop1_collateral = st.number_input("ETH Supplied as Collateral (Loop 1)", min_value=0.1, value=float(st.session_state.loop1_collateral), step=0.01)
    st.session_state.loop1_ltv = st.slider("Target Loop 1 LTV (%)", min_value=30, max_value=60, value=st.session_state.loop1_ltv, step=1)

    loop1_debt = st.session_state.loop1_collateral * (st.session_state.loop1_ltv / 100.0) * st.session_state.eth_price_input
    loop1_eth_stack = st.session_state.loop1_collateral + (loop1_debt / st.session_state.eth_price_input)
    loop1_health = (st.session_state.loop1_collateral * st.session_state.eth_price_input) / loop1_debt if loop1_debt > 0 else 10.0

    st.number_input("Debt After Loop 1 ($)", value=loop1_debt, step=10.0, disabled=True, key="auto_debt")
    st.number_input("ETH Stack After Loop 1", value=loop1_eth_stack, step=0.01, disabled=True, key="auto_stack")
    st.markdown(f"**Loop 1 Health Score:** {loop1_health:.2f}")

# --- LP Exit Simulation ---
st.subheader("LP Exit Simulation")
with st.expander("LP Exit Simulation", expanded=True):
    lp_gain = st.number_input("ETH Gained from LP", min_value=0.0, value=0.0, step=0.01)
    updated_stack = st.session_state.eth_stack + lp_gain
    st.markdown(f"**Updated ETH Stack after LP Exit: {updated_stack:.2f} ETH**")

# --- Heatmap Grid Calculation ---
min_health_score = 1.6
ltv1 = st.session_state.loop1_ltv
eth_stack_loop1 = loop1_eth_stack
debt_loop1 = loop1_debt

ltv2_range = np.arange(30, 51, 1)
rows = []
for ltv2 in ltv2_range:
    total_debt = debt_loop1 + (eth_stack_loop1 * (ltv2 / 100.0) * st.session_state.eth_price_input)
    total_collateral = eth_stack_loop1 * st.session_state.eth_price_input
    final_health = total_collateral / total_debt if total_debt > 0 else 10.0
    if final_health >= min_health_score:
        total_eth = eth_stack_loop1 + (ltv2 / 100.0 * eth_stack_loop1)
        usd_borrow = eth_stack_loop1 * ltv2 / 100.0 * st.session_state.eth_price_input
        label = f"{final_health:.2f}\n↓{ltv2:.0f}% @ ${usd_borrow:,.0f}\n{total_eth:.2f} ETH"
        rows.append({
            "Second LTV": ltv2,
            "Final Health Score": final_health,
            "Total ETH": total_eth,
            "Label": label
        })

heatmap_df = pd.DataFrame(rows)

st.markdown("---")

if not heatmap_df.empty:
    pivot_hs = heatmap_df.pivot(index="Second LTV", columns=None, values="Final Health Score")
    pivot_labels = heatmap_df.pivot(index="Second LTV", columns=None, values="Label")

    fig, ax = plt.subplots(figsize=(2, 10))
    sns.heatmap(
        pivot_hs,
        annot=pivot_labels,
        fmt="",
        cmap="RdYlGn",
        cbar_kws={'label': 'Final Health Score'},
        annot_kws={'fontsize': 8},
        ax=ax
    )
    ax.set_title("Loop 2 Leverage Grid")
    ax.set_xlabel("")
    ax.set_ylabel("Second Loop LTV (%)")
    st.pyplot(fig)
else:
    st.info("No results meet the criteria (Final Health Score ≥ 1.6). Adjust inputs or try again.")

st.markdown("**Instructions:** Loop 1 is now manually set. Explore granular Loop 2 options with a minimum health score of 1.6.")
