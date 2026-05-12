import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import StringIO

st.set_page_config(page_title="My GEX Dashboard", layout="wide")
st.title("🚀 My Personal GEX Dashboard")
st.markdown("**Supports SPX + SPY + other tickers**")

ticker = st.text_input("Enter Ticker", value="SPX").upper().strip()

st.caption(f"📥 CBOE Link → [Open {ticker} Page](https://www.cboe.com/delayed_quotes/{ticker.lower()}/quote_table/)")

uploaded_file = st.file_uploader(f"Upload {ticker} CSV from CBOE", type=["csv"])

if uploaded_file is not None:
    # Read the entire file as text to find the correct header row
    content = uploaded_file.getvalue().decode("utf-8")
    lines = content.splitlines()
    
    # Find the row that contains "Strike" (the real header)
    header_row = None
    for i, line in enumerate(lines):
        if "Strike" in line:
            header_row = i
            break
    
    if header_row is None:
        st.error("Could not find 'Strike' column. Make sure you downloaded the full options chain.")
        st.stop()
    
    st.write(f"✅ Detected data table starting at row {header_row}")
    
    # Read the CSV starting from the correct header row
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, skiprows=header_row, on_bad_lines='skip')
    
    st.write("**Columns found:**", list(df.columns))
    
    # Standardize Strike column
    strike_col = next((col for col in df.columns if 'strike' in str(col).lower()), None)
    if not strike_col:
        st.error("Could not find Strike column")
        st.stop()
    
    df = df.dropna(subset=[strike_col])
    df = df.rename(columns={strike_col: 'Strike'})

    current_price = st.number_input("Current Price", value=739.24, step=0.01)

    # Robust column detection for Gamma and Open Interest
    call_gamma_col = next((col for col in df.columns if 'gamma' in str(col).lower() and ('call' in str(col).lower() or col == 'Gamma')), None)
    put_gamma_col = next((col for col in df.columns if 'gamma' in str(col).lower() and ('put' in str(col).lower() or col == 'Gamma.1')), None)
    call_oi_col = next((col for col in df.columns if 'open interest' in str(col).lower() and ('call' in str(col).lower() or col == 'Open Interest')), None)
    put_oi_col = next((col for col in df.columns if 'open interest' in str(col).lower() and ('put' in str(col).lower() or col == 'Open Interest.1')), None)

    if not call_gamma_col or not put_gamma_col:
        st.error("Could not detect Gamma columns. Reply with the column list above.")
        st.stop()

    # Calculate GEX
    df['Call_GEX'] = df[call_gamma_col] * df[call_oi_col] * 100 * (current_price ** 2) * 0.01
    df['Put_GEX']  = df[put_gamma_col]  * df[put_oi_col]  * 100 * (current_price ** 2) * 0.01 * (-1)

    net_gex = (df['Call_GEX'].sum() + df['Put_GEX'].sum()) / 1_000_000_000

    # Gamma Flip
    gex_by_strike = df.groupby('Strike')[['Call_GEX', 'Put_GEX']].sum().sum(axis=1)
    sorted_gex = gex_by_strike.sort_index()
    sign_change = np.where(np.diff(np.sign(sorted_gex)))[0]
    if len(sign_change) > 0:
        idx = sign_change[0]
        gamma_flip = float(sorted_gex.index[idx] + (sorted_gex.index[idx+1] - sorted_gex.index[idx]) * 
                         (-sorted_gex.iloc[idx] / (sorted_gex.iloc[idx+1] - sorted_gex.iloc[idx])))
    else:
        gamma_flip = float(sorted_gex.idxmin() if sorted_gex.min() < 0 else sorted_gex.idxmax())

    col1, col2, col3 = st.columns(3)
    col1.metric("Net GEX", f"${net_gex:,.2f}B", 
                delta="Positive = Stabilizing" if net_gex > 0 else "Negative = Volatile")
    col2.metric("Gamma Flip", f"{gamma_flip:.0f}")
    col3.metric("Current Price", f"{current_price:.2f}")

    fig = plt.figure(figsize=(14, 7))
    colors = ['green' if x > 0 else 'red' for x in gex_by_strike.values]
    plt.bar(gex_by_strike.index, gex_by_strike.values, width=8, color=colors, alpha=0.85)
    plt.axvline(current_price, color='yellow', linewidth=3, label='Current Price')
    plt.axvline(gamma_flip, color='white', linestyle='--', linewidth=2.5, label=f'Gamma Flip ({gamma_flip:.0f})')
    plt.title(f'GEX Profile — {ticker} | Net GEX ${net_gex:,.2f}B')
    plt.xlabel('Strike Price')
    plt.ylabel('GEX ($ notional per 1% move)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    st.pyplot(fig)

    st.success(f"✅ {ticker} loaded successfully!")
else:
    st.info("Upload your CSV above")
