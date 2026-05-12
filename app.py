import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from flashalpha import FlashAlpha

st.set_page_config(page_title="My Live GEX Dashboard", layout="wide")
st.title("🚀 My Live GEX Dashboard")
st.markdown("**Real-time Gamma Exposure for any ticker** (SPX, SPY, AAPL, TSLA, etc.)")

# Get API key from Streamlit secrets (secure)
api_key = st.secrets.get("FLASHALPHA_KEY")
if not api_key:
    st.error("⚠️ Please add your FlashAlpha API key in Streamlit secrets (see instructions below)")
    st.stop()

fa = FlashAlpha(api_key)

# Ticker input
ticker = st.text_input("Enter ticker (e.g. SPX, SPY, AAPL, TSLA)", value="SPX").upper().strip()

if st.button("Load GEX Data", type="primary"):
    with st.spinner(f"Fetching live GEX for {ticker}..."):
        try:
            gex_data = fa.gex(ticker)   # one API call

            net_gex = gex_data.get('net_gex', 0) / 1_000_000_000
            gamma_flip = gex_data.get('gamma_flip')
            spot = gex_data.get('spot_price') or gex_data.get('underlying_price')

            # Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Net GEX", f"${net_gex:,.2f}B",
                        delta="Positive = Stabilizing" if net_gex > 0 else "Negative = Volatile")
            col2.metric("Gamma Flip", f"{gamma_flip:.0f}" if gamma_flip else "N/A")
            col3.metric("Current Price", f"{spot:.2f}" if spot else "N/A")

            # Chart - GEX by strike
            gex_by_strike = gex_data.get('gex_by_strike', {})
            if gex_by_strike:
                strikes = list(gex_by_strike.keys())
                values = list(gex_by_strike.values())

                fig = plt.figure(figsize=(14, 7))
                colors = ['green' if v > 0 else 'red' for v in values]
                plt.bar(strikes, values, width=8, color=colors, alpha=0.85)
                plt.axvline(spot, color='yellow', linewidth=3, label='Current Price')
                if gamma_flip:
                    plt.axvline(gamma_flip, color='white', linestyle='--', linewidth=2.5, label=f'Gamma Flip ({gamma_flip:.0f})')
                plt.title(f'Live GEX Profile — {ticker} | Net GEX ${net_gex:,.2f}B')
                plt.xlabel('Strike Price')
                plt.ylabel('GEX ($ notional per 1% move)')
                plt.legend()
                plt.grid(True, alpha=0.3)
                st.pyplot(fig)
            else:
                st.warning("No GEX by strike data returned")

            st.success(f"✅ Loaded {ticker} successfully!")

        except Exception as e:
            st.error(f"Error fetching data: {e}")
            st.info("Note: Free tier = 5 calls/day. SPX/SPY may require paid plan.")

st.caption("💡 Free tier limit: 5 requests/day total. Change ticker or refresh = 1 request.")
