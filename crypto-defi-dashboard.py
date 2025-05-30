import streamlit as st
import pandas as pd

st.set_page_config(page_title="ETH Leverage Strategy Dashboard", layout="wide")

# Constants
MIN_HEALTH_SCORE = 1.0
LIQUIDATION_THRESHOLD = 0.83
LOOP2_LTV_RANGE = range(30, 51)  # 30% to 50%

# Title
st.title("ETH Leverage Strategy Dashboard")

# Sidebar reset
if st.button("🔄 Reset All"):
    st.experimental_rerun()

# Loop 1 Setup
st.header("Loop 1 Setup")

eth_price = st.number_input("Current ETH Price ($)", value=2500.0, min_value=100.0, max_value=10000.0, step=50.0)
eth_collateral = st.number_input("Current ETH Collateral", value=6.73, min_value=0.0, max_value=100.0, step=0.01)
ltv1 = st.slider("Loop 1 Borrow LTV (%)", min_value=30, max_value=68, value=40)

# Loop 1 Calculations
loop1_debt = (ltv1 / 100) * eth_collateral * eth_price
eth_gained = loop1_debt / eth_price
eth_stack = eth_collateral + eth_gained
loop1_health_score = (eth_stack * eth_price * LIQUIDATION_THRESHOLD) / loop1_debt if loop1_debt else 0

# Loop 1 Results
st.subheader("Loop 1 Results")
st.write(f"**Debt After Loop 1:** ${loop1_debt:,.2f}")
st.write(f"**ETH Gained After Loop 1:** {eth_gained:.2f}")
st.write(f"**ETH Stack After Loop 1:** {eth_stack:.2f}")
st.write(f"**Loop 1 Health Score:** {loop1_health_score:.2f}")

# Loop 2 Simulation
st.subheader("Loop 2 Simulation")

loop2_results = []

for ltv2 in LOOP2_LTV_RANGE:
    loop2_debt = (ltv2 / 100) * eth_stack * eth_price
    total_debt = loop1_debt + loop2_debt
    total_eth = eth_stack
    health_score = (total_eth * eth_price * LIQUIDATION_THRESHOLD) / total_debt if total_debt else 0
    pct_to_liquidation = max(0.0, (1 - (1 / health_score))) * 100 if health_score > 1 else 0.0
    liquidation_price = eth_price * (1 - (pct_to_liquidation / 100))

    loop2_results.append({
        "LTV Loop 2 (%)": ltv2,
        "USDC Loan": loop2_debt,
        "Health Score": round(health_score, 2),
        "% to Liquidation": f"{pct_to_liquidation:.1f}%",
        "Price at Liquidation": f"${liquidation_price:,.2f}"
    })

# Create DataFrame
df = pd.DataFrame(loop2_results)
df["Rank"] = df["Health Score"].rank(ascending=False).astype(int)

# Hide row index
hide_table_row_index = """
    <style>
    tbody th {display:none}
    .blank {display:none}
    </style>
"""
st.markdown(hide_table_row_index, unsafe_allow_html=True)

# Display DataFrame
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)
