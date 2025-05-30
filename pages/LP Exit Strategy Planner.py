import streamlit as st
import pandas as pd
import requests
import re

st.header("Step 4: LP Exit Planner")

# --- Constants (pre-filled for convenience) ---
wallet_address = "0xb4f25c81fb52d959616e3837cbc9e24a283b9df4"
moralis_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjgyMDNmNDlmLTMzOWMtNDc5YS04Y2U4LTM0YzI5M2IzODU3YyIsIm9yZ0lkIjoiNDMwOTg5IiwidXNlcklkIjoiNDQzMzM1IiwidHlwZUlkIjoiMmVlOTUxYjAtOTk4ZC00NjRmLWFmZTEtM2FlZDVlNjhhMzE3IiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3MzkzNzI3NTUsImV4cCI6NDg5NTEzMjc1NX0.8GWca9PdAXaJ5ReNTdCKnMQkQ3GdEGPOj67yTw19krM"

# --- Price logic ---
def tick_to_price_precise(tick, decimals_token0=18, decimals_token1=18, invert_price=True):
    sqrt_price = 1.0001 ** (tick / 2)
    price = (sqrt_price ** 2) * (10 ** (decimals_token0 - decimals_token1))
    return 1 / price if invert_price else price

# --- Moralis fetch ---
def get_lp_from_moralis(token_id):
    headers = {
        "accept": "application/json",
        "X-API-Key": moralis_key
    }
    url = f"https://deep-index.moralis.io/api/v2.2/nft/0xc36442b4a4522e871399cd717abdd847ab11fe88/{token_id}?chain=arbitrum"
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else None

# --- ETH Price ---
if "eth_price" not in st.session_state:
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        st.session_state.eth_price = r.json()["ethereum"]["usd"]
    except:
        st.session_state.eth_price = 2578

current_price = st.session_state.eth_price

# --- UI ---
st.subheader("🔗 LP Live Data Integration (Optional)")
lp_url = st.text_input("Paste Uniswap LP Position URL", "https://app.uniswap.org/positions/v3/arbitrum/4494432")
manual_network = st.selectbox("Network", ["arbitrum", "ethereum"], index=0)
st.text_input("Wallet Address (optional for ETH tracking)", value=wallet_address, disabled=True)

# --- ETH balance ---
use_live_eth = False
eth_live = None
if wallet_address and moralis_key:
    try:
        r = requests.get(f"https://deep-index.moralis.io/api/v2.2/{wallet_address}/balance?chain=eth", headers={
            "X-API-Key": moralis_key,
            "accept": "application/json"
        })
        eth_live = int(r.json()["balance"]) / 1e18
        st.success(f"Live ETH Balance: {eth_live:.4f} ETH")
        use_live_eth = st.checkbox("Use live ETH balance to auto-fill stack", value=False)
    except:
        pass

# --- Parse URL ---
lp_low = 2300.0
lp_high = 2500.0
match = re.search(r"uniswap.org/positions/v3/(?:arbitrum|ethereum)/([0-9]+)", lp_url)
if match:
    token_id = match.group(1)
    lp = get_lp_from_moralis(token_id)
    if lp and "normalized_metadata" in lp:
        try:
            tick_lower = int(lp["2"]["tickLower"] if "tickLower" not in lp else lp["tickLower"])
            tick_upper = int(lp["2"]["tickUpper"] if "tickUpper" not in lp else lp["tickUpper"])
        except:
            tick_lower = int(lp["normalized_metadata"]["description"].split("tickLower=")[1].split(",")[0])
            tick_upper = int(lp["normalized_metadata"]["description"].split("tickUpper=")[1].split(",")[0])
        lp_low = round(tick_to_price_precise(tick_lower), 2)
        lp_high = round(tick_to_price_precise(tick_upper), 2)
        st.success(f"Loaded LP: token0 = {lp.get('name', 'n/a')}, fee = 500, range: {lp_low}—{lp_high}")
    else:
        st.warning("LP position not found or failed to fetch.")
        st.json(lp)

# --- Inputs ---
lp_low = st.number_input("Your LP Lower Bound ($)", value=lp_low)
lp_high = st.number_input("Your LP Upper Bound ($)", value=lp_high)
fees_earned_eth = st.number_input("Estimated Fees Earned (ETH)", value=0.10, step=0.01)
loop2_debt_usd = st.number_input("Loop 2 USDC Debt ($)", value=4000.0, step=50.0)
eth_stack = eth_live if use_live_eth and eth_live else st.number_input("Current ETH Stack", value=8.75, step=0.01)

# --- Sim ---
st.subheader("Price Scenario Simulation")
eth_scenario_price = st.slider("Simulate ETH Price ($)", 1000, 5000, int(current_price), step=50)
collateral_usd = eth_stack * eth_scenario_price
repayable_eth = loop2_debt_usd / eth_scenario_price
net_eth = fees_earned_eth - repayable_eth

# --- Range logic ---
status = "in"
try:
    if current_price > lp_high:
        status = "above"
    elif current_price < lp_low:
        status = "below"
except ZeroDivisionError:
    status = "invalid"

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
else:
    st.error("Could not determine LP range status due to invalid bounds.")

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
