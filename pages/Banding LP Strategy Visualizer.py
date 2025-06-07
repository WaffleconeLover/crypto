import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import requests
from matplotlib.ticker import FuncFormatter

st.set_page_config(layout="wide")
st.title("Banding LP Chart Builder")

# ETH price fetch button
if st.button("Refresh ETH Price"):
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        eth_price = response.json()["ethereum"]["usd"]
        st.session_state["eth_price"] = eth_price
    except Exception:
        st.error("Failed to retrieve ETH price data from CoinGecko.")

# Display current ETH price
eth_price = st.session_state.get("eth_price", "Not Available")
st.markdown(f"**Current ETH Price:** {eth_price if isinstance(eth_price, str) else f'${eth_price:.2f}'}")

input_text = st.text_area("Paste Band Data Here:", height=200)

if st.button("Generate Chart"):
    lines = input_text.strip().split("\n")

    bands = []
    zones = []
    current_band = {}

    for line in lines:
        line = line.strip()
        try:
            if line.startswith("Band"):
                if current_band:
                    bands.append(current_band)
                    current_band = {}
                parts = line.split("|")
                current_band = {
                    "label": parts[0].strip(),
                    "min": float(parts[1].split("=")[1].strip()),
                    "max": float(parts[2].split("=")[1].strip()),
                    "spread": parts[3].split("=")[1].strip(),
                    "liq_price": float(parts[4].split("=")[1].strip()),
                    "liq_drop_pct": float(parts[5].split("=")[1].strip())
                }
            elif "% Down" in line:
                parts = line.split("|")
                zones.append({
                    "band": current_band.get("label", "Unknown"),
                    "level": float(parts[0].split("=")[1].strip()),
                    "liq_price": float(parts[1].split("=")[1].strip()),
                    "distance": float(parts[2].split("=")[1].strip()),
                    "buffer": float(parts[3].split("=")[1].strip())
                })
        except Exception as e:
            st.warning(f"Failed to parse line: {line} — {e}")

    if current_band:
        bands.append(current_band)

    if not bands:
        st.warning("No valid band data found.")
    else:
        # Mock 15-min Heiken Ashi candles
        def generate_mock_candles():
            now = datetime.now()
            times = [now - timedelta(minutes=15 * i) for i in range(96)][::-1]
            base = eth_price if isinstance(eth_price, (int, float)) else 2500
            data = []
            price = base
            for t in times:
                open_ = price + (1 - 2 * (t.minute % 2)) * 5
                close = open_ + (1 - 2 * (t.minute % 3)) * 5
                high = max(open_, close) + 2
                low = min(open_, close) - 2
                data.append((t, open_, high, low, close))
                price = close
            return pd.DataFrame(data, columns=["time", "open", "high", "low", "close"])

        ha_df = generate_mock_candles()

        for band in bands:
            ymin = band["min"] * 0.99
            ymax = band["max"] * 1.01

            fig, ax = plt.subplots(figsize=(12, 5))
            ax.set_title(f"{band['label']} Range Chart")
            ax.set_ylabel("ETH Price")
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())

            # Candles
            for i in range(len(ha_df)):
                row = ha_df.iloc[i]
                color = "green" if row.close >= row.open else "red"
                ax.plot([row.time, row.time], [row.low, row.high], color=color)
                ax.plot([row.time, row.time], [row.open, row.close], color=color, linewidth=5)

            # Range
            ax.axhspan(band["min"], band["max"], color="green", alpha=0.2)
            ax.axhline(band["liq_price"], color="crimson", linestyle="dashed")
            ax.text(ha_df.index[-1], band["liq_price"], f"Liq: ${band['liq_price']} ({band['liq_drop_pct'] * 100:.1f}%)", 
                    va="bottom", ha="right", fontsize=9)
            ax.text(ha_df.index[-1], (band["min"] + band["max"]) / 2, f"{band['label']}\n{int(band['min'])} - {int(band['max'])}", 
                    va="top", ha="right", fontsize=9)

            st.pyplot(fig)

            # Drawdown chart
            fig2, ax2 = plt.subplots(figsize=(12, 3))
            ax2.set_title(f"{band['label']} Drawdowns Chart")
            ax2.set_ylabel("ETH Price")
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H'))
            ax2.xaxis.set_major_locator(mdates.AutoDateLocator())

            for zone in zones:
                if zone['band'] == band['label']:
                    ax2.axhline(zone["level"], linestyle="dotted", color="crimson")
                    ax2.text(ha_df.index[-1], zone["level"], f"{int(zone['level'])} | {zone['buffer']*100:.0f}%", 
                             va="bottom", ha="right", fontsize=8)

            st.pyplot(fig2)
