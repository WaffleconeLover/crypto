import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(layout="wide")
st.title("Banding LP Chart Builder")

# ----------------------------
# ETH Price Handling
# ----------------------------
fallback_price = 2500
eth_price = st.session_state.get("eth_price", fallback_price)

def fetch_eth_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "ethereum", "vs_currencies": "usd"}
        r = requests.get(url, params=params)
        return r.json()["ethereum"]["usd"]
    except:
        return None

if st.button("Refresh ETH Price"):
    new_price = fetch_eth_price()
    if new_price:
        st.session_state.eth_price = new_price
        eth_price = new_price
    else:
        st.error("Failed to retrieve ETH price data from CoinGecko.")
        eth_price = fallback_price

if eth_price:
    st.markdown(f"**Current ETH Price:** ${eth_price:.2f}")
else:
    st.markdown(f"**Current ETH Price:** _Not Available — using fallback (${fallback_price})_")
    eth_price = fallback_price

# ----------------------------
# Band Input
# ----------------------------
band_text = st.text_area("Paste Band Data Here:")

def parse_band_lines(lines):
    bands = []
    zones = []
    for line in lines:
        line = line.strip()
        if not line or "=" not in line:
            continue

        if line.startswith("Band"):
            band_data = {}
            try:
                for part in line.split("|"):
                    key, value = part.strip().split(" = ")
                    key = key.strip()
                    value = value.strip().replace('%', '')
                    band_data[key] = float(value) if "Drop" in key or "Spread" in key else int(value)
                bands.append(band_data)
            except Exception as e:
                st.warning(f"Failed to parse band line: {line} — {e}")

        elif "Down" in line:
            try:
                zone = {}
                first_eq = line.split("=", 1)
                zone["label"] = first_eq[0].strip()
                zone["level"] = float(first_eq[1].split("|")[0].strip())

                parts = line.split("|")
                for part in parts:
                    if "=" in part:
                        k, v = part.strip().split(" = ")
                        k = k.strip()
                        v = v.strip().replace('%', '')
                        if "Drop" in k:
                            zone["Liq. Drop %"] = float(v)
                zones.append(zone)
            except Exception as e:
                st.warning(f"Failed to parse zone line: {line} — {e}")
    return bands, zones

# ----------------------------
# Heiken Ashi Candles
# ----------------------------
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
            ha_open.append((ha_open[i - 1] + ha_df["HA_Close"].iloc[i - 1]) / 2)
        ha_df["HA_Open"] = ha_open
        ha_df["HA_High"] = ha_df[["HA_Open", "HA_Close", "high"]].max(axis=1)
        ha_df["HA_Low"] = ha_df[["HA_Open", "HA_Close", "low"]].min(axis=1)
        return ha_df
    except:
        return pd.DataFrame()

# ----------------------------
# Chart Generator
# ----------------------------
if st.button("Generate Chart") and band_text:
    lines = band_text.strip().split("\n")
    bands, zones = parse_band_lines(lines)
    ha = get_heiken_ashi()

    fig, ax = plt.subplots(figsize=(14, 6))
    all_prices = []

    for band in bands:
        ax.axhspan(band["Min"], band["Max"], color="green", alpha=0.3)
        ax.axhline(band["Liq. Price"], linestyle="--", color="red")
        mid = (band["Min"] + band["Max"]) / 2
        label_time = ha.index[-1] if not ha.empty else datetime.utcnow()
        ax.text(label_time, mid,
                f'{band["Min"]} – {band["Max"]}\nLiq: ${band["Liq. Price"]:.0f} ({band["Liq. Drop %"]:.1%})',
                fontsize=9, va="center", ha="right")
        all_prices.extend([band["Min"], band["Max"], band["Liq. Price"]])

    for zone in zones:
        if "level" in zone:
            ax.axhline(zone["level"], linestyle="dotted", color="crimson")
            label_time = ha.index[-1] if not ha.empty else datetime.utcnow()
            ax.text(label_time, zone["level"],
                    f"{zone['label']} | Buffer = {zone['Liq. Drop %']:.1%}",
                    fontsize=8, va="bottom", ha="right")
            all_prices.append(zone["level"])

    if not ha.empty:
        for i in range(len(ha)):
            color = "green" if ha["HA_Close"].iloc[i] > ha["HA_Open"].iloc[i] else "red"
            ax.plot([ha.index[i], ha.index[i]], [ha["HA_Low"].iloc[i], ha["HA_High"].iloc[i]], color=color)
            ax.plot([ha.index[i], ha.index[i]], [ha["HA_Open"].iloc[i], ha["HA_Close"].iloc[i]], color=color, linewidth=5)

    if all_prices:
        ymin = min(all_prices) * 0.99
        ymax = max(all_prices) * 1.01
        ax.set_ylim(ymin, ymax)

    ax.set_title("Liquidity Bands and Liquidation Zones")
    ax.set_ylabel("ETH Price")
    st.pyplot(fig)
