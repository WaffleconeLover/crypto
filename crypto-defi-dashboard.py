# ETH Leverage Dashboard — Updated with Stable Loop 2 Grid

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests

st.set_page_config(page_title="ETH Leverage Heatmap", layout="wide")

# ---------- State Initialization ----------
if "eth_price_input" not in st.session_state:
    st.session_state.eth_price_input = 2660.00
if "loop1_eth" not in st.session_state:
    st.session_state.loop1_eth = 10.4
if "loop1_debt" not in st.session_state:
    st.session_state.loop1_debt = 11200.0

# ---------- Utility ----------
def fetch_eth_price():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        return response.json()['ethereum']['usd']
    except:
        return None

# ---------- Controls ----------
st.title("ETH Leverage Heatmap")

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🔄 Reset App (keep Loop 1)"):
        st.experimental_rerun()
with col2:
    if st.button("❌ Reset Loop 1 Inputs"):
        st.session_state.loop1_eth = 10.4
        st.session_state.loop1_debt = 11200.0
        st.experimental_rerun()

eth_price_live = fetch_eth_price()
if eth_price_live:
    eth_price = eth_price_live
    st.markdown(f"**Live ETH Price from CoinGecko:** ${eth_price:,.2f}")
else:
    st.warning("Unable to fetch live ETH price. Please enter it manually.")
    eth_price = st.number_input("Manual ETH Price Input ($)", min_value=100.0, max_value=10000.0, value=float(st.session_state.eth_price_input), step=10.0)
    st.session_state.eth_price_input = eth_price

eth_stack = st.slider("Current ETH Stack", 1.0, 50.0, 6.73, step=0.01)

# ---------- Manual Loop 1 ----------
with st.expander("Manual Loop 1 Setup", expanded=True):
    loop1_eth = st.number_input("ETH Stack After Loop 1", value=st.session_state.loop1_eth, step=0.1)
    st.session_state.loop1_eth = loop1_eth
    loop1_debt = st.number_input("Debt After Loop 1 ($)", min_value=0.0, value=float(st.session_state.loop1_debt), step=10.0)
    st.session_state.loop1_debt = loop1_debt
    loop1_health = round(((loop1_eth * eth_price * 0.8) / loop1_debt), 2) if loop1_debt > 0 else 0.0
    st.markdown(f"**Loop 1 Health Score:** {loop1_health:.2f}")

# ---------- LP Exit ----------
with st.expander("LP Exit Simulation", expanded=True):
    eth_from_lp = st.number_input("ETH Gained from LP", min_value=0.0, step=0.01)
    updated_stack = eth_stack + eth_from_lp
    st.markdown(f"**Updated ETH Stack after LP Exit: {updated_stack:.2f} ETH**")

# ---------- Loop 2 Grid Generation ----------
second_loop_lvts = np.arange(30.0, 52.0, 1.0)
data = []

first_loop_eth = loop1_eth
first_loop_debt = loop1_debt
first_loop_collateral = first_loop_eth * eth_price

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
        "First LTV": 40.0,
        "Final Health Score": final_hs,
        "Loop 2 Debt": int(loop2_debt),
        "Liq Price": liq_price,
        "Liq Drop %": liq_drop_pct,
        "Total ETH": total_eth,
        "ETH Gain %": pct_gain
    })

heatmap_df = pd.DataFrame(data)
heatmap_df = heatmap_df[heatmap_df["Final Health Score"] >= 1.6].copy()

heatmap_df["Score"] = (
    heatmap_df["Final Health Score"] * 40 +
    heatmap_df["Liq Drop %"] * 0.4 +
    heatmap_df["ETH Gain %"] * 0.2 +
    heatmap_df["Loop 2 Debt"] * 0.015
)
heatmap_df = heatmap_df.sort_values("Score", ascending=False).copy()
heatmap_df["Rank"] = range(1, len(heatmap_df) + 1)

required_cols = ["Final Health Score", "Loop 2 Debt", "Liq Drop %", "Liq Price", "Total ETH", "ETH Gain %", "Rank"]
heatmap_df = heatmap_df.dropna(subset=required_cols)

def strip_zero(val):
    return f"{val:.2f}".rstrip("0").rstrip(".")

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
pivot_hs = heatmap_df.pivot(index="Second LTV", columns="First LTV", values="Final Health Score")
pivot_labels = heatmap_df.pivot(index="Second LTV", columns="First LTV", values="Label")

if not pivot_hs.empty:
    fig, ax = plt.subplots(figsize=(3, 14))
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
else:
    st.info("No results meet the criteria (Final Health Score ≥ 1.6). Adjust inputs or try again.")

st.markdown("**Instructions:** Loop 1 is now manually set. Explore granular Loop 2 options with a minimum health score of 1.6.")
