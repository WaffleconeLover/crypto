import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- Settings ---
st.set_page_config(page_title="ETH LP Volatility Dashboard", layout="wide")
st.title("ETH Loop Strategy & Volatility Planner")

# --- Parameters ---
eth_price = st.number_input("Current ETH Price ($)", value=2600.0, step=50.0)
collateral_eth = st.number_input("ETH Deposited (Loop 1)", value=6.73, step=0.1)
loop1_ltv = st.slider("Loop 1 LTV (%)", min_value=10, max_value=60, value=30)
expected_lp_days = st.slider("Expected LP Duration (Days)", min_value=1, max_value=30, value=7)

# --- Volatility Calculation ---
def get_eth_volatility(days):
    end = datetime.today()
    start = end - timedelta(days=days + 5)  # buffer for market closure
    df = yf.download("ETH-USD", start=start, end=end)
    df['returns'] = df['Adj Close'].pct_change()
    vol = df['returns'].std() * np.sqrt(365)  # Annualized volatility
    return vol

vol = get_eth_volatility(expected_lp_days)

if vol < 0.5:
    vol_level = 'Low'
    min_health = 1.4
elif vol < 0.8:
    vol_level = 'Moderate'
    min_health = 1.6
else:
    vol_level = 'High'
    min_health = 1.8

st.markdown(f"**Volatility Level**: {vol_level}  ")
st.markdown(f"**Estimated Annualized Volatility**: {vol:.2%}  ")
st.markdown(f"**Recommended Minimum Loop 2 Health Score**: {min_health}")

# --- Loop 1 Outputs ---
collateral_usd = collateral_eth * eth_price
loop1_loan = collateral_usd * (loop1_ltv / 100)
eth_gained = loop1_loan / eth_price
eth_stack = collateral_eth + eth_gained
new_collateral_usd = eth_stack * eth_price
loop1_health = (new_collateral_usd * 0.8) / loop1_loan

st.subheader("Loop 1 Summary")
st.markdown(f"Debt After Loop 1: ${loop1_loan:,.2f}")
st.markdown(f"ETH Gained After Loop 1: {eth_gained:.2f}")
st.markdown(f"ETH Stack After Loop 1: {eth_stack:.2f}")
st.markdown(f"New Collateral After Loop 1: ${new_collateral_usd:,.2f}")
st.markdown(f"Loop 1 Health Score: {loop1_health:.2f}")

# --- Loop 2 Table ---
ltv2_range = range(10, 51)
rows = []
for ltv2 in ltv2_range:
    usdc_loan_2 = new_collateral_usd * (ltv2 / 100)
    total_debt = loop1_loan + usdc_loan_2
    health_score = (new_collateral_usd * 0.8) / total_debt
    liquidation_price = (total_debt / (eth_stack * 0.85)) if eth_stack > 0 else 0
    pct_to_liquidation = 1 - (liquidation_price / eth_price)
    rows.append({
        "Loop 2 LTV (%)": ltv2,
        "USDC Loan (Loop 2)": usdc_loan_2,
        "Total Debt": total_debt,
        "Health Score": health_score,
        "% to Liquidation": pct_to_liquidation,
        "Liquidation Price ($)": liquidation_price,
        "Volatility Threshold Met?": "Yes" if health_score >= min_health else "No"
    })

loop2_df = pd.DataFrame(rows)

# Format columns
loop2_df["USDC Loan (Loop 2)"] = loop2_df["USDC Loan (Loop 2)"].map("${:,.2f}".format)
loop2_df["Total Debt"] = loop2_df["Total Debt"].map("${:,.2f}".format)
loop2_df["Health Score"] = loop2_df["Health Score"].map("{:.2f}".format)
loop2_df["% to Liquidation"] = loop2_df["% to Liquidation"].map("{:.1%}".format)
loop2_df["Liquidation Price ($)"] = loop2_df["Liquidation Price ($)"].map("${:,.2f}".format)

st.subheader("Loop 2 Scenarios")
st.dataframe(loop2_df, use_container_width=True, hide_index=True)

st.caption("Table highlights whether the selected Loop 2 LTVs meet the volatility-adjusted health score threshold.")
