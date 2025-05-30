import streamlit as st
import pandas as pd
import requests
import re

st.header("Step 4: LP Exit Planner")

# ✅ FIXED: Official Uniswap subgraph for Arbitrum
SUBGRAPH_URLS = {
    "ethereum": "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3",
    "arbitrum": "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3-arbitrum"
}

def convert_to_hex_position_id(position_id):
    hex_str = hex(int(position_id))[2:].zfill(64)
    return f"0x{hex_str}"

def fetch_position_by_id(position_id_hex, network):
    url = SUBGRAPH_URLS.get(network)
    query = f"""
    {{
      position(id: "{position_id_hex}") {{
        id
        liquidity
        depositedToken0
        depositedToken1
        collectedFeesToken0
        collectedFeesToken1
        pool {{
          token0 {{ symbol decimals }}
          token1 {{ symbol decimals }}
          feeTier
        }}
        tickLower {{ tickIdx }}
        tickUpper {{ tickIdx }}
      }}
    }}
    """
    response = requests.post(url, json={"query": query})
    return response.json()

def tick_to_price(tick):
    return 1.0001 ** int(tick)

def get_eth_balance(wallet_address, moralis_api_key):
    headers = {"accept": "application/json", "X-API-Key": moralis_api_key}
    url = f"https://deep-index.moralis.io/api/v2.2/{wallet_address}/balance?chain=eth"
    r = requests.get(url, headers=headers)
    return int(r.json()["balance"]) / 1e18 if r.status_code == 200 else None

# Fetch ETH price once
if "eth_price" not in st.session_state:
    try:
        price_data = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd").json()
        st.session_state.eth_price = price_data["ethereum"]["usd"]
    except:
        st.session_state.eth_price = 2578

current_price = st.session_state.eth_price

# --- LP Data Inputs ---
st.subheader("🔗 LP Live Data Integration (Optional)")
lp_url = st.text_input("Paste Uniswap LP Position URL")
moralis_key = st.text_input("Paste your Moralis API Key", type="password")
wallet_address = st.text_input("Wallet Address (optional for ETH tracking)")
network = st.selectbox("Network", ["ethereum", "arbitrum"], index=1)

# --- ETH Balance Live Fill ---
use_live_eth = False
eth_live = None
if wallet_address and moralis_key:
    eth_live = get_eth_balance(wallet_address, moralis_key)
    if eth_live:
        st.success(f"Live ETH Balance: {eth_live:.4f} ETH")
        use_live_eth = st.checkbox("Use live ETH balance to auto-fill stack", value=False)

# --- LP Lookup via URL ---
lp_low = 2300.0
lp_high = 2500.0
match = re.search(r"uniswap.org/positions/v[34]/([^/]+)/([0-9]+)", lp_url)
if match:
    network_from_url = match.group(1).lower()
    position_id = match.group(2)
    position_id_hex = convert_to_hex_position_id(position_id)
    data = fetch_position_by_id(position_id_hex, network_from_url)
    pos = data.get("data", {}).get("position")
    if pos:
        token0 = pos["pool"]["token0"]["symbol"]
        token1 = pos["pool"]["token1"]["symbol"]
        tick_low = int(pos["tickLower"]["tickIdx"])
        tick_high = int(pos["tickUpper"]["tickIdx"])
        lp_low = round(tick_to_price(tick_low) * current_price, 2)
        lp_high = round(tick_to_price(tick_high) * current_price, 2)
        st.success(f"Loaded LP: {token0}/{token1} — Range: ${lp_low} to ${lp_high}")
    else:
        st.warning("LP position not found or failed to fetch.")

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

# --- Output Guidance ---
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
