import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(layout="wide")
st.title("ETH Liquidity Band Dashboard (Auto Mode Enabled)")

# -- Constants --
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/pairs/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
COINGECKO_API = "https://api.coingecko.com/api/v3/coins/ethereum/ohlc?vs_currency=usd&days=1"

@st.cache_data(ttl=60)
def fetch_eth_spot():
    try:
        r = requests.get(DEXSCREENER_API)
        r.raise_for_status()
        data = r.json()
        return float(data["pair"]["priceUsd"])
    except:
        return None

@st.cache_data(ttl=300)
def fetch_eth_candles():
    try:
        r = requests.get(COINGECKO_API)
        r.raise_for_status()
        raw = r.json()
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except:
        return None

def compute_heikin_ashi(df):
    ha_df = pd.DataFrame(index=df.index)
    ha_df["close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = [(df["open"].iloc[0] + df["close"].iloc[0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i - 1] + ha_df["close"].iloc[i - 1]) / 2)
    ha_df["open"] = ha_open
    ha_df["high"] = df[["high", "open", "close"]].max(axis=1)
    ha_df["low"] = df[["low", "open", "close"]].min(axis=1)
    return ha_df

def load_google_sheet_text(sheet_id, tab_name="BandSetup", cell_range="B14:B17"):
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
    worksheet = gc.open_by_key(sheet_id).worksheet(tab_name)
    cells = worksheet.get(cell_range)
    lines = [row[0] for row in cells if row and row[0].strip()]
    return lines

def load_csv():
    return pd.read_csv("data/bands.csv")

def render_chart_from_row(row, eth_price=None):
    band_label = row["Label"]
    band_min = row["Min"]
    band_max = row["Max"]
    band_mid = (band_min + band_max) / 2

    dd_levels = [(level, row[level]) for level in ["Down5", "Down10", "Down15"]]

    df = fetch_eth_candles()
    df.set_index("timestamp", inplace=True)
    ha_df = compute_heikin_ashi(df)
    ha_plot_df = ha_df[["open", "high", "low", "close"]].copy()
    ha_plot_df.index.name = "Date"

    ap_lines = [
        mpf.make_addplot([band_min] * len(ha_plot_df), color='orange', linestyle='--'),
        mpf.make_addplot([band_max] * len(ha_plot_df), color='green', linestyle='--')
    ]

    if eth_price:
        ap_lines.append(mpf.make_addplot([eth_price] * len(ha_plot_df), color='red'))

    fig_mpf, ax_mpf = mpf.plot(
        ha_plot_df,
        type='candle',
        style='charles',
        ylabel="Price",
        title=f"{band_label} Range (Heikin-Ashi)",
        addplot=ap_lines,
        figsize=(10, 5),
        returnfig=True
    )

    if eth_price and band_min <= eth_price <= band_max:
        ax_mpf[0].axhspan(band_min, band_max, color='green', alpha=0.2)

    st.pyplot(fig_mpf)

    fig, ax2 = plt.subplots(figsize=(10, 3))
    for label, price in dd_levels:
        ax2.axhline(price, linestyle="--", label=f"{label} = {int(price)}", color="skyblue")
    ax2.set_title(f"{band_label} Drawdowns")
    ax2.set_ylabel("Price")
    ax2.legend()
    st.pyplot(fig)

def render_charts(input_text):
    lines = input_text.strip().split("\n")
    band_line = lines[0]
    dd_lines = lines[1:]

    try:
        parts = {}
        band_label = band_line.split("|")[0].strip() if "|" in band_line else "Band"

        for kv in band_line.split("|"):
            if "=" in kv:
                key, val = kv.split("=")
                key = key.strip()
                val = val.strip().replace("%", "")
                parts[key] = float(val)

        band_min = parts["Min"]
        band_max = parts["Max"]
        band_mid = (band_min + band_max) / 2

        dd_levels = []
        for line in dd_lines:
            for kv in line.split("|"):
                if "Down" in kv and "=" in kv:
                    label, val = kv.split("=")
                    dd_levels.append((label.strip(), float(val.strip())))
                    break

        df = fetch_eth_candles()
        df.set_index("timestamp", inplace=True)
        ha_df = compute_heikin_ashi(df)
        ha_plot_df = ha_df[["open", "high", "low", "close"]].copy()
        ha_plot_df.index.name = "Date"

        ap_lines = [
            mpf.make_addplot([band_min] * len(ha_plot_df), color='orange', linestyle='--'),
            mpf.make_addplot([band_max] * len(ha_plot_df), color='green', linestyle='--')
        ]

        fig_mpf, ax_mpf = mpf.plot(
            ha_plot_df,
            type='candle',
            style='charles',
            ylabel="Price",
            title=f"{band_label} Range (Heikin-Ashi)",
            addplot=ap_lines,
            figsize=(10, 5),
            returnfig=True
        )

        ax_mpf[0].text(
            0.5,
            band_mid,
            band_line.strip(),
            transform=ax_mpf[0].get_yaxis_transform(),
            ha="center",
            va="center",
            color="red",
            fontsize=10,
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.7)
        )

        st.pyplot(fig_mpf)

        fig, ax2 = plt.subplots(figsize=(10, 3))
        for label, price in dd_levels:
            ax2.axhline(price, linestyle="--", label=f"{label} = {int(price)}", color="skyblue")
        ax2.set_title(f"{band_label} Drawdowns")
        ax2.set_ylabel("Price")
        ax2.legend()
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Failed to parse data or generate chart: {e}")

# ---- MAIN LOGIC ----
mode = st.radio("Data Source Mode", ["Manual", "From Google Sheet", "From CSV"])

auto_refresh = st.checkbox("Auto-refresh ETH price every 30 sec")
if auto_refresh:
    st.experimental_rerun()

eth_price = st.session_state.get("eth_price", fetch_eth_spot())
if eth_price:
    st.markdown(f"**Latest ETH Price:** ${eth_price:,.2f}")
else:
    st.error("Failed to fetch ETH price data.")

if mode == "Manual":
    st.subheader("Paste Band Data")
    band_input = st.text_area("Band Data Input", height=150)
    if st.button("Submit Band Info") and band_input:
        st.session_state.band_input = band_input.strip()
    if "band_input" in st.session_state:
        render_charts(st.session_state["band_input"])

elif mode == "From Google Sheet":
    sheet_id = "1lYMzXhF_bP1cCFLyHUmXHCZv4WbAHh2QwFvD-AdhAQY"
    tab_name = "BandSetup"

    band_option = st.selectbox(
        "Select Band to Load from Sheet",
        ["Band 1", "Band 2", "Band 3", "Band 4"]
    )

    band_ranges = {
        "Band 1": "B14:B17",
        "Band 2": "B18:B21",
        "Band 3": "B22:B25",
        "Band 4": "B26:B29"
    }

    try:
        cell_range = band_ranges[band_option]
        lines = load_google_sheet_text(sheet_id, tab_name, cell_range)
        band_text = "\n".join(lines)
        st.text_area("Band Data Pulled from Sheet", band_text, height=150)
        if band_text:
            render_charts(band_text)
    except Exception as e:
        st.error(f"Failed to load sheet: {e}")
        st.info("Falling back to manual input:")
        band_input = st.text_area("Paste Band Data", height=150)
        if st.button("Submit Band Info") and band_input:
            render_charts(band_input.strip())

elif mode == "From CSV":
    df_bands = load_csv()
    if not df_bands.empty:
        for _, row in df_bands.iterrows():
            render_chart_from_row(row, eth_price)
