# LP Exit Planner - Phase 1 Expansion + LP Integration Scaffold
import streamlit as st
import pandas as pd
import requests

st.header("Step 4: LP Exit Planner")

# --- LP Fetch Function ---
def fetch_uniswap_v3_positions(wallet):
    url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
    query = """
    {
      positions(where: { owner: \"%s\" }) {
        id
        liquidity
        depositedToken0
        depositedToken1
        pool {
          token0 { symbol decimals }
          token1 { symbol decimals }
          feeTier
        }
        tickLower { tickIdx }
        tickUpper { tickIdx }
      }
    }
    """ % wallet.lower()

    response = requests.post(url, json={"query": query})
    return response.json()

# --- Inputs ---
lp_low = st.number_input("Your LP Lower Bound ($)", value=2300.0)
lp_high = st.number_input("Your LP Upper Bound ($)", value=2500.0)
current_price = st.session_state.eth_price

fees_earned_eth = st.number_input("Estimated Fees Earned (ETH)", value=0.10, step=0.01)
loop2_debt_usd = st.number_input("Loop 2 USDC Debt ($)", value=4000.00, step=50.00)
eth_stack = st.number_input("Current ETH Stack", value=8.75, step=0.01)

# --- LP Data Integration Scaffold ---
st.subheader("🔗 LP Live Data Integration (Optional)")
wallet_address = st.text_input("Enter Wallet Address for LP Tracking")
platform = st.selectbox("Select LP Platform", ["Uniswap V3", "Metrix", "Other"], index=0)

if wallet_address and platform == "Uniswap V3":
    lp_data = fetch_uniswap_v3_positions(wallet_address)

    if "data" in lp_data and "positions" in lp_data["data"]:
        st.subheader("📊 LP Positions Found")
        for i, position in enumerate(lp_data["data"]["positions"]):
            pool = position["pool"]
            st.markdown(f"**Position {i+1}: {pool['token0']['symbol']} / {pool['token1']['symbol']}**")
            st.markdown(f"- Liquidity: {position['liquidity']}")
            st.markdown(f"- Fee Tier: {int(pool['feeTier']) / 10000:.2%}")
            st.markdown(f"- Tick Range: {position['tickLower']['tickIdx']} to {position['tickUpper']['tickIdx']}")
            st.markdown("---")
    else:
        st.warning("No LP positions found or failed to fetch.")

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
