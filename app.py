import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="My GEX Dashboard", layout="wide")
st.title("🚀 My Personal GEX Dashboard")
st.markdown("**Supports SPX + stocks/ETFs (SPY, QQQ, AAPL, TSLA, etc.)**")

ticker = st.text_input("Enter Ticker", value="SPX").upper().strip()

st.caption(f"📥 CBOE Link → [Open {ticker} Page](https://www.cboe.com/delayed_quotes/{ticker.lower()}/quote_table/)")

uploaded_file = st.file_uploader(f"Upload {ticker} CSV from CBOE", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, skiprows=2)
    
    st.write("**Columns found in CSV:**", list(df.columns))
    
    # === SUPER ROBUST COLUMN DETECTION ===
    # Standardize Strike column
    strike_col = next((col for col in df.columns if 'strike' in col.lower()), None)
    if not strike_col:
        st.error("Could not find Strike column. Make sure you downloaded the full options chain.")
        st.stop()
    df = df.dropna(subset=[strike_col])
    df = df.rename(columns={strike_col: 'Strike'})

    # Current price
    current_price = st.number_input("Current Price", value=7412.84, step=0.01)

    # Try multiple possible column name patterns
    call_gamma_col = None
    put_gamma_col = None
    call_oi_col = None
    put_oi_col = None

    cols = [c.lower() for c in df.columns]

    # Pattern 1: SPX style (Gamma / Gamma.1)
    if 'gamma' in cols and 'gamma.1' in cols:
        call_gamma_col = 'Gamma'
        put_gamma_col = 'Gamma.1'
        call_oi_col = 'Open Interest'
        put_oi_col = 'Open Interest.1'

    # Pattern 2: Stock/ETF style (Call Gamma / Put Gamma)
    elif any('call gamma' in c for c in df.columns) and any('put gamma' in c for c in df.columns):
        call_gamma_col = next(c for c in df.columns if 'call gamma' in c.lower())
        put_gamma_col = next(c for c in df.columns if 'put gamma' in c.lower())
        call_oi_col = next(c for c in df.columns if 'call open interest' in c.lower())
        put_oi_col = next(c for c in df.columns if 'put open interest' in c.lower())

    # Pattern 3: Fallback broad search
    else:
        for col in df.columns:
            cl = col.lower()
            if 'gamma' in cl and 'call' in cl:
                call_gamma_col = col
            elif 'gamma' in cl and 'put' in cl:
                put_gamma_col = col
            elif 'open interest' in cl and 'call' in cl:
                call_oi_col = col
            elif 'open interest' in cl and 'put' in cl:
                put_oi_col = col

    if not call_gamma_col or not put_gamma_col:
        st.error("Could not detect Gamma columns. Please reply with the 'Columns found' list above.")
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

    # Display
    col1, col2, col3 = st.columns(3)
    col1.metric("Net GEX", f"${net_gex:,.2f}B", 
                delta="Positive = Stabilizing" if net_gex > 0 else "Negative = Volatile")
    col2.metric("Gamma Flip", f"{gamma_flip:.0f}")
    col3.metric("Current Price", f"{current_price:.2f}")

    # Chart
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
