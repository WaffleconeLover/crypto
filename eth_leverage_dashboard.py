import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Page config
st.set_page_config(page_title="ETH Leverage Strategy Dashboard", layout="wide")
st.markdown("<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True)

st.title("ETH Leverage Heatmap (Plotly Edition)")

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
    data.append({
        "Second LTV": s_ltv,
        "Final Health Score": final_hs,
        "Total ETH": total_eth,
        "Loop2 USDC": loop2_usdc,
        "Liquidation Price": liq_price,
        "Pct Gain": pct_gain
    })

df = pd.DataFrame(data)

# Plotly heatmap
fig = px.density_heatmap(
    df,
    x="Final Health Score",
    y="Second LTV",
    z="Total ETH",
    color_continuous_scale="RdYlGn",
    labels={"Total ETH": "ETH Total"},
    title="ETH Leverage Setups by Final Health Score and Second Loop LTV"
)

fig.update_layout(
    xaxis_title="Final Health Score",
    yaxis_title="Second LTV (%)",
    coloraxis_colorbar=dict(title="Total ETH"),
    autosize=True
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("**This version uses Plotly to ensure full compatibility with Streamlit and avoid matplotlib errors.**")
