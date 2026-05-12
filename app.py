import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from flashalpha import FlashAlpha

st.set_page_config(page_title="FlashAlpha GEX - Cross Reference", layout="wide")

st.title("🔌 FlashAlpha GEX Dashboard")
st.markdown("**Compare FlashAlpha results with our calculations**")

# API Key
api_key = st.secrets.get("FLASHALPHA_KEY")
if not api_key:
    st.error("⚠️ Add FLASHALPHA_KEY in Streamlit Secrets")
    st.stop()

fa = FlashAlpha(api_key)

# Ticker and expiration
col1, col2 = st.columns(2)
with col1:
    ticker = st.text_input("**Ticker**", value="SPX").upper().strip()
with col2:
    expiration = st.text_input("**Expiration (YYYY-MM-DD)**", value="2026-05-15")

st.caption(f"📅 Analyzing: {ticker} | Expiration: {expiration} | Uses 1 of 5 daily requests")

if st.button("📊 Load from FlashAlpha", type="primary"):
    with st.spinner(f"Fetching {ticker} from FlashAlpha..."):
        try:
            gex_data = fa.gex(ticker, expiration=expiration)
            
            # Extract key levels
            net_gex = gex_data.get('net_gex', 0) / 1_000_000_000
            gamma_flip = gex_data.get('gamma_flip')
            spot = gex_data.get('spot_price') or gex_data.get('underlying_price')
            call_wall = gex_data.get('call_wall')
            put_wall = gex_data.get('put_wall')
            zero_gamma = gex_data.get('zero_gamma')
            
            gex_by_strike = gex_data.get('gex_by_strike', {})
            if isinstance(gex_by_strike, list):
                gex_dict = {item['strike']: item['net_gex'] for item in gex_by_strike}
                gex_by_strike = pd.Series(gex_dict)
            elif isinstance(gex_by_strike, dict):
                gex_by_strike = pd.Series(gex_by_strike)
            
            # Display FlashAlpha Results
            st.markdown("### 🔌 FlashAlpha Results")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Net GEX", f"${net_gex:,.2f}B", 
                         delta="Positive = Stabilizing" if net_gex > 0 else "Negative = Volatile")
            with col2:
                st.metric("Call Wall", f"{call_wall:.0f}" if call_wall else "N/A")
            with col3:
                st.metric("Put Wall", f"{put_wall:.0f}" if put_wall else "N/A")
            with col4:
                st.metric("Gamma Flip", f"{gamma_flip:.0f}" if gamma_flip else "N/A")
            with col5:
                st.metric("Zero Gamma", f"{zero_gamma:.0f}" if zero_gamma else "N/A")
            
            # Horizontal GEX Chart
            st.markdown("### 📈 GEX Profile (FlashAlpha)")
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=gex_by_strike.values,
                y=gex_by_strike.index,
                orientation='h',
                marker_color=['#00d26a' if val > 0 else '#ff4757' for val in gex_by_strike.values],
                opacity=0.9,
                hovertemplate='Strike: %{y}<br>GEX: %{x:,.0f}<extra></extra>'
            ))
            
            if spot:
                fig.add_hline(y=spot, line_dash="dash", line_color="#ffd93d", line_width=3,
                             annotation_text=f"CURRENT ({spot:.0f})", annotation_position="right",
                             annotation_font_color="#ffd93d", annotation_font_size=12)
            if gamma_flip:
                fig.add_hline(y=gamma_flip, line_dash="dot", line_color="#ffffff", line_width=2.5,
                             annotation_text=f"GAMMA FLIP ({gamma_flip:.0f})", annotation_position="left",
                             annotation_font_color="#ffffff", annotation_font_size=11)
            if call_wall:
                fig.add_hline(y=call_wall, line_dash="solid", line_color="#00d26a", line_width=2,
                             annotation_text=f"CALL WALL ({call_wall:.0f})", annotation_position="right",
                             annotation_font_color="#00d26a", annotation_font_size=10)
            if put_wall:
                fig.add_hline(y=put_wall, line_dash="solid", line_color="#ff4757", line_width=2,
                             annotation_text=f"PUT WALL ({put_wall:.0f})", annotation_position="left",
                             annotation_font_color="#ff4757", annotation_font_size=10)
            
            fig.add_vline(x=0, line_dash="solid", line_color="#4a5568", line_width=1)
            
            # Auto-zoom
            strikes_with_gex = gex_by_strike[abs(gex_by_strike) > 0.001 * abs(gex_by_strike).max()].index
            if len(strikes_with_gex) > 0:
                fig.update_yaxes(range=[strikes_with_gex.min() - 2, strikes_with_gex.max() + 2])
            
            fig.update_layout(
                template="plotly_dark",
                height=700,
                margin=dict(l=80, r=40, t=20, b=40),
                xaxis_title="GEX ($ notional per 1% move)",
                yaxis_title="Strike Price",
                showlegend=False,
                hovermode="closest"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.success(f"✅ FlashAlpha data loaded! (1/5 requests used today)")
            
            # Comparison section
            st.markdown("---")
            st.markdown("### 🔄 Cross-Reference Section")
            st.info("💡 Upload the same CSV to the other dashboard and compare the key levels side by side!")
            
            # Raw data
            with st.expander("📋 Raw FlashAlpha Data"):
                st.json(gex_data)
            
        except Exception as e:
            st.error(f"Error: {e}")
            st.info("💡 Tip: Make sure the expiration date is valid for this ticker. Free tier supports single-expiry GEX only.")

else:
    st.info("👆 Click 'Load from FlashAlpha' to fetch data (uses 1 of 5 daily requests)")
    st.caption(f"Fixed expiration: May 15, 2026 (this Friday) | Change in the field above if needed")
