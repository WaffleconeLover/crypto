import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# --- Setup ---
st.set_page_config(layout="wide")
st.title("ETH Leverage Heatmap")

# --- Initialize session state ---
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
    st.session_state.eth_price_input = st.number_input(
        "Manual ETH Price Input ($)", 
        min_value=100.0, 
        max_value=10000.0, 
        value=float(st.session_state.eth_price_input), 
        step=10.0
    )

# --- ETH Stack Input ---
st.session_state.eth_stack = st.slider("Current ETH Stack", min_value=1.0, max_value=50.0, value=st.session_state.eth_stack, step=0.01)

# --- Loop 1 Setup ---
st.subheader("Manual Loop 1 Setup")
with st.expander("Manual Loop 1 Setup", expanded=True):
    st.session_state.loop1_collateral = st.number_input(
        "ETH Supplied as Collateral (Loop 1)", 
        min_value=0.1, 
        value=float(st.session_state.loop1_collateral), 
        step=0.01
    )
    st.session_state.loop1_ltv = st.slider("Target Loop 1 LTV (%)", min_value=30, max_value=60, value=st.session_state.loop1_ltv, step=1)

    loop1_debt = st.session_state.loop1_collateral * (st.session_state.loop1_ltv / 100.0) * st.session_state.eth_price_input
    loop1_eth_stack = st.session_state.loop1_collateral + (loop1_debt / st.session_state.eth_price_input)
    loop1_health = (st.session_state.loop1_collateral * st.session_state.eth_price_input) / loop1_debt if loop1_debt > 0 else 10.0

    st.number_input("Debt After Loop 1 ($)", value=loop1_debt, step=10.0, disabled=True, key="auto
