import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import datetime
import requests

# -- Fetch ETH price data for last 48 hours
@st.cache_data(ttl=300)
def fetch_eth_prices():
    url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
    params = {"vs_currency": "usd", "days": 2, "interval": "hourly"}
    r = requests.get(url, params=params)
    data = r.json()
    prices = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    prices["timestamp"] = pd.to_datetime(prices["timestamp"], unit="ms")
    prices.set_index("timestamp", inplace=True)
    return prices

eth_df = fetch_eth_prices()

# -- Sidebar and inputs
st.title("Banding LP Chart Builder")
st.button("Refresh ETH Price")

st.markdown("**Current ETH Price:** ${:.2f}".format(eth_df["price"].iloc[-1]))

user_input = st.text_area("Paste Band 1 Block:")
submit = st.button("Generate Chart")

if submit:
    try:
        lines = [line.strip() for line in user_input.strip().splitlines() if line.strip()]

        band_data = {}
        levels = []
        for line in lines:
            if line.startswith("Band"):
                parts = dict(item.strip().split("=", 1) for item in line.split("|") if "=" in item)
                band_data = {
                    "min": float(parts["Min"]),
                    "max": float(parts["Max"]),
                    "liq": float(parts["Liq. Price"]),
                    "drop": float(parts["Liq. Drop %"])
                }
            elif "% Down" in line:
                parts = dict(item.strip().split("=", 1) for item in line.split("|") if "=" in item)
                pct = line.split("% Down")[0].strip()
                levels.append((pct + "% Down", float(parts["= " if "= " in parts else list(parts.keys())[0]])))

        if band_data:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

            # Plot 1 - Range
            ax1.plot(eth_df.index, eth_df["price"], label="ETH Price", color="green")
            ax1.axhline(band_data["min"], linestyle="--", color="blue", label="Band Min")
            ax1.axhline(band_data["max"], linestyle="--", color="orange", label="Band Max")
            ax1.legend()
            ax1.set_title("Band 1 Range Chart")
            ax1.set_ylabel("Price")
            ax1.grid(True, linestyle='--', alpha=0.5)

            # Plot 2 - Drawdowns
            for label, level in levels:
                ax2.axhline(level, linestyle="--", label=label, color="skyblue")
            ax2.set_title("Band 1 Drawdowns Chart")
            ax2.set_ylabel("Price")
            ax2.legend()
            ax2.grid(True, linestyle='--', alpha=0.5)

            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H"))
            plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")

            st.pyplot(fig)

    except Exception as e:
        st.error(f"Error processing input: {e}")
