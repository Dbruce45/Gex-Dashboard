import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from flashalpha import FlashAlpha
from datetime import datetime

st.set_page_config(page_title="My Live GEX Dashboard", layout="wide")
st.title("🚀 My Live GEX Dashboard")
st.markdown("**Real-time Gamma Exposure with Expiration Dropdown**")

# API Key
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

col1, col2 = st.columns([3, 1])

with col1:
    if st.button("🔄 Load Available Expirations", type="secondary"):
        with st.spinner(f"Fetching expirations for {ticker}..."):
            try:
                # This gets the full list of expiration dates
                options_data = fa.options(ticker)          # ← this is the key call
                expirations = sorted(options_data.get("expirations", []))
                st.session_state.expirations = expirations
                st.success(f"Found {len(expirations)} expirations for {ticker}")
            except Exception as e:
                st.error(f"Could not load expirations: {e}")

# Expiration dropdown (only shows after loading)
if st.session_state.expirations:
    selected_expiration = st.selectbox(
        "Select Expiration Date",
        options=st.session_state.expirations,
        index=0  # default to the soonest
    )
else:
    selected_expiration = st.text_input("Expiration date
