import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="My GEX Dashboard", layout="wide")
st.title("🚀 My Personal GEX Indicator Dashboard")
st.markdown("**Daily SPX GEX Dashboard** — Upload fresh CBOE data below")

uploaded_file = st.file_uploader("Upload today's SPX_quotedata.csv (from CBOE)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, skiprows=2)
    df = df.dropna(subset=['Strike'])

    current_spot_price = st.number_input("Current SPX Price", value=7412.84, step=0.01)

    # Calculate GEX
    df['Call_GEX'] = df['Gamma'] * df['Open Interest'] * 100 * (current_spot_price ** 2) * 0.01
    df['Put_GEX']  = df['Gamma.1'] * df['Open Interest.1'] * 100 * (current_spot_price ** 2) * 0.01 * (-1)

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
    col3.metric("Current SPX", f"{current_spot_price}")

    fig = plt.figure(figsize=(14, 7))
    colors = ['green' if x > 0 else 'red' for x in gex_by_strike.values]
    plt.bar(gex_by_strike.index, gex_by_strike.values, width=8, color=colors, alpha=0.85)
    plt.axvline(current_spot_price, color='yellow', linewidth=3, label='Current SPX Price')
    plt.axvline(gamma_flip, color='white', linestyle='--', linewidth=2.5, label=f'Gamma Flip ({gamma_flip:.0f})')
    plt.title(f'GEX Profile — Net GEX ${net_gex:,.2f}B', fontsize=16)
    plt.xlabel('Strike Price')
    plt.ylabel('GEX ($ notional per 1% move)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    st.pyplot(fig)

    st.success("✅ Dashboard updated!")
else:
    st.info("👆 Upload your SPX_quotedata.csv file to see the live GEX dashboard")
    st.caption("How to get the file: Go to https://www.cboe.com/delayed_quotes/spx/quote_table/ → Download CSV")
