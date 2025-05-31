import streamlit as st
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Crypto Defi Dashboard",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("# AAVE Collateral and Lending")

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

st.header("Step 1: Fetch ETH Price")

eth_price = st.session_state.eth_price
st.markdown(f"**Real-Time ETH Price:** ${eth_price:,.2f}")

# --- AAVE Account Info via The Graph ---
st.header("Step 2: Aave Account Overview")
wallet_address = "0xb4f25c81fb52d959616e3837cbc9e24a283b9df4".lower()

query = f"""
{{
  userReserves(where: {{ user: \"{wallet_address}\" }}) {{
    reserve {{
      symbol
      decimals
    }}
    currentATokenBalance
    currentTotalDebt
  }}
  users(where: {{ id: \"{wallet_address}\" }}) {{
    healthFactor
  }}
}}
"""

response = requests.post(
    "https://api.thegraph.com/subgraphs/name/aave/protocol-v3-arbitrum",
    json={"query": query}
)

try:
    json_data = response.json()
    result = json_data.get("data", {})
except Exception as e:
    st.error("Failed to decode JSON from The Graph.")
    st.stop()

supplied_eth = 0
borrowed_usd = 0
health_factor = 0

if "userReserves" in result:
    for entry in result.get("userReserves", []):
        if entry.get("reserve", {}).get("symbol", "").lower() == "weth":
            decimals = int(entry["reserve"].get("decimals", 18))
            supplied_eth = float(entry.get("currentATokenBalance", 0)) / 10 ** decimals
        if entry.get("currentTotalDebt"):
            borrowed_usd += float(entry["currentTotalDebt"])

if result.get("users") and len(result["users"]) > 0:
    health_factor = float(result["users"][0].get("healthFactor", 0))

# --- Derived Metrics ---
total_collateral_usd = supplied_eth * eth_price
liq_price = borrowed_usd / (supplied_eth * 0.8) if supplied_eth > 0 else 0
pct_to_liq = 1 - (liq_price / eth_price) if eth_price > 0 else 0

# --- Loop 1 Summary ---
st.subheader("Loop 1 Summary")
st.markdown(f"- **Debt After Loop 1:** ${borrowed_usd:,.2f}")
st.markdown(f"- **ETH Stack After Loop 1:** {supplied_eth:.2f}")
st.markdown(f"- **New Collateral After Loop 1:** ${total_collateral_usd:,.2f}")
st.markdown(f"- **Loop 1 Health Score:** {health_factor:.2f}")
st.markdown(f"- **Loop 1 % to Liquidation:** {pct_to_liq:.1%}")
st.markdown(f"- **Loop 1 Liquidation Price:** ${liq_price:,.2f}")

# --- Volatility ---
def get_eth_volatility(days):
    df = yf.download("ETH-USD", period="90d", interval="1d")
    price_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    df['returns'] = df[price_col].pct_change()
    price_series = df[price_col]
    rolling_std = df['returns'].rolling(window=days).std()
    vol_annualized = rolling_std.iloc[-1] * np.sqrt(365)
    return vol_annualized, df, price_series, rolling_std

expected_lp_days = 7
vol, hist_df, price_series, rolling_std = get_eth_volatility(expected_lp_days)
vol_pct = vol * 100

def categorize_vol(v):
    if v < 20:
        return "Low"
    elif v < 40:
        return "Moderate"
    else:
        return "High"

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
    total_debt = borrowed_usd + loan2
    hf = (total_collateral_usd * 0.80) / total_debt if total_debt > 0 else 0
    liq_price2 = total_debt / (supplied_eth * 0.80) if supplied_eth > 0 else 0
    pct_to_liq2 = 1 - (liq_price2 / eth_price) if eth_price > 0 else 0
    loop2_data.append({
        "LTV (%)": ltv2,
        "Health Score": round(hf, 2),
        "Loan Amount ($)": f"${loan2:,.2f}",
        "Total New Debt ($)": f"${total_debt:,.2f}",
        "% to Liquidation": f"{pct_to_liq2:.1%}",
        "ETH Price at Liquidation": f"${liq_price2:,.2f}"
    })

df = pd.DataFrame(loop2_data)
st.dataframe(df, use_container_width=True)
