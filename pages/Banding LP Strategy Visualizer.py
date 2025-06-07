import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests

@st.cache_data(ttl=300)
def get_eth_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        response = requests.get(url)
        return response.json()['ethereum']['usd']
    except:
        return None

# Sidebar: ETH price controls
st.sidebar.title("Chart Controls")
refresh_mode = st.sidebar.radio("ETH Price Refresh", ["Manual", "Every 5 min"], index=0)
if refresh_mode == "Manual" and st.sidebar.button("Refresh ETH Price"):
    st.cache_data.clear()

eth_price = get_eth_price()
st.sidebar.markdown(f"**Current ETH Price:** ${eth_price}")

# Main UI
st.title("Banding LP Strategy Visualizer")
raw_input = st.text_area("Paste Band Chart Setups Text", height=300)

# Parse text input
bands = []
if raw_input:
    for line in raw_input.splitlines():
        if "|" in line and "Min" in line and "Max" in line and "Liq. Price" in line:
            parts = [p.strip() for p in line.split('|')]
            try:
                band_id = parts[0].split()[1] if parts[0].lower().startswith("band") else str(len(bands) + 1)
                band_min = float(parts[1].split('=')[-1].strip())
                band_max = float(parts[2].split('=')[-1].strip())
                liq_price = float(parts[3].split('=')[-1].strip())
                liq_drop = float(parts[4].split('=')[-1].replace('%', '').strip())
                bands.append({
                    "Band": f"Band {band_id}",
                    "Min": band_min,
                    "Max": band_max,
                    "Liq Price": liq_price,
                    "Liq Drop %": liq_drop
                })
            except Exception as e:
                st.warning(f"Could not parse: `{line}` — {e}")

# Plot chart
if bands:
    df = pd.DataFrame(bands)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axhline(eth_price, color='gray', linestyle='--', label=f"ETH Spot = ${eth_price:.2f}")

    for _, row in df.iterrows():
        ax.fill_betweenx([row['Min'], row['Max']], 0, 1, color='green', alpha=0.3, transform=ax.get_yaxis_transform())
        ax.text(0.5, (row['Min'] + row['Max']) / 2, 
                f"{row['Band']}\n${row['Min']} - ${row['Max']}\nLiq: ${row['Liq Price']} ({row['Liq Drop %']}%)",
                ha='center', va='center', fontsize=9, transform=ax.get_yaxis_transform())
        ax.axhline(row['Liq Price'], color='red', linestyle=':', linewidth=1)

    ax.set_ylim(min(df['Liq Price'].min(), eth_price) * 0.95, df['Max'].max() * 1.05)
    ax.set_title("Liquidity Bands and Liquidation Zones")
    ax.set_ylabel("ETH Price")
    ax.set_xticks([])
    ax.legend()
    st.pyplot(fig)
else:
    st.info("Paste your Band Chart Setups to visualize the ranges.")
