# LP Exit Strategy Planner - Tab Extension for ETH Loop Simulator

import streamlit as st
import pandas as pd

st.header("Step 4: LP Exit Strategy Planner")

# User inputs for LP range and unwind conditions
lp_low = st.number_input("Your LP Lower Bound ($)", value=2300.0)
lp_high = st.number_input("Your LP Upper Bound ($)", value=2500.0)
current_price = st.session_state.eth_price

# Determine out-of-range status
if current_price > lp_high:
    out_of_range = "above"
elif current_price < lp_low:
    out_of_range = "below"
else:
    out_of_range = "in"

# Optional: fees earned + loop 2 debt inputs
fees_earned_eth = st.number_input("Estimated Fees Earned (ETH)", value=0.10, step=0.01)
loop2_debt_usd = st.number_input("Loop 2 USDC Debt ($)", value=4000.00, step=50.00)

# ETH stack
eth_stack = st.number_input("Current ETH Stack", value=8.75, step=0.01)
collateral_usd = eth_stack * current_price

st.subheader("Guidance")

if out_of_range == "in":
    st.success("✅ Your LP is currently in range. Let it continue accumulating fees.")

elif out_of_range == "above":
    repayable_eth = loop2_debt_usd / current_price
    net_eth = fees_earned_eth - repayable_eth
    st.markdown(f"You are **{(current_price - lp_high) / lp_high:.1%} above** your LP range.")
    st.markdown(f"You've earned approximately **{fees_earned_eth:.2f} ETH** in fees.")
    st.markdown(f"Loop 2 debt is **${loop2_debt_usd:,.2f}**, which equals **{repayable_eth:.2f} ETH** at current price.")

    if net_eth > 0:
        st.success(f"✅ You can fully repay Loop 2 with fees and retain **{net_eth:.2f} ETH**.")
    else:
        st.warning(f"⚠️ You are short **{abs(net_eth):.2f} ETH** to repay Loop 2. Consider partial repay or wait for more fees.")

elif out_of_range == "below":
    eth_needed = loop2_debt_usd / current_price
    if eth_needed <= eth_stack:
        st.warning(f"🟡 Your LP is fully in ETH. You can repay Loop 2 with **{eth_needed:.2f} ETH**, leaving **{eth_stack - eth_needed:.2f} ETH**.")
    else:
        st.error(f"🔴 Your ETH is currently worth **${collateral_usd:,.2f}**, but Loop 2 debt is **${loop2_debt_usd:,.2f}**.")
        recovery_price = loop2_debt_usd / eth_stack
        st.markdown(f"You need ETH to rise to **${recovery_price:,.2f}** to break even and repay.")

