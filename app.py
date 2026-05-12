import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import yfinance as yf

st.set_page_config(page_title="My GEX Dashboard", layout="wide")
st.title("🚀 My Personal GEX Dashboard")
st.markdown("**Modern view • Call Wall + Put Wall • Auto Price Fetch**")

ticker = st.text_input("Enter Ticker", value="SPX").upper().strip()

st.caption(f"📥 [CBOE {ticker} Page](https://www.cboe.com/delayed_quotes/{ticker.lower()}/quote_table/)")

uploaded_file = st.file_uploader(f"Upload {ticker} CSV from CBOE", type=["csv"])

if uploaded_file is not None:
    # Auto-detect header row
    content = uploaded_file.getvalue().decode("utf-8")
    lines = content.splitlines()
    
    header_row = None
    for i, line in enumerate(lines):
        if "Strike" in line:
            header_row = i
            break
    
    if header_row is None:
        st.error("Could not find the options table.")
        st.stop()
    
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, skiprows=header_row, on_bad_lines='skip')

    strike_col = next((col for col in df.columns if 'strike' in str(col).lower()), None)
    df = df.dropna(subset=[strike_col])
    df = df.rename(columns={strike_col: 'Strike'})

    # === AUTO PRICE FETCH ===
    col_price1, col_price2 = st.columns([3, 1])
    with col_price1:
        current_price = st.number_input("Current Price", value=739.24, step=0.01)
    with col_price2:
        if st.button("🔄 Get Latest Price", help="Pulls latest price using yfinance"):
            with st.spinner("Fetching price..."):
                try:
                    # Try normal ticker, fallback for SPX
                    t = yf.Ticker(ticker if ticker != "SPX" else "^GSPC")
                    price = t.info.get('regularMarketPrice') or t.info.get('currentPrice') or t.history(period="1d")['Close'].iloc[-1]
                    current_price = float(price)
                    st.success(f"✅ Updated to ${current_price:.2f}")
                except Exception:
                    st.warning("Could not fetch price automatically. Enter manually.")

    # Column detection (same as before)
    call_gamma_col = next((col for col in df.columns if 'gamma' in str(col).lower() and ('call' in str(col).lower() or col == 'Gamma')), None)
    put_gamma_col = next((col for col in df.columns if 'gamma' in str(col).lower() and ('put' in str(col).lower() or col == 'Gamma.1')), None)
    call_oi_col = next((col for col in df.columns if 'open interest' in str(col).lower() and ('call' in str(col).lower() or col == 'Open Interest')), None)
    put_oi_col = next((col for col in df.columns if 'open interest' in str(col).lower() and ('put' in str(col).lower() or col == 'Open Interest.1')), None)

    if not call_gamma_col or not put_gamma_col:
        st.error("Could not detect Gamma columns.")
        st.stop()

    # Calculate GEX
    df['Call_GEX'] = df[call_gamma_col] * df[call_oi_col] * 100 * (current_price ** 2) * 0.01
    df['Put_GEX']  = df[put_gamma_col]  * df[put_oi_col]  * 100 * (current_price ** 2) * 0.01 * (-1)

    net_gex = (df['Call_GEX'].sum() + df['Put_GEX'].sum()) / 1_000_000_000

    gex_by_strike = df.groupby('Strike')[['Call_GEX', 'Put_GEX']].sum().sum(axis=1)

    call_wall = gex_by_strike[gex_by_strike > 0].idxmax() if any(gex_by_strike > 0) else None
    put_wall = gex_by_strike[gex_by_strike < 0].idxmin() if any(gex_by_strike < 0) else None

    sorted_gex = gex_by_strike.sort_index()
    sign_change = np.where(np.diff(np.sign(sorted_gex)))[0]
    if len(sign_change) > 0:
        idx = sign_change[0]
        gamma_flip = float(sorted_gex.index[idx] + (sorted_gex.index[idx+1] - sorted_gex.index[idx]) * 
                         (-sorted_gex.iloc[idx] / (sorted_gex.iloc[idx+1] - sorted_gex.iloc[idx])))
    else:
        gamma_flip = float(sorted_gex.idxmin() if sorted_gex.min() < 0 else sorted_gex.idxmax())

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Net GEX", f"${net_gex:,.2f}B", delta="Positive = Stabilizing" if net_gex > 0 else "Negative = Volatile")
    col2.metric("Call Wall", f"{call_wall:.0f}" if call_wall else "N/A")
    col3.metric("Put Wall", f"{put_wall:.0f}" if put_wall else "N/A")
    col4.metric("Gamma Flip", f"{gamma_flip:.0f}")

    # Clean Plotly Chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=gex_by_strike.index,
        y=gex_by_strike.values,
        marker_color=['green' if val > 0 else 'red' for val in gex_by_strike.values],
        opacity=0.85,
        name="GEX by Strike"
    ))

    fig.add_vline(x=current_price, line_dash="dash", line_color="yellow", annotation_text="CURRENT PRICE")
    fig.add_vline(x=gamma_flip, line_dash="dot", line_color="white", annotation_text=f"GAMMA FLIP ({gamma_flip:.0f})")

    if call_wall:
        fig.add_annotation(x=call_wall, y=gex_by_strike.max()*0.9, text="CALL WALL", showarrow=True, arrowhead=2)
    if put_wall:
        fig.add_annotation(x=put_wall, y=gex_by_strike.min()*0.9, text="PUT WALL", showarrow=True, arrowhead=2)

    fig.update_layout(
        title=f"GEX Profile — {ticker} | Net GEX ${net_gex:,.2f}B",
        xaxis_title="Strike Price",
        yaxis_title="GEX ($ notional per 1% move)",
        template="plotly_dark",
        height=650,
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.success(f"✅ {ticker} loaded!")
else:
    st.info("Upload your CSV above")
