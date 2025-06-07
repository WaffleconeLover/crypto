import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("Banding LP Chart Builder")

# ETH price logic
@st.cache_data(ttl=300)
def get_eth_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        return r.json()["ethereum"]["usd"]
    except:
        return None

eth_price = get_eth_price()
if st.button("Refresh ETH Price"):
    get_eth_price.clear()
    eth_price = get_eth_price()

if eth_price:
    st.markdown(f"**Current ETH Price: ${eth_price}**")

# Heiken Ashi generation
def get_heiken_ashi():
    url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=1&interval=minute"
    try:
        r = requests.get(url)
        data = r.json()
        if r.status_code != 200 or "prices" not in data:
            st.error("Failed to retrieve ETH price data from CoinGecko.")
            return pd.DataFrame()
        
        df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df = df.resample("15T").ohlc().dropna()

        ha = pd.DataFrame(index=df.index)
        ha["Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
        ha["Open"] = 0.0
        ha.iloc[0, ha.columns.get_loc("Open")] = (df.iloc[0]["open"] + df.iloc[0]["close"]) / 2
        for i in range(1, len(ha)):
            ha.iloc[i, ha.columns.get_loc("Open")] = (ha.iloc[i - 1]["Open"] + ha.iloc[i - 1]["Close"]) / 2
        ha["High"] = ha[["Open", "Close"]].join(df["high"]).max(axis=1)
        ha["Low"] = ha[["Open", "Close"]].join(df["low"]).min(axis=1)
        return ha.dropna()
    except Exception as e:
        st.error(f"Error fetching Heiken Ashi data: {e}")
        return pd.DataFrame()

# UI
input_text = st.text_area("Paste Band Data Here:", height=300)
submit = st.button("Generate Chart")

if submit and input_text:
    lines = [line.strip() for line in input_text.splitlines() if line.strip()]
    bands = []
    i = 0
    while i < len(lines):
        if not lines[i].lower().startswith("band"):
            i += 1
            continue
        try:
            band_line = lines[i]
            zone_lines = lines[i+1:i+4]
            parts = [p.strip() for p in band_line.split("|")]

            band_name = parts[0]
            band_min = float(parts[1].split("=")[1].strip())
            band_max = float(parts[2].split("=")[1].strip())
            liq_price = float(parts[4].split("=")[1].strip())
            liq_drop = float(parts[5].split("=")[1].strip())

            zones = []
            for zl in zone_lines:
                label = zl.split("=")[0].strip()
                price = float(zl.split("=")[1].split("|")[0].strip())
                zones.append((label, price))

            bands.append({
                "name": band_name,
                "min": band_min,
                "max": band_max,
                "liq": liq_price,
                "liq_drop": liq_drop,
                "zones": zones
            })
            i += 4
        except Exception as e:
            st.warning(f"Failed to parse lines starting with: {lines[i]}")
            i += 1

    # Charting
    if bands:
        ha = get_heiken_ashi()
        fig, ax = plt.subplots(figsize=(14, 6))

        # Plot candles
        if not ha.empty:
            for ts, row in ha.iterrows():
                color = "green" if row["Close"] >= row["Open"] else "red"
                ax.plot([ts, ts], [row["Low"], row["High"]], color=color, linewidth=1)
                ax.add_patch(plt.Rectangle(
                    (ts - timedelta(minutes=5), min(row["Open"], row["Close"])),
                    timedelta(minutes=10),
                    abs(row["Close"] - row["Open"]),
                    color=color, alpha=0.6
                ))

        # Plot bands
        all_prices = []
        for band in bands:
            ax.axhspan(band["min"], band["max"], color="green", alpha=0.25)
            ax.axhline(band["liq"], color="red", linestyle="--", linewidth=1)
            ax.text(ha.index[-1], (band["min"] + band["max"]) / 2,
                    f"{band['name']} ${band['min']}–${band['max']}\nLiq: ${band['liq']} ({round(band['liq_drop']*100, 1)}%)",
                    fontsize=8, va="center", ha="right")
            all_prices.extend([band["min"], band["max"], band["liq"]])
            for label, price in band["zones"]:
                ax.axhline(price, color="crimson", linestyle="--", linewidth=1)
                ax.text(ha.index[0], price, label, va="center", ha="left", fontsize=8, color="crimson")
                all_prices.append(price)

        if all_prices:
            min_y = min(all_prices) * 0.99
            max_y = max(all_prices) * 1.01
            ax.set_ylim(min_y, max_y)

        ax.axhline(eth_price, color="gray", linestyle=":", label=f"ETH Spot = ${eth_price}")
        ax.set_title("Liquidity Bands and Liquidation Zones")
        ax.set_ylabel("ETH Price")
        ax.legend()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        fig.autofmt_xdate()
        st.pyplot(fig)
