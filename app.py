import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from flashalpha import FlashAlpha
from datetime import datetime

st.set_page_config(page_title="My Live GEX Dashboard", layout="wide")
st.title("🚀 My Live GEX Dashboard")
st.markdown("**Real-time Gamma Exposure with Expiration Dropdown**")

# API Key from secrets
api_key = st.secrets.get("FLASHALPHA_KEY")
if not api_key:
    st.error("Please add your FlashAlpha API key in Streamlit Secrets")
    st.stop()

fa = FlashAlpha(api_key)

# Ticker input
ticker = st.text_input("Enter ticker (SPX, SPY, AAPL, TSLA, etc.)", value="SPX").upper().strip()

# Session state to remember expirations
if "expirations" not in st.session_state:
    st.session_state.expirations = None

# Load expirations button
if st.button("🔄 Load Available Expirations", type="secondary"):
    with st.spinner(f"Fetching expirations for {ticker}..."):
        try:
            options_data = fa.options(ticker)
            expirations = sorted(options_data.get("expirations", []))
            st.session_state.expirations = expirations
            st.success(f"Found {len(expirations)} expirations for {ticker}")
        except Exception as e:
            st.error(f"Could not load expirations: {e}")

# Expiration dropdown
if st.session_state.expirations:
    selected_expiration = st.selectbox(
        "Select Expiration Date",
        options=st.session_state.expirations,
        index=0
    )
else:
    selected_expiration = st.text_input(
        "Expiration date (YYYY-MM-DD)",
        value=datetime.now().strftime("%Y-%m-%d")
    )

# Load GEX button
if st.button("📊 Load GEX Data", type="primary"):
    with st.spinner(f"Fetching GEX for {ticker} on {selected_expiration}..."):
        try:
            gex_data = fa.gex(ticker, expiration=selected_expiration)

            net_gex = gex_data.get('net_gex', 0) / 1_000_000_000
            gamma_flip = gex_data.get('gamma_flip')
            spot = gex_data.get('spot_price') or gex_data.get('underlying_price')

            col1, col2, col3 = st.columns(3)
            col1.metric("Net GEX", f"${net_gex:,.2f}B",
                        delta="Positive = Stabilizing" if net_gex > 0 else "Negative = Volatile")
            col2.metric("Gamma Flip", f"{gamma_flip:.0f}" if gamma_flip else "N/A")
            col3.metric("Current Price", f"{spot:.2f}" if spot else "N/A")
            col3.caption(f"Expiry: {selected_expiration}")

            # Chart
            gex_by_strike = gex_data.get('gex_by_strike', {})
            if gex_by_strike:
                strikes = list(gex_by_strike.keys())
                values = list(gex_by_strike.values())

                fig = plt.figure(figsize=(14, 7))
                colors = ['green' if v > 0 else 'red' for v in values]
                plt.bar(strikes, values, width=8, color=colors, alpha=0.85)
                plt.axvline(spot, color='yellow', linewidth=3, label='Current Price')
                if gamma_flip:
                    plt.axvline(gamma_flip, color='white', linestyle='--', linewidth=2.5, label=f'Gamma Flip')
                plt.title(f'GEX Profile — {ticker} | {selected_expiration} | Net GEX ${net_gex:,.2f}B')
                plt.xlabel('Strike Price')
                plt.ylabel('GEX ($ notional per 1% move)')
                plt.legend()
                plt.grid(True, alpha=0.3)
                st.pyplot(fig)

            st.success(f"✅ {ticker} {selected_expiration} loaded!")

        except Exception as e:
            st.error(f"Error: {e}")

st.caption("Free tier: 5 requests/day • 'Load Expirations' + 'Load GEX' each count as calls")
