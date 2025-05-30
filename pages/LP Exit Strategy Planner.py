# LP Exit Planner - Supports Direct Uniswap LP URL Lookup
import streamlit as st
import pandas as pd
import requests
import re

st.header("Step 4: LP Exit Planner")

# --- Subgraph Mapping ---
SUBGRAPH_URLS = {
    "ethereum": "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3",
    "arbitrum": "https://api.thegraph.com/subgraphs/name/ianlapham/uniswap-arbitrum-one"
}

# --- LP Fetch by Position ID ---
def fetch_uniswap_v3_position_by_id(position_id, network):
    url = SUBGRAPH_URLS.get(network)
    if not url:
        return {}

    query = """
    {
      position(id: \"%s\") {
        id
        liquidity
        depositedToken0
        depositedToken1
        collectedFeesToken0
        collectedFeesToken1
        pool {
          token0 { symbol decimals }
          token1 { symbol decimals }
          feeTier
        }
        tickLower { tickIdx }
        tickUpper { tickIdx }
      }
    }
    """ % position_id

    response = requests.post(url, json={"query": query})
    return response.json()

# --- Moralis ETH Balance Fetch ---
def get_eth_balance(wallet_address, moralis_api_key):
    headers = {
        "accept": "application/json",
        "X-API-Key": moralis_api_key
    }
    url = f"https://deep-index.moralis.io/api/v2.2/{wallet_address}/balance?chain=eth"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        balance_wei = int(response.json()["balance"])
        return balance_wei / 1e18
    else:
        return None

# --- ETH Price Fallback ---
def fetch_eth_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        return r.json()["ethereum"]["usd"]
    except:
        return 2578.00

if "eth_price" not in st.session_state:
    st.session_state.eth_price = fetch_eth_price()

current_price = st.session_state.eth_price

# --- Inputs ---
lp_low = st.number_input("Your LP Lower Bound ($)", value=2300.0)
lp_high = st.number_input("Your LP Upper Bound ($)", value=2500.0)
fees_earned_eth = st.number_input("Estimated Fees Earned (ETH)", value=0.10, step=0.01)
loop2_debt_usd = st.number_input("Loop 2 USDC Debt ($)", value=4000.00, step=50.00)

# --- LP Data Integration Scaffold ---
st.subheader("🔗 LP Live Data Integration (Optional)")
lp_url = st.text_input("Paste Uniswap LP Position URL")
moralis_key = st.text_input("Paste your Moralis API Key", type="password")

network = None
position_id = None
match = re.search(r"uniswap.org/positions/v3/([^/]+)/([0-9]+)", lp_url)
if match:
    network = match.group(1).lower()
    position_id = match.group(2)

# --- ETH Live Balance ---
use_live_eth = False
eth_live = None
wallet_address = st.text_input("(Optional) Wallet Address for ETH Stack")
if wallet_address and moralis_key:
    eth_live = get_eth_balance(wallet_address, moralis_key)
    if eth_live is not None:
        st.success(f"Live ETH Balance: {eth_live:.4f} ETH")
        use_live_eth = st.checkbox("Use live ETH balance to auto-fill stack", value=False)
    else:
        st.error("Failed to fetch ETH balance from Moralis.")

# --- ETH Stack Input ---
if use_live_eth and eth_live is not None:
    eth_stack = eth_live
else:
    eth_stack = st.number_input("Current ETH Stack", value=8.75, step=0.01)

# --- Display LP Info ---
if position_id and network:
    lp_data = fetch_uniswap_v3_position_by_id(position_id, network)
    if "data" in lp_data and "position" in lp_data["data"] and lp_data["data"]["position"]:
        pos = lp_data["data"]["position"]
        pool = pos["pool"]
        st.subheader(f"📊 LP Position: {pool['token0']['symbol']} / {pool['token1']['symbol']} on {network.capitalize()}")
        st.markdown(f"- Liquidity: {pos['liquidity']}")
        st.markdown(f"- Fee Tier: {int(pool['feeTier']) / 10000:.2%}")
        st.markdown(f"- Tick Range: {pos['tickLower']['tickIdx']} to {pos['tickUpper']['tickIdx']}")
    else:
        st.warning("LP position not found or failed to fetch.")

# --- Scenarios ---
st.subheader("Price Scenario Simulation")
eth_scenario_price = st.slider("Simulate ETH Price ($)", min_value=1000, max_value=5000, value=int(current_price), step=50)
collateral_usd = eth_stack * eth_scenario_price
repayable_eth = loop2_debt_usd / eth_scenario_price
net_eth = fees_earned_eth - repayable_eth

# --- LP Range Check ---
if current_price > lp_high:
    out_of_range = "above"
elif current_price < lp_low:
    out_of_range = "below"
else:
    out_of_range = "in"

# --- Outputs ---
st.subheader("Guidance")

if out_of_range == "in":
    st.success("✅ Your LP is currently in range. Let it continue accumulating fees.")

elif out_of_range == "above":
    st.markdown(f"Price is **{(current_price - lp_high) / lp_high:.1%} above** your LP range.")
    st.markdown(f"You've earned **{fees_earned_eth:.2f} ETH** in fees.")
    st.markdown(f"Loop 2 debt is **${loop2_debt_usd:,.2f}**, or **{repayable_eth:.2f} ETH** at scenario price **${eth_scenario_price:,.2f}**.")
    if net_eth > 0:
        st.success(f"✅ You can fully repay Loop 2 with fees and retain **{net_eth:.2f} ETH**.")
    else:
        st.warning(f"⚠️ You are short **{abs(net_eth):.2f} ETH** to repay Loop 2. Consider partial repay or wait for more fees.")

elif out_of_range == "below":
    eth_needed = loop2_debt_usd / eth_scenario_price
    if eth_needed <= eth_stack:
        st.warning(f"🟡 Your LP is fully in ETH. You can repay Loop 2 with **{eth_needed:.2f} ETH**, leaving **{eth_stack - eth_needed:.2f} ETH**.")
    else:
        recovery_price = loop2_debt_usd / eth_stack
        st.error(f"🔴 Your ETH is worth **${collateral_usd:,.2f}**, but Loop 2 debt is **${loop2_debt_usd:,.2f}**.")
        st.markdown(f"You need ETH to rise to **${recovery_price:,.2f}** to repay Loop 2.")

# --- Summary Table ---
st.subheader("P&L Summary")
data = {
    "Scenario Price ($)": [eth_scenario_price],
    "ETH Stack": [eth_stack],
    "Collateral Value ($)": [collateral_usd],
    "Loop 2 Debt ($)": [loop2_debt_usd],
    "Debt in ETH": [repayable_eth],
    "Fees Earned (ETH)": [fees_earned_eth],
    "Net ETH After Repay": [net_eth]
}
st.dataframe(pd.DataFrame(data))
