import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import requests

# ---- ETH price from CoinGecko or manual ----
def get_eth_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        return r.json()['ethereum']['usd']
    except:
        return None

# ---- Session state defaults ----
if "eth_price" not in st.session_state:
    st.session_state.eth_price = get_eth_price() or 2500.0
if "eth_collateral" not in st.session_state:
    st.session_state.eth_collateral = 6.73
if "loop1_ltv" not in st.session_state:
    st.session_state.loop1_ltv = 40.0

st.title("ETH Looping Dashboard")

# ---- Loop 1 Setup ----
st.header("Loop 1 Setup")

eth_price = st.number_input("ETH Price (live or manual)", value=st.session_state.eth_price, step=10.0)
st.session_state.eth_price = eth_price

eth_collateral = st.number_input("ETH Collateral", value=st.session_state.eth_collateral, step=0.1)
st.session_state.eth_collateral = eth_collateral

target_ltv = st.slider("Target LTV for Loop 1", min_value=30.0, max_value=60.0, value=st.session_state.loop1_ltv, step=0.5)
st.session_state.loop1_ltv = target_ltv

loop1_debt = (eth_collateral * eth_price) * (target_ltv / 100)
eth_stack = eth_collateral + (loop1_debt / eth_price)
loop1_health = (eth_collateral * eth_price * 0.825) / loop1_debt if loop1_debt else np.nan
eth_gained = eth_stack - eth_collateral

st.markdown(f"**Debt After Loop 1:** ${loop1_debt:,.2f}")
st.markdown(f"**ETH Gained After Loop 1:** {eth_gained:.2f}")
st.markdown(f"**ETH Stack After Loop 1:** {eth_stack:.2f}")
st.markdown(f"**Loop 1 Health Score:** {loop1_health:.2f}")

# ---- Loop 2 Simulation ----
st.header("Loop 2 Grid")

first_ltv = round(target_ltv, 1)
second_ltv_range = np.arange(30, 65, 1)

data = []

for second_ltv in second_ltv_range:
    loop2_debt = (eth_stack * eth_price) * (second_ltv / 100)
    total_debt = loop1_debt + loop2_debt
    total_eth = eth_stack + (loop2_debt / eth_price)
    health_score = (total_eth * eth_price * 0.825) / total_debt if total_debt else np.nan
    final_value = total_eth * eth_price

    if health_score >= 1.6:
        data.append({
            "First LTV": first_ltv,
            "Second LTV": second_ltv,
            "Total Debt": total_debt,
            "ETH": round(total_eth, 2),
            "Final Value": final_value,
            "Final Health Score": health_score,
            "% LTV": f"{second_ltv}%"
        })

heatmap_df = pd.DataFrame(data)

# ---- Label assignment ----
heatmap_df["Label"] = heatmap_df.apply(
    lambda row: f"{row['Final Health Score']:.2f}\n${row['Final Value']:,.0f}\n{row['% LTV']}\n{row['ETH']} ETH"
    if row["Final Health Score"] >= 1.6 else "", axis=1
)

# ---- Grid visualization ----
if not heatmap_df.empty:
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
else:
    st.warning("No Loop 2 options meet the minimum health score of 1.6. Adjust LTV or ETH collateral.")

# ---- Reset Button ----
if st.button("Reset Inputs"):
    st.session_state.clear()
    st.experimental_rerun()
