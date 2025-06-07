import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

st.title("Band 1 Range Chart and Drawdowns")

# ETH price button
if st.button("Refresh ETH Price"):
    try:
        eth_price = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd").json()["ethereum"]["usd"]
        st.session_state.eth_price = eth_price
    except:
        st.session_state.eth_price = "Error fetching"
if "eth_price" in st.session_state:
    st.write(f"Current ETH Price: ${st.session_state.eth_price}")

# Text input for Band 1
user_input = st.text_area("Paste Band 1 block", height=200)

if user_input:
    # Clean whitespace
    lines = [line.strip() for line in user_input.strip().split("\n") if line.strip()]
    
    # Parse values
    try:
        min_val = int(lines[0].split("Min = ")[1].split(" |")[0])
        max_val = int(lines[0].split("Max = ")[1].split(" |")[0])
        liq_price = int(lines[0].split("Liq. Price = ")[1].split(" |")[0])

        dd_prices = []
        dd_labels = []
        for line in lines[1:]:
            pct_label = line.split("= ")[0]
            price = int(line.split("= ")[1].split(" |")[0])
            dd_prices.append(price)
            dd_labels.append(pct_label)

        # Generate time series
        now = datetime.now()
        times = [now - timedelta(minutes=15 * i) for i in range(50)][::-1]
        prices = np.linspace(min_val, max_val, len(times))

        # Heikin Ashi conversion
        df = pd.DataFrame({"Time": times, "Close": prices})
        df["Open"] = df["Close"].shift(1).fillna(df["Close"][0])
        df["High"] = df[["Open", "Close"]].max(axis=1)
        df["Low"] = df[["Open", "Close"]].min(axis=1)

        df["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
        ha_open = [(df["Open"][0] + df["Close"][0]) / 2]
        for i in range(1, len(df)):
            ha_open.append((ha_open[i - 1] + df["HA_Close"][i - 1]) / 2)
        df["HA_Open"] = ha_open
        df["HA_High"] = df[["HA_Open", "HA_Close", "High"]].max(axis=1)
        df["HA_Low"] = df[["HA_Open", "HA_Close", "Low"]].min(axis=1)

        # Chart 1: Band range
        fig, ax = plt.subplots(figsize=(10, 4))
        for i in range(len(df)):
            color = "green" if df["HA_Close"][i] > df["HA_Open"][i] else "red"
            ax.plot([df["Time"][i], df["Time"][i]], [df["HA_Low"][i], df["HA_High"][i]], color=color)
            ax.add_patch(plt.Rectangle((mdates.date2num(df["Time"][i]) - 0.005, min(df["HA_Open"][i], df["HA_Close"][i])),
                                       0.01, abs(df["HA_Close"][i] - df["HA_Open"][i]), color=color))

        ax.axhline(min_val, color="blue", linestyle="--", label="Band Min")
        ax.axhline(max_val, color="orange", linestyle="--", label="Band Max")
        ax.set_ylim(min_val * 0.99, max_val * 1.01)
        ax.set_title("Band 1 Range Chart")
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.legend()
        st.pyplot(fig)

        # Chart 2: Drawdowns
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(df["Time"], df["Close"], label="ETH Price", color="black")

        for label, price in zip(dd_labels, dd_prices):
            ax2.axhline(price, linestyle="--", label=label)

        ax2.set_ylim(min(dd_prices) * 0.99, max(dd_prices) * 1.01)
        ax2.set_title("Band 1 Drawdowns Chart")
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax2.legend()
        st.pyplot(fig2)

    except Exception as e:
        st.error(f"Failed to parse input: {e}")
