import streamlit as st
import pandas as pd
import requests
import re
import math

st.header("Step 4: LP Exit Planner")

# --- Constants ---
WALLET_ADDRESS = "0xb4f25c81fb52d959616e3837cbc9e24a283b9df4"
GRAPH_KEY = "d997b56020107b5449f63d478635f9c6"
MORALIS_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjgyMDNmNDlmLTMzOWMtNDc5YS04Y2U4LTM0YzI5M2IzODU3YyIsIm9yZ0lkIjoiNDMwOTg5IiwidXNlcklkIjoiNDQzMzM1IiwidHlwZUlkIjoiMmVlOTUxYjAtOTk4ZC00NjRmLWFmZTEtM2FlZDVlNjhhMzE3IiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3MzkzNzI3NTUsImV4cCI6NDg5NTEzMjc1NX0.8GWca9PdAXaJ5ReNTdCKnMQkQ3GdEGPOj67yTw19krM"

# --- Helper Functions ---
def tick_to_price(tick, base_is_token0):
    price = 1.0001 ** int(tick)
    return 1 / price if not base_is_token0 else price

def get_eth_balance(wallet_address, moralis_api_key):
    headers = {"accept": "application/json", "X-API-Key": moralis_api_key}
    url = f"https://deep-index.moralis.io/api/v2.2/{wallet_address}/balance?chain=eth"
    r = requests.get(url, headers=headers)
    return int(r.json()["balance"]) / 1e18 if r.status_code == 200 else None

def get_lp_from_moralis(token_id, chain, moralis_api_key):
    headers = {
        "accept": "application/json",
        "X-API-Key": moralis_api_key
    }
    url = f"https://deep-index.moralis.io/api/v2.2/nft/0xc36442b4a4522e871399cd717abdd847ab11fe88/{token_id}?chain={chain}&format=decimal"
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {e}", "status_code": r.status_code}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {e}"}
    except ValueError:
        return {"error": "Invalid JSON response", "raw_text": r.text}

# --- ETH Price ---
if "eth_price" not in st.session_state:
    try:
        price_data = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd").json()
        st.session_state.eth_price = price_data["ethereum"]["usd"]
    except:
        st.session_state.eth_price = 2578

current_price = st.session_state.eth_price

# --- UI ---
st.subheader("🔗 LP Live Data Integration (Optional)")
lp_url = st.text_input("Paste Uniswap LP Position URL", value="https://app.uniswap.org/positions/v3/arbitrum/4494432")
manual_network = st.selectbox("Network", ["ethereum", "arbitrum"], index=1)

wallet_address = st.text_input("Wallet Address (optional for ETH tracking)", value=WALLET_ADDRESS)
eth_live = get_eth_balance(wallet_address, MORALIS_KEY)
use_live_eth = False
if eth_live:
    st.success(f"Live ETH Balance: {eth_live:.4f} ETH")
    use_live_eth = st.checkbox("Use live ETH balance to auto-fill stack", value=False)

# --- LP Price Range ---
lp_low = 2300.0
lp_high = 2500.0
match = re.search(r"uniswap.org/positions/v3/([^/]+)/(\d+)", lp_url)
if match:
    network_from_url = match.group(1).lower()
    token_id = match.group(2)
    selected_network = network_from_url if network_from_url in ["ethereum", "arbitrum"] else manual_network

    response = get_lp_from_moralis(token_id, selected_network, MORALIS_KEY)
    attributes = response.get("attributes")
    if attributes:
        tick_lower = int(attributes["tickLower"])
        tick_upper = int(attributes["tickUpper"])
        token0 = attributes["token0"]
        token1 = attributes["token1"]
        base_token = "ARB" if selected_network == "arbitrum" else "ETH"
        base_is_token0 = token0.startswith(base_token)
        lp_low = round(tick_to_price(tick_lower, base_is_token0) * current_price, 2)
        lp_high = round(tick_to_price(tick_upper, base_is_token0) * current_price, 2)
        st.success(f"Loaded LP: {token0}/{token1} — Range: ${lp_low} to ${lp_high}")
    else:
        st.warning("LP position not found or failed to fetch.")
        st.json(response)

# --- Inputs ---
lp_low = st.number_input("Your LP Lower Bound ($)", value=lp_low)
lp_high = st.number_input("Your LP Upper Bound ($)", value=lp_high)
fees_earned_eth = st.number_input("Estimated Fees Earned (ETH)", value=0.10, step=0.01)
loop2_debt_usd = st.number_input("Loop 2 USDC Debt ($)", value=4000.0, step=50.0)
eth_stack = eth_live if use_live_eth and eth_live else st.number_input("Current ETH Stack", value=8.75, step=0.01)

# --- Price Simulation ---
st.subheader("Price Scenario Simulation")
eth_scenario_price = st.slider("Simulate ETH Price ($)", 1000, 5000, int(current_price), step=50)
collateral_usd = eth_stack * eth_scenario_price
repayable_eth = loop2_debt_usd / eth_scenario_price
net_eth = fees_earned_eth - repayable_eth

# --- Range Check ---
if current_price > lp_high:
    status = "above"
elif current_price < lp_low:
    status = "below"
else:
    status = "in"

# --- Guidance ---
st.subheader("Guidance")
if status == "in":
    st.success("✅ Your LP is currently in range. Let it continue accumulating fees.")
elif status == "above":
    st.markdown(f"Price is **{(current_price - lp_high)/lp_high:.1%} above** your LP range.")
    st.markdown(f"You've earned **{fees_earned_eth:.2f} ETH** in fees.")
    st.markdown(f"Loop 2 debt = **${loop2_debt_usd:,.2f}** = **{repayable_eth:.2f} ETH** at **${eth_scenario_price}**.")
    st.warning(f"⚠️ You are short **{abs(net_eth):.2f} ETH** to repay Loop 2.")
elif status == "below":
    needed = loop2_debt_usd / eth_scenario_price
    if needed <= eth_stack:
        st.success(f"You can repay Loop 2 with **{needed:.2f} ETH**, keeping **{eth_stack - needed:.2f} ETH**.")
    else:
        recovery_price = loop2_debt_usd / eth_stack
        st.error(f"You need ETH to reach **${recovery_price:,.2f}** to repay Loop 2.")

# --- Summary Table ---
st.subheader("P&L Summary")
st.dataframe(pd.DataFrame({
    "Scenario Price ($)": [eth_scenario_price],
    "ETH Stack": [eth_stack],
    "Collateral Value ($)": [collateral_usd],
    "Loop 2 Debt ($)": [loop2_debt_usd],
    "Debt in ETH": [repayable_eth],
    "Fees Earned (ETH)": [fees_earned_eth],
    "Net ETH After Repay": [net_eth]
}))
