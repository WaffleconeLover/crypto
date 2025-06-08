import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime as dt
import json
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(layout="wide")
st.title("ETH Liquidity Band Dashboard")

# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Settings")

eth_price_auto = st.sidebar.checkbox("Auto-refresh ETH price", value=True)
if not eth_price_auto:
    eth_price = st.sidebar.number_input("Manual ETH Price", value=2500.0)
else:
    eth_price = None  # Will be fetched live below

sheet_url = "https://docs.google.com/spreadsheets/d/1lYMzXhF_bP1cCFLyHUmXHCZv4WbAHh2QwFvD-AdhAQY/"
sheet_tab = "Banding"
sheet_range = "B14:B29"

# -----------------------------
# Functions
# -----------------------------

@st.cache_data(ttl=60)
def fetch_eth_price():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
        return response.json()["ethereum"]["usd"]
    except:
        return None

def load_google_sheet_text(sheet_id, tab_name="Banding", cell_range="B14:B29"):
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds_dict = json.loads(st.secrets["google_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    gc = gspread.authorize(creds)

    try:
        spreadsheet = gc.open_by_key(sheet_id)
        sheet_names = [ws.title for ws in spreadsheet.worksheets()]
        st.write("Available tabs:", sheet_names)  # Debugging output

        worksheet = spreadsheet.worksheet(tab_name)
        cells = worksheet.get(cell_range)
        lines = [row[0] for row in cells if row and row[0].strip()]
        return lines
    except Exception as e:
        st.error(f"Error loading sheet data: {e}")
        return []

def parse_line(line):
    try:
        parts = [float(x.strip()) for x in line.split(",")]
        if len(parts) == 5:
            return {
                "Date": parts[0],
                "Min": parts[1],
                "Max": parts[2],
                "Liq.": parts[3],
                "Liq. Limit": parts[4]
            }
    except:
        pass
    return None

def generate_chart(df, selected_date):
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(df["Date"], df["Min"], label="Min", linestyle="--")
    ax.plot(df["Date"], df["Max"], label="Max", linestyle="--")
    ax.plot(df["Date"], df["Liq."], label="Liq.", linestyle="-", marker="o")
    ax.plot(df["Date"], df["Liq. Limit"], label="Liq. Limit", linestyle="-", marker="x")

    if selected_date in df["Date"].values:
        selected_row = df[df["Date"] == selected_date].iloc[0]
        mid = (selected_row["Min"] + selected_row["Max"]) / 2
        ax.annotate(f"{selected_date}", xy=(selected_date, mid), xytext=(0, 10),
                    textcoords='offset points', ha='center', color='red', fontsize=12)

    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%d'))
    ax.set_xlabel("Date")
    ax.set_ylabel("ETH Price")
    ax.legend()
    ax.grid(True)
    fig.autofmt_xdate()
    st.pyplot(fig)

# -----------------------------
# ETH Price
# -----------------------------
if eth_price_auto:
    price = fetch_eth_price()
    if price:
        st.metric("ETH Price (Live)", f"${price:,.2f}")
    else:
        st.warning("Failed to fetch ETH price")
        price = None
else:
    price = eth_price
    st.metric("ETH Price (Manual)", f"${price:,.2f}")

# -----------------------------
# Load Sheet Data
# -----------------------------
sheet_id = sheet_url.split("/d/")[1].split("/")[0]
lines = load_google_sheet_text(sheet_id, tab_name=sheet_tab, cell_range=sheet_range)

parsed = [parse_line(line) for line in lines if parse_line(line)]
df = pd.DataFrame(parsed)

if not df.empty:
    df["Date"] = pd.to_datetime(df["Date"], origin="1899-12-30", unit="D")
    selected_date = st.selectbox("Select Date", df["Date"].dt.strftime('%Y-%m-%d'))

    selected_date_parsed = pd.to_datetime(selected_date)
    generate_chart(df, selected_date_parsed)
else:
    st.warning("No data to display.")
