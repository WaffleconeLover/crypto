import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="ETH Leverage Loop Simulator", layout="wide")

st.title("ETH Leverage Loop Simulator")

# --- Step 1: ETH Price ---
@st.cache_data(show_spinner=False)
def get_eth_price():
    try:
        res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        return res.json()['ethereum']['usd']
    except:
        return None

if "eth_price" not in st.session_state:
    st.session_state.eth_price = get_eth_price()

if st.button("Refresh ETH Price from CoinGecko"):
    st.session_state.eth_price = get_eth_price()

eth_price = st.session_state.eth_price or 2600
st.markdown(f"**Real-Time ETH Price:** ${eth_price:,.2f}")

# --- Step 2: Configure Loop 1 ---
st.header("Step 2: Configure Loop 1")
eth_collateral = st.number_input("Initial ETH Collateral", value=6.73)
loop1_ltv = st.slider("Loop 1 Borrow LTV (%)", min_value=10, max_value=50, value=30)

# --- Step 2A: Loop 1 Calculations ---
collateral_value_l1 = eth_collateral * eth_price
usdc_loan_l1 = collateral_value_l1 * (loop1_ltv / 100)
eth_gained = usdc_loan_l1 / eth_price
eth_stack_after_l1 = eth_collateral + eth_gained
collateral_value_after_l1 = eth_stack_after_l1 * eth_price
health_score_l1 = (collateral_value_l1 * 0.8) / usdc_loan_l1

st.subheader("Loop 1 Summary")
st.markdown(f"- **Debt After Loop 1:** ${usdc_loan_l1:,.2f}")
st.markdown(f"- **ETH Gained After Loop 1:** {eth_gained:.2f}")
st.markdown(f"- **ETH Stack After Loop 1:** {eth_stack_after_l1:.2f}")
st.markdown(f"- **New Collateral After Loop 1:** ${collateral_value_after_l1:,.2f}")
st.markdown(f"- **Loop 1 Health Score:** {health_score_l1:.2f}")

# --- Step 3: Loop 2 Evaluation ---
st.header("Step 3: Loop 2 Evaluation")
data = []
for ltv2 in range(10, 50):
    usdc_loan_l2 = collateral_value_after_l1 * (ltv2 / 100)
    total_debt = usdc_loan_l1 + usdc_loan_l2
    health_score = (collateral_value_after_l1 * 0.8) / total_debt
    percent_to_liq = (1 / health_score) * 100  # 1.0 HF = 100% to liq
    liq_price = eth_price * (1 - percent_to_liq / 100)
    data.append({
        "LTV (%)": ltv2,
        "Health Score": round(health_score, 2),
        "Loan Amount ($)": f"${usdc_loan_l2:,.2f}",
        "% to Liquidation": f"{percent_to_liq:.1f}%",
        "ETH Price at Liquidation": f"${liq_price:,.2f}"
    })

results_df = pd.DataFrame(data)
st.dataframe(results_df, use_container_width=True, hide_index=True)
