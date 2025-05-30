import streamlit as st
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

st.set_page_config(page_title="ETH Leverage Loop Simulator", layout="wide")
st.title("ETH Leverage Loop Simulator")

# --- Fetch ETH Price ---
def fetch_eth_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        return r.json()["ethereum"]["usd"]
    except:
        return 2600.00  # fallback price

if "eth_price" not in st.session_state:
    st.session_state.eth_price = fetch_eth_price()

if st.button("Refresh ETH Price from CoinGecko"):
    st.session_state.eth_price = fetch_eth_price()

eth_price = st.session_state.eth_price
st.markdown(f"**Real-Time ETH Price:** ${eth_price:,.2f}")

# --- Lock/Unlock Mechanism ---
if "lock_settings" not in st.session_state:
    st.session_state.lock_settings = False

st.header("Step 2: Configure Loop 1")

col1, col2 = st.columns(2)
with col1:
    if not st.session_state.lock_settings:
        initial_collateral_eth = st.number_input("Initial ETH Collateral", value=6.73, step=0.01, key="initial_eth")
    else:
        st.markdown(f"**Initial ETH Collateral:** {st.session_state.initial_eth}")
with col2:
    if not st.session_state.lock_settings:
        ltv1 = st.slider("Loop 1 Borrow LTV (%)", min_value=10, max_value=58, value=30, key="ltv1")
    else:
        st.markdown(f"**Loop 1 LTV:** {st.session_state.ltv1}")

expected_lp_days = st.slider("Expected LP Duration (Days)", 1, 30, 7)

col3, col4 = st.columns(2)
with col3:
    if st.button("Lock Loop 1 Settings"):
        st.session_state.lock_settings = True
        st.session_state.initial_eth = initial_collateral_eth
        st.session_state.ltv1 = ltv1
with col4:
    if st.button("Unlock Loop 1 Settings"):
        st.session_state.lock_settings = False

# --- Loop 1 Calculation ---
initial_eth = st.session_state.get("initial_eth", 6.73)
ltv1 = st.session_state.get("ltv1", 30)
collateral_usd = initial_eth * eth_price
debt_usd = collateral_usd * ltv1 / 100
eth_gained = debt_usd / eth_price
total_eth = initial_eth + eth_gained
total_collateral_usd = total_eth * eth_price
health_score = (total_collateral_usd * 0.80) / debt_usd
liq_price = (debt_usd / total_eth) / 0.80
pct_to_liq = 1 - (liq_price / eth_price)

# --- Volatility ---
def get_eth_volatility(days):
    df = yf.download("ETH-USD", period="90d", interval="1d")
    price_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    df['returns'] = df[price_col].pct_change()
    price_series = df[price_col]
    rolling_std = df['returns'].rolling(window=days).std()
    vol_annualized = rolling_std.iloc[-1] * np.sqrt(365)
    return vol_annualized, df, price_series, rolling_std

vol, hist_df, price_series, rolling_std = get_eth_volatility(expected_lp_days)
vol_pct = vol * 100

def categorize_vol(v):
    if v < 20:
        return "Low"
    elif v < 40:
        return "Moderate"
    else:
        return "High"

# --- Loop 1 Summary ---
st.subheader("Loop 1 Summary")
st.markdown(f"- **Debt After Loop 1:** ${debt_usd:,.2f}")
st.markdown(f"- **ETH Gained After Loop 1:** {eth_gained:.2f}")
st.markdown(f"- **ETH Stack After Loop 1:** {total_eth:.2f}")
st.markdown(f"- **New Collateral After Loop 1:** ${total_collateral_usd:,.2f}")
st.markdown(f"- **Loop 1 Health Score:** {health_score:.2f}")
st.markdown(f"- **Loop 1 % to Liquidation:** {pct_to_liq:.1%}")
st.markdown(f"- **Loop 1 Liquidation Price:** ${liq_price:,.2f}")
st.markdown(f"- **Est. Annualized Volatility ({expected_lp_days}D Lookback):** {vol_pct:.2f}%")
st.markdown(f"- **Market Behavior:** {categorize_vol(vol_pct)}")

# --- Volatility Chart ---
st.subheader("Volatility Trend")
fig, ax1 = plt.subplots(figsize=(8, 3))
ax1.plot(price_series.index, price_series, color='blue', label='ETH Price ($)')
ax1.set_ylabel("ETH Price ($)", color='blue')
ax2 = ax1.twinx()
ax2.plot(rolling_std.index, rolling_std * 100 * np.sqrt(365), color='red', label='Annualized Volatility (%)')
ax2.set_ylabel("Annualized Volatility (%)", color='red')
fig.tight_layout()
st.pyplot(fig)

# --- Loop 2 Simulation ---
st.header("Step 3: Loop 2 Evaluation")
loop2_data = []
for ltv2 in range(10, 50):
    loan2 = total_collateral_usd * ltv2 / 100
    total_debt = debt_usd + loan2
    hf = (total_collateral_usd * 0.80) / total_debt
    liq_price2 = total_debt / (total_eth * 0.80)
    pct_to_liq2 = 1 - (liq_price2 / eth_price)
    loop2_data.append({
        "LTV (%)": ltv2,
        "Health Score": round(hf, 2),
        "Loan Amount ($)": f"${loan2:,.2f}",
        "% to Liquidation": f"{pct_to_liq2:.1%}",
        "ETH Price at Liquidation": f"${liq_price2:,.2f}"
    })

df = pd.DataFrame(loop2_data)
st.dataframe(df, use_container_width=True)
