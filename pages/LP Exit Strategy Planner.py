import streamlit as st
import pandas as pd
import requests
import re
from web3 import Web3

# --- Constants ---
WALLET_ADDRESS = "0xb4f25c81fb52d959616e3837cbc9e24a283b9df4"
MORALIS_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjgyMDNmNDlmLTMzOWMtNDc5YS04Y2U4LTM0YzI5M2IzODU3YyIsIm9yZ0lkIjoiNDMwOTg5IiwidXNlcklkIjoiNDQzMzM1IiwidHlwZUlkIjoiMmVlOTUxYjAtOTk4ZC00NjRmLWFmZTEtM2FlZDVlNjhhMzE3IiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3MzkzNzI3NTUsImV4cCI6NDg5NTEzMjc1NX0.8GWca9PdAXaJ5ReNTdCKnMQkQ3GdEGPOj67yTw19krM"
ARBITRUM_RPC = "https://arb1.arbitrum.io/rpc"
UNIV3_NFT_ADDRESS = "0xc36442b4a4522e871399cd717abdd847ab11fe88"
UNIV3_ABI_POSITIONS = [{
    "constant": True,
    "inputs": [{"name": "tokenId", "type": "uint256"}],
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
    "payable": False,
    "stateMutability": "view",
    "type": "function"
}]

# --- Init Web3 ---
web3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC))
nft_contract = web3.eth.contract(address=Web3.to_checksum_address(UNIV3_NFT_ADDRESS), abi=UNIV3_ABI_POSITIONS)

# --- Helpers ---
def tick_to_price(tick):
    return 1.0001 ** tick

def get_eth_balance(wallet_address):
    headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}
    url = f"https://deep-index.moralis.io/api/v2.2/{wallet_address}/balance?chain=eth"
    r = requests.get(url, headers=headers)
    return int(r.json()["balance"]) / 1e18 if r.status_code == 200 else None

def extract_position_id(url):
    match = re.search(r"/positions/v[34]/[^/]+/(\d+)", url)
    return int(match.group(1)) if match else None

def fetch_uniswap_position(token_id):
    try:
        return nft_contract.functions.positions(token_id).call()
    except Exception as e:
        return {"error": str(e)}

# --- ETH Price ---
if "eth_price" not in st.session_state:
    try:
        price_data = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd").json()
        st.session_state.eth_price = price_data["ethereum"]["usd"]
    except:
        st.session_state.eth_price = 2578

eth_price = st.session_state.eth_price

# --- UI ---
st.header("Step 4: LP Exit Planner")
st.subheader("🔗 LP Live Data Integration (Optional)")

lp_url = st.text_input("Paste Uniswap LP Position URL", value="https://app.uniswap.org/positions/v3/arbitrum/4494432")
network = st.selectbox("Network", ["arbitrum"], index=0)
wallet_address = st.text_input("Wallet Address (optional for ETH tracking)", value=WALLET_ADDRESS)

eth_live = get_eth_balance(wallet_address)
if eth_live is not None:
    st.success(f"Live ETH Balance: {eth_live:.4f} ETH")
    use_live = st.checkbox("Use live ETH balance to auto-fill stack", value=False)
else:
    use_live = False

# --- LP Data Fetch ---
token_id = extract_position_id(lp_url)
lp_low, lp_high = 2300.0, 2500.0
fetched = False

if token_id:
    result = fetch_uniswap_position(token_id)
    if isinstance(result, dict) and "error" in result:
        st.warning("LP position not found or failed to fetch.")
        st.json(result)
    else:
        tick_low = result[5]
        tick_high = result[6]
        lp_low = round(tick_to_price(tick_low) * eth_price, 2)
        lp_high = round(tick_to_price(tick_high) * eth_price, 2)
        token0 = result[2]
        token1 = result[3]
        fee = result[4]
        st.success(f"Loaded LP: token0 = {token0[-4:]}, token1 = {token1[-4:]}, fee = {fee}, range: ${lp_low} - ${lp_high}")
        fetched = True

# --- Inputs ---
lp_low = st.number_input("Your LP Lower Bound ($)", value=lp_low)
lp_high = st.number_input("Your LP Upper Bound ($)", value=lp_high)
fees_earned_eth = st.number_input("Estimated Fees Earned (ETH)", value=0.10, step=0.01)
loop2_debt_usd = st.number_input("Loop 2 USDC Debt ($)", value=4000.0, step=50.0)
eth_stack = eth_live if use_live and eth_live is not None else st.number_input("Current ETH Stack", value=8.75, step=0.01)

# --- Simulation ---
st.subheader("Price Scenario Simulation")
eth_scenario_price = st.slider("Simulate ETH Price ($)", 1000, 5000, int(eth_price), step=50)
collateral_usd = eth_stack * eth_scenario_price
repayable_eth = loop2_debt_usd / eth_scenario_price
net_eth = fees_earned_eth - repayable_eth

# --- Range Check ---
if eth_price > lp_high:
    status = "above"
elif eth_price < lp_low:
    status = "below"
else:
    status = "in"

# --- Guidance ---
st.subheader("Guidance")
if status == "in":
    st.success("✅ Your LP is currently in range. Let it continue accumulating fees.")
elif status == "above":
    st.markdown(f"Price is **{(eth_price - lp_high)/lp_high:.1%} above** your LP range.")
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
