import streamlit as st
import pandas as pd
import requests
from web3 import Web3

st.header("Step 4: LP Exit Planner")

# --- CONFIG ---
MORALIS_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
WALLET = "0xb4f25c81fb52d959616e3837cbc9e24a283b9df4"

# --- Web3 + Contract Setup ---
ARB_RPC = "https://arb1.arbitrum.io/rpc"
w3 = Web3(Web3.HTTPProvider(ARB_RPC))

NFT_MANAGER_ADDRESS = Web3.to_checksum_address("0xc36442b4a4522e871399cd717abdd847ab11fe88")
ABI_POSITIONS = [{
    "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
    "name": "positions",
    "outputs": [
        {"name": "nonce", "type": "uint96"},
        {"name": "operator", "type": "address"},
        {"name": "token0", "type": "address"},
        {"name": "token1", "type": "address"},
        {"name": "fee", "type": "uint24"},
        {"name": "tickLower", "type": "int24"},
        {"name": "tickUpper", "type": "int24"},
        {"name": "liquidity", "type": "uint128"},
        {"name": "feeGrowthInside0LastX128", "type": "uint256"},
        {"name": "feeGrowthInside1LastX128", "type": "uint256"},
        {"name": "tokensOwed0", "type": "uint128"},
        {"name": "tokensOwed1", "type": "uint128"}
    ],
    "stateMutability": "view",
    "type": "function"
}]

nft_manager = w3.eth.contract(address=NFT_MANAGER_ADDRESS, abi=ABI_POSITIONS)

def tick_to_price(tick, invert=False):
    price = 1.0001 ** tick
    return 1 / price if invert else price

def get_eth_balance(wallet, key):
    headers = {"X-API-Key": key}
    url = f"https://deep-index.moralis.io/api/v2.2/{wallet}/balance?chain=eth"
    r = requests.get(url, headers=headers)
    return int(r.json().get("balance", 0)) / 1e18 if r.status_code == 200 else None

# --- ETH Price ---
if "eth_price" not in st.session_state:
    try:
        coingecko = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        st.session_state.eth_price = coingecko.json()["ethereum"]["usd"]
    except:
        st.session_state.eth_price = 2578

current_price = st.session_state.eth_price

# --- UI Inputs ---
st.subheader("🔗 LP Live Data Integration (Optional)")
lp_url = st.text_input("Paste Uniswap LP Position URL", value="https://app.uniswap.org/positions/v3/arbitrum/4494432")
network = st.selectbox("Network", ["ethereum", "arbitrum"], index=1)
wallet_address = st.text_input("Wallet Address (optional for ETH tracking)", value=WALLET)

# --- Get ETH Balance ---
use_live_eth = False
eth_live = get_eth_balance(wallet_address, MORALIS_KEY)
if eth_live:
    st.success(f"Live ETH Balance: {eth_live:.4f} ETH")
    use_live_eth = st.checkbox("Use live ETH balance to auto-fill stack", value=False)

# --- LP Position Fetch ---
lp_low = 2300.0
lp_high = 2500.0
match = None

import re
match = re.search(r"positions/v3/\w+/(\d+)", lp_url)
if match:
    token_id = int(match.group(1))
    try:
        pos = nft_manager.functions.positions(token_id).call()
        token0 = pos[2]
        token1 = pos[3]
        fee = pos[4]
        tick_low = pos[5]
        tick_high = pos[6]

        invert_price = True  # ARB/WETH → show ARB per 1 WETH
        lp_low = round(tick_to_price(tick_low, invert=invert_price), 2)
        lp_high = round(tick_to_price(tick_high, invert=invert_price), 2)
        st.success(f"Loaded LP: token0 = {token0[-4:]}, token1 = {token1[-4:]}, fee = {fee}, range: {lp_low:,}—{lp_high:,}")
    except Exception as e:
        st.warning("LP position not found or failed to fetch.")
        st.json({"error": str(e)})

# --- Strategy Inputs ---
lp_low = st.number_input("Your LP Lower Bound ($)", value=lp_low)
lp_high = st.number_input("Your LP Upper Bound ($)", value=lp_high)
fees_earned_eth = st.number_input("Estimated Fees Earned (ETH)", value=0.10, step=0.01)
loop2_debt_usd = st.number_input("Loop 2 USDC Debt ($)", value=4000.0, step=50.0)
eth_stack = eth_live if use_live_eth else st.number_input("Current ETH Stack", value=8.75, step=0.01)

# --- Scenario ---
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

# --- Summary ---
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
