import streamlit as st
import requests
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Optional: Lock Critical UI Elements (do not remove)
st.markdown("<h2>ETH Liquidity Band Dashboard</h2>", unsafe_allow_html=True)

# Session State Initialization
if "eth_price" not in st.session_state:
    st.session_state.eth_price = ""

if "band_data" not in st.session_state:
    st.session_state.band_data = ""

# --- Price Fetching ---
def fetch_eth_price():
    url = "https://api.dexscreener.com/latest/dex/pairs/ethereum/0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
    try:
        res = requests.get(url)
        data = res.json()
        return round(float(data["pair"]["priceUsd"]), 2)
    except Exception as e:
        st.warning(f"Failed to fetch ETH price: {e}")
        return None

# --- UI Elements ---
st.subheader("1. Refresh ETH Price")
if st.button("🔄 Refresh ETH Price"):
    price = fetch_eth_price()
    if price:
        st.session_state.eth_price = price

if st.session_state.eth_price:
    st.write(f"**Latest ETH Price:** ${st.session_state.eth_price}")

st.markdown("---")

st.subheader("2. Paste Band Data")
st.session_state.band_data = st.text_area("Paste band and drawdown data below:", st.session_state.band_data, height=250)

if st.button("Submit Band Info"):
    st.session_state.submitted_text = st.session_state.band_data

st.markdown("---")

# --- Parsing & Chart Rendering ---
def parse_data_block(block):
    lines = block.strip().split("\n")
    band_line = lines[0]
    drawdowns = lines[1:]

    # Extract band range info
    parts = band_line.split("|")
    label = parts[0].strip()
    min_price = float(parts[1].split("=")[1])
    max_price = float(parts[2].split("=")[1])

    # Extract drawdown levels
    dd_lines = [l for l in drawdowns if l.strip() and "% Down" in l]
    dd_data = []
    for line in dd_lines:
        tokens = line.split("|")
        level = tokens[0].strip()
        level_price = float(tokens[0].split("=")[1])
        liq_price = float(tokens[1].split("=")[1])
        dist = float(tokens[2].split("=")[1])
        liq_drop = float(tokens[3].split("=")[1])
        dd_data.append((level, level_price, liq_price, dist, liq_drop))

    return label, min_price, max_price, dd_data

def render_band_chart(label, min_p, max_p):
    st.write(f"**{label} Range Chart**")
    eth = st.session_state.eth_price
    fig, ax = plt.subplots()
    ax.axhline(y=min_p, color='orange', linestyle='--', label='Min')
    ax.axhline(y=max_p, color='green', linestyle='--', label='Max')
    if eth and min_p <= eth <= max_p:
        ax.axhline(y=eth, color='blue', linewidth=2, label='ETH Price')
    ax.set_ylim(min_p - 200, max_p + 200)
    ax.set_title(f"{label} Range")
    ax.set_ylabel("Price")
    ax.legend()
    st.pyplot(fig)

def render_drawdown_chart(label, drawdowns):
    st.write(f"**{label} Drawdowns Chart**")
    fig, ax = plt.subplots()
    for level, price, _, _, _ in drawdowns:
        ax.axhline(y=price, linestyle='--', label=level)
    ax.set_title(f"{label} Drawdowns")
    ax.set_ylabel("Price")
    ax.legend()
    st.pyplot(fig)

# Trigger render if data submitted
if st.session_state.get("submitted_text"):
    blocks = st.session_state.submitted_text.strip().split("\n\n")
    for block in blocks:
        label, min_p, max_p, drawdowns = parse_data_block(block)
        render_band_chart(label, min_p, max_p)
        render_drawdown_chart(label, drawdowns)
        st.markdown("---")
