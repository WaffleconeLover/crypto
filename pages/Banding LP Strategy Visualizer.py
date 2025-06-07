import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import requests
from datetime import datetime, timedelta

st.title("Banding LP Chart Builder")

eth_price = st.session_state.get("eth_price", None)

def fetch_eth_price():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        return response.json()["ethereum"]["usd"]
    except Exception:
        return None

if st.button("Refresh ETH Price"):
    eth_price = fetch_eth_price()
    if eth_price:
        st.session_state.eth_price = eth_price
    else:
        st.error("Failed to retrieve ETH price data from CoinGecko.")

if eth_price:
    st.markdown(f"**Current ETH Price:** ${eth_price}")
else:
    st.markdown("**Current ETH Price:** _Not Available_")

user_input = st.text_area("Paste Band Data Here:")

if st.button("Generate Chart") and user_input:
    lines = [line.strip() for line in user_input.strip().split("\n") if line.strip()]
    bands = []
    zones = []

    for line in lines:
        if line.startswith("Band"):
            try:
                parts = dict(item.strip().split(" = ") for item in line.split("|"))
                bands.append({
                    "label": parts["Band 1"] if "Band 1" in parts else parts.get("Band", "Band"),
                    "min": float(parts["Min"]),
                    "max": float(parts["Max"]),
                    "liq": float(parts["Liq. Price"]),
                    "drop": float(parts["Liq. Drop %"]),
                })
            except Exception as e:
                st.warning(f"Failed to parse line: {line} — {e}")
        elif line.startswith(("5", "10", "15")):
            try:
                pct = line.split("%")[0].strip()
                parts = dict(item.strip().split(" = ") for item in line.split("|"))
                zones.append({
                    "label": f"{pct}% Down",
                    "level": float(parts[f"{pct}% Down"]),
                    "liq": float(parts["Liq. Price"]),
                    "dist": float(parts["Dist. from Liq. Price"]),
                    "buffer": float(parts["Liq. Drop %"]),
                })
            except Exception as e:
                st.warning(f"Failed to parse line: {line} — {e}")

    def get_heiken_ashi():
        try:
            url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
            params = {"vs_currency": "usd", "days": "1", "interval": "minute"}
            r = requests.get(url, params=params).json()
            prices = r["prices"]
            df = pd.DataFrame(prices, columns=["time", "price"])
            df["time"] = pd.to_datetime(df["time"], unit="ms")
            df.set_index("time", inplace=True)
            df = df.resample("15min").ohlc()["price"].dropna()

            ha_df = df.copy()
            ha_df["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
            ha_open = [(df["open"].iloc[0] + df["close"].iloc[0]) / 2]
            for i in range(1, len(df)):
                ha_open.append((ha_open[i-1] + ha_df["HA_Close"].iloc[i-1]) / 2)
            ha_df["HA_Open"] = ha_open
            ha_df["HA_High"] = ha_df[["HA_Open", "HA_Close", "high"]].max(axis=1)
            ha_df["HA_Low"] = ha_df[["HA_Open", "HA_Close", "low"]].min(axis=1)
            return ha_df
        except:
            return pd.DataFrame()

    ha = get_heiken_ashi()

    fig, ax = plt.subplots(figsize=(12, 6))

    for band in bands:
        ax.axhspan(band["min"], band["max"], color="green", alpha=0.3)
        ax.axhline(band["liq"], linestyle="--", color="red")
        mid = (band["min"] + band["max"]) / 2
        text_y = band["liq"] + (band["max"] - band["min"]) * 0.05
        text_x = ha.index[-1] if not ha.empty else datetime.utcnow()
        ax.text(text_x, text_y,
                f"{band['label']} \n{band['min']} – {band['max']}\nLiq: ${band['liq']} ({band['drop']:.3%})",
                fontsize=9, va="top", ha="right")

    for zone in zones:
        ax.axhline(zone["level"], linestyle="dotted", color="red")
        ax.text(ha.index[-1] if not ha.empty else datetime.utcnow(),
                zone["level"],
                f"{zone['label']} = {zone['level']} | Liq. Buffer % = {zone['buffer']:.1%}",
                fontsize=8, va="bottom", ha="right")

    if not ha.empty:
        for i in range(len(ha)):
            color = "green" if ha["HA_Close"].iloc[i] > ha["HA_Open"].iloc[i] else "red"
            ax.plot([ha.index[i], ha.index[i]], [ha["HA_Low"].iloc[i], ha["HA_High"].iloc[i]], color=color)
            ax.plot([ha.index[i], ha.index[i]], [ha["HA_Open"].iloc[i], ha["HA_Close"].iloc[i]],
                    color=color, linewidth=5)

    all_prices = [b["min"] for b in bands] + [b["max"] for b in bands]
    ymin = min(all_prices) * 0.99
    ymax = max(all_prices) * 1.01
    ax.set_ylim(ymin, ymax)
    ax.set_title("Liquidity Bands and Liquidation Zones")
    ax.set_ylabel("ETH Price")

    st.pyplot(fig)
