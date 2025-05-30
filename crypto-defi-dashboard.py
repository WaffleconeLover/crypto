import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="ETH Leverage Loop Simulator", layout="wide")

# -------------------------------
# Section 1: Fetch ETH Price
# -------------------------------
@st.cache_data(ttl=600)
def fetch_eth_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        response = requests.get(url)
        return response.json()["ethereum"]["usd"]
    except Exception:
        return None

st.title("ETH Leverage Loop Simulator")

st.header("Step 1: ETH Price")
if st.button("Refresh ETH Price from CoinGecko"):
    st.cache_data.clear()

eth_price = fetch_eth_price()
if eth_price:
    st.markdown(f"**Real-Time ETH Price:** ${eth_price:,.2f}")
else:
    st.warning("Unable to fetch live ETH price. Please refresh or enter manually.")
    eth_price = st.number_input("Manual ETH Price", min_value=100.0, max_value=10000.0, value=2600.0)

# -------------------------------
# Section 2: Loop 1 Setup
# -------------------------------
st.header("Step 2: Configure Loop 1")
initial_collateral = st.number_input("Initial ETH Collateral", min_value=0.0, value=6.73, step=0.01)
ltv1 = st.slider("Loop 1 Borrow LTV (%)", min_value=10, max_value=58, value=40)

# Loop 1 calculations
usdc_borrowed1 = initial_collateral * eth_price * (ltv1 / 100)
eth_gained1 = usdc_borrowed1 / eth_price
eth_stack1 = initial_collateral + eth_gained1
health_score1 = (eth_stack1 * eth_price) / usdc_borrowed1 if usdc_borrowed1 > 0 else 999

st.subheader("Loop 1 Summary")
st.markdown(f"- **Debt After Loop 1:** ${usdc_borrowed1:,.2f}")
st.markdown(f"- **ETH Gained After Loop 1:** {eth_gained1:.2f}")
st.markdown(f"- **ETH Stack After Loop 1:** {eth_stack1:.2f}")
st.markdown(f"- **Loop 1 Health Score:** {health_score1:.2f}")

# -------------------------------
# Section 3: Loop 2 Evaluation
# -------------------------------
st.header("Step 3: Loop 2 Evaluation")

ltv2_range = range(30, 51)
loop2_rows = []

eth_stack_after_loop1 = eth_stack1  # 6.73 + ETH gained in Loop 1
usdc_debt_after_loop1 = usdc_borrowed1

for ltv2 in ltv2_range:
    loop2_usdc = eth_stack_after_loop1 * eth_price * (ltv2 / 100)
    total_debt = usdc_debt_after_loop1 + loop2_usdc
    health_score = (eth_stack_after_loop1 * eth_price) / total_debt if total_debt > 0 else 999
    percent_to_liquidation = health_score / 1.0
    liquidation_price = eth_price / percent_to_liquidation

    loop2_rows.append({
        "LTV (%)": ltv2,
        "Health Score": round(health_score, 2),
        "Loan Amount ($)": f"${loop2_usdc:,.2f}",
        "% to Liquidation": f"{percent_to_liquidation * 100:.1f}%",
        "ETH Price at Liquidation": f"${liquidation_price:,.2f}"
    })

df_loop2 = pd.DataFrame(loop2_rows)
st.dataframe(df_loop2, use_container_width=True)
