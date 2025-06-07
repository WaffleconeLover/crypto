import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from datetime import datetime

st.set_page_config(page_title="Banding LP Chart Builder", layout="wide")
st.title("Banding LP Chart Builder")

# --- Constants to preserve UI components ---
LOCKED_UI_BLOCK = True

@st.cache_data(ttl=300)
def fetch_eth_prices():
    url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
    params = {"vs_currency": "usd", "days": "3", "interval": "hourly"}
    response = requests.get(url, params=params)

    if response.status_code != 200:
        st.error("Failed to fetch ETH price data.")
        return pd.DataFrame(columns=["timestamp", "price"])

    data = response.json()
    if "prices" not in data:
        st.error("Malformed data received from CoinGecko.")
        return pd.DataFrame(columns=["timestamp", "price"])

    prices = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    prices["timestamp"] = pd.to_datetime(prices["timestamp"], unit="ms")
    prices.set_index("timestamp", inplace=True)
    return prices

# --- UI Controls ---
col1, col2 = st.columns([4, 1])
with col1:
    st.subheader("Paste Band 1 Block")
    band_input = st.text_area("", height=150)
with col2:
    st.write("\n")
    st.write("\n")
    if st.button("Refresh ETH Price"):
        st.session_state["eth_df"] = fetch_eth_prices()

eth_df = st.session_state.get("eth_df", fetch_eth_prices())

# Display current ETH price if available
if not eth_df.empty:
    latest_price = eth_df["price"].iloc[-1]
    st.write(f"Current ETH Price: ${latest_price:,.2f}")
else:
    st.write("Current ETH Price: *Not Available*")

# --- Chart Generation ---
if st.button("Generate Chart"):
    if not band_input:
        st.warning("Please paste a valid Band 1 block to generate the chart.")
    else:
        try:
            # Parse band metadata
            lines = band_input.splitlines()
            band_line = lines[0]
            band_data = {s.split("=")[0].strip(): float(s.split("=")[1]) for s in band_line.split("|") if "=" in s}
            band_min = band_data.get("Min")
            band_max = band_data.get("Max")
            band_name = band_line.split("|")[0].strip()

            # Parse drawdown levels
            dd_lines = [line for line in lines[1:] if "Down =" in line]
            drawdowns = []
            for line in dd_lines:
                label = line.split("=")[0].strip()
                parts = {s.split("=")[0].strip(): float(s.split("=")[1]) for s in line.split("|") if "=" in s}
                drawdowns.append((label, parts["Liq. Price"]))

            # Plotting
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

            # --- Band Range Chart ---
            ax1.plot(eth_df.index, eth_df["price"], label="ETH Price", color="green")
            ax1.axhline(band_min, color="blue", linestyle="--", label="Band Min")
            ax1.axhline(band_max, color="orange", linestyle="--", label="Band Max")
            ax1.set_title(f"{band_name} Range Chart")
            ax1.set_ylabel("Price")
            ax1.legend()
            ax1.grid(True)

            # --- Drawdowns Chart ---
            ax2.set_title(f"{band_name} Drawdowns Chart")
            for label, level in drawdowns:
                ax2.axhline(level, linestyle="--", label=label)
            ax2.set_ylabel("Price")
            ax2.grid(True)
            ax2.legend()

            st.pyplot(fig)

        except Exception as e:
            st.error(f"Failed to parse input or render chart: {e}")
