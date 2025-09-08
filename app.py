import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
import base64
from math import erf, sqrt as msqrt

# Page configuration
st.set_page_config(
    page_title="WhatIfWealth - Backtesting Portfolio",
    page_icon="📈",
    layout="wide"
)

# Title and description
st.title("📈 WhatIfWealth - סימולציית השקעה רטרואקטיבית")
st.markdown("""
אפליקציה לניתוח ביצועי תיק השקעות היסטורי עם השוואה ל-benchmarks
""")

# Sidebar for input
st.sidebar.header("הגדרות תיק השקעות")

# Date inputs
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input(
        "תאריך התחלה",
        value=datetime.now() - timedelta(days=365),
        max_value=datetime.now()
    )
with col2:
    end_date = st.date_input(
        "תאריך סיום",
        value=datetime.now(),
        max_value=datetime.now()
    )

# Portfolio input
st.sidebar.subheader("תיק השקעות")
st.sidebar.markdown("הכנס מניות ואחוזי השקעה (סה״כ צריך להיות 100%)")

# Sample portfolio for demonstration
sample_portfolio = {
    "AAPL": 30,
    "MSFT": 25,
    "GOOGL": 20,
    "AMZN": 15,
    "TSLA": 10
}

# Portfolio input interface
portfolio = {}
total_percentage = 0

# Check if optimized portfolio exists in session state
if 'optimized_portfolio' in st.session_state:
    sample_portfolio = st.session_state.optimized_portfolio
    # Clear the session state after using it
    del st.session_state.optimized_portfolio
else:
    sample_portfolio = {
        "QQQ": 30,
        "MAGS": 10,
        "XAR": 20,
        "VXUS": 15,
        "SPY": 10,
        "XLV": 15
    }

for i, (ticker, percentage) in enumerate(sample_portfolio.items()):
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        new_ticker = st.text_input(f"מניה {i+1}", value=ticker, key=f"ticker_{i}")
    with col2:
        new_percentage = st.number_input(f"אחוז {i+1}", value=percentage, min_value=0, max_value=100, key=f"perc_{i}")
    
    if new_ticker and new_percentage > 0:
        portfolio[new_ticker.upper()] = new_percentage
        total_percentage += new_percentage

# Add more stocks
num_additional = st.sidebar.number_input("מספר מניות נוספות", min_value=0, max_value=10, value=0)

for i in range(num_additional):
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        ticker = st.text_input(f"מניה נוספת {i+1}", key=f"add_ticker_{i}")
    with col2:
        percentage = st.number_input(f"אחוז {i+1}", min_value=0, max_value=100, key=f"add_perc_{i}")
    
    if ticker and percentage > 0:
        portfolio[ticker.upper()] = percentage
        total_percentage += percentage

# Display total percentage
st.sidebar.markdown(f"**סה״כ אחוזים: {total_percentage}%**")

if total_percentage != 100:
    st.sidebar.warning(f"סה״כ האחוזים צריך להיות 100%. כרגע: {total_percentage}%")

# Benchmark selection
st.sidebar.subheader("Benchmark להשוואה")
benchmark = st.sidebar.selectbox(
    "בחר benchmark",
    ["SPY", "QQQ", "IWM", "TLT", "GLD", "BTC-USD"],
    help="SPY = S&P 500, QQQ = NASDAQ, IWM = Russell 2000, TLT = Treasury Bonds, GLD = Gold, BTC-USD = Bitcoin"
)

# Safety slider: user's confidence not to lose money in alternative portfolios
st.sidebar.subheader("רמת ביטחון שלא אפסיד כסף (תיקים חלופיים)")
safety_level = st.sidebar.slider(
    "safety",
    min_value=0,
    max_value=100,
    value=50,
    help="0 = לא אכפת לי להפסיד, 100 = ביטחון מלא שלא אפסיד"
)

# Lock specific tickers for alternative suggestions
st.sidebar.subheader("נעילה: אל תשנה אחוזים במניות הנבחרות")
locked_tickers = st.sidebar.multiselect(
    "בחר מניות לנעילה",
    options=list(portfolio.keys()),
    help="המניות שנבחרו ישמרו על אחוז ההשקעה הנוכחי באופטימיזציה"
)

# Instructions
with st.expander("הוראות שימוש"):
    st.markdown("""
    ### איך להשתמש באפליקציה:
    
    1. **הגדר תאריכים**: בחר תאריך התחלה וסיום לניתוח
    2. **הכנס תיק השקעות**: הוסף מניות ואחוזי השקעה (סה״כ 100%)
    3. **בחר Benchmark**: בחר מדד להשוואה (SPY, QQQ, וכו׳)
    4. **הרץ ניתוח**: לחץ על כפתור "הרץ ניתוח"
    5. **הצע שילוב חדש**: לחץ על "הצע שילוב חדש" לקבלת אופטימיזציה
    6. **צפה בתוצאות**: גרפים, מדדי ביצוע, והשוואות
    7. **ייצא דוח**: הורד דוח PDF מפורט
    
    ### מדדי ביצוע:
    - **תשואה כוללת**: הרווח/הפסד הכולל בתקופה
    - **תשואה שנתית**: תנודתיות שנתית
    - **Sharpe Ratio**: יחס תשואה לסיכון
    - **Max Drawdown**: הירידה המקסימלית מהשיא
    
    ### אופטימיזציה:
    - ** נבדקים 5,000 שינויים אקראיים בתיק, ללא הוספת רכיבים חדשים
    - **Sharpe Ratio**: קריטריון ראשי (70%)
    - **תשואה כוללת**: קריטריון משני (30%)
    - **מניות זמינות**: תיק נוכחי + רכיבי benchmark
    """)


# Run analysis button
run_analysis = st.sidebar.button("הרץ ניתוח", type="primary")

# Suggest new combination button
suggest_combination = st.sidebar.button("הצע שילוב חדש", type="secondary")

if run_analysis and portfolio and total_percentage == 100:
    with st.spinner("מחשב ביצועי תיק..."):
        
        # Fetch historical data
        @st.cache_data
        def fetch_data(tickers, start, end):
            data = {}
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(start=start, end=end)
                    if not hist.empty:
                        data[ticker] = hist['Close']
                except Exception as e:
                    st.error(f"שגיאה בטעינת {ticker}: {e}")
            return data
        
        # Get portfolio and benchmark data
        portfolio_data = fetch_data(list(portfolio.keys()), start_date, end_date)
        benchmark_data = fetch_data([benchmark], start_date, end_date)
        
        if portfolio_data and benchmark_data:
            
            # Calculate portfolio returns
            portfolio_df = pd.DataFrame(portfolio_data)
            portfolio_df = portfolio_df.fillna(method='ffill')
            
            # Calculate weighted returns
            weights = np.array(list(portfolio.values())) / 100
            portfolio_returns = portfolio_df.pct_change().dropna()
            weighted_returns = (portfolio_returns * weights).sum(axis=1)
            
            # Calculate cumulative returns
            cumulative_returns = (1 + weighted_returns).cumprod()
            
            # Benchmark returns
            benchmark_returns = benchmark_data[benchmark].pct_change().dropna()
            benchmark_cumulative = (1 + benchmark_returns).cumprod()
            
            # Performance metrics
            total_return = (cumulative_returns.iloc[-1] - 1) * 100
            benchmark_total_return = (benchmark_cumulative.iloc[-1] - 1) * 100
            
            # Volatility (annualized)
            volatility = weighted_returns.std() * np.sqrt(252) * 100
            benchmark_volatility = benchmark_returns.std() * np.sqrt(252) * 100
            
            # Sharpe ratio (assuming risk-free rate of 2%)
            risk_free_rate = 0.02
            sharpe_ratio = (weighted_returns.mean() * 252 - risk_free_rate) / (weighted_returns.std() * np.sqrt(252))
            benchmark_sharpe = (benchmark_returns.mean() * 252 - risk_free_rate) / (benchmark_returns.std() * np.sqrt(252))
            
            # Maximum drawdown
            rolling_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdown.min() * 100
            
            benchmark_rolling_max = benchmark_cumulative.expanding().max()
            benchmark_drawdown = (benchmark_cumulative - benchmark_rolling_max) / benchmark_rolling_max
            benchmark_max_drawdown = benchmark_drawdown.min() * 100
            
            # Probability of not losing money over selected period
            log_returns_main = np.log1p(weighted_returns)
            trading_days_main = len(log_returns_main)
            mu_log_main = log_returns_main.mean()
            sigma_log_main = log_returns_main.std()
            if sigma_log_main == 0:
                p_no_loss_main = 1.0 if mu_log_main > 0 else 0.0
            else:
                mean_sum_main = mu_log_main * trading_days_main
                std_sum_main = sigma_log_main * np.sqrt(trading_days_main)
                z_main = (0 - mean_sum_main) / std_sum_main
                cdf_main = 0.5 * (1 + erf(z_main / msqrt(2)))
                p_no_loss_main = 1 - cdf_main
            
            # Display results
            st.header("📊 תוצאות הניתוח")
            
            # Performance comparison
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("תשואה כוללת", f"{total_return:.2f}%", f"{total_return - benchmark_total_return:.2f}%")
            
            with col2:
                st.metric("תשואה שנתית", f"{volatility:.2f}%", f"{volatility - benchmark_volatility:.2f}%")
            
            with col3:
                st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}", f"{sharpe_ratio - benchmark_sharpe:.2f}")
            
            with col4:
                st.metric("Max Drawdown", f"{max_drawdown:.2f}%", f"{max_drawdown - benchmark_max_drawdown:.2f}%")
            with col5:
                st.metric("סיכוי לא להפסיד", f"{p_no_loss_main*100:.1f}%")
            if p_no_loss_main * 100 < safety_level:
                st.warning(f"רמת הביטחון מחושבת ({p_no_loss_main*100:.1f}%) נמוכה מהסף שנבחר ({safety_level}%). שקול לשנות הקצאות או להפחית סיכון.")
            
            # Portfolio composition
            st.subheader("הרכב התיק")
            portfolio_df_display = pd.DataFrame({
                'מניה': list(portfolio.keys()),
                'אחוז השקעה': list(portfolio.values()),
                'תשואה כוללת': [((portfolio_df[ticker].iloc[-1] / portfolio_df[ticker].iloc[0]) - 1) * 100 
                                for ticker in portfolio.keys()]
            })
            st.dataframe(portfolio_df_display, use_container_width=True)
            
            # Performance chart
            st.subheader("גרף ביצועים")
            
            fig = go.Figure()
            
            # Portfolio line
            fig.add_trace(go.Scatter(
                x=cumulative_returns.index,
                y=cumulative_returns.values * 100,
                mode='lines',
                name='תיק השקעות',
                line=dict(color='blue', width=2)
            ))
            
            # Benchmark line
            fig.add_trace(go.Scatter(
                x=benchmark_cumulative.index,
                y=benchmark_cumulative.values * 100,
                mode='lines',
                name=f'Benchmark ({benchmark})',
                line=dict(color='red', width=2)
            ))
            
            fig.update_layout(
                title="השוואת ביצועים",
                xaxis_title="תאריך",
                yaxis_title="תשואה מצטברת (%)",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Drawdown chart
            st.subheader("גרף Drawdown")
            
            fig_dd = go.Figure()
            
            fig_dd.add_trace(go.Scatter(
                x=drawdown.index,
                y=drawdown.values * 100,
                mode='lines',
                name='תיק השקעות',
                fill='tonexty',
                line=dict(color='blue')
            ))
            
            fig_dd.add_trace(go.Scatter(
                x=benchmark_drawdown.index,
                y=benchmark_drawdown.values * 100,
                mode='lines',
                name=f'Benchmark ({benchmark})',
                fill='tonexty',
                line=dict(color='red')
            ))
            
            fig_dd.update_layout(
                title="Drawdown לאורך זמן",
                xaxis_title="תאריך",
                yaxis_title="Drawdown (%)",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_dd, use_container_width=True)
            
            # Detailed metrics table
            st.subheader("מדדי ביצוע מפורטים")
            
            metrics_df = pd.DataFrame({
                'מדד': ['תשואה כוללת', 'תשואה שנתית', 'Sharpe Ratio', 'Max Drawdown', 'Beta'],
                'תיק השקעות': [f"{total_return:.2f}%", f"{volatility:.2f}%", f"{sharpe_ratio:.2f}", f"{max_drawdown:.2f}%", "N/A"],
                f'Benchmark ({benchmark})': [f"{benchmark_total_return:.2f}%", f"{benchmark_volatility:.2f}%", f"{benchmark_sharpe:.2f}", f"{benchmark_max_drawdown:.2f}%", "1.00"],
                'הפרש': [f"{total_return - benchmark_total_return:.2f}%", f"{volatility - benchmark_volatility:.2f}%", f"{sharpe_ratio - benchmark_sharpe:.2f}", f"{max_drawdown - benchmark_max_drawdown:.2f}%", "N/A"]
            })
            
            st.dataframe(metrics_df, use_container_width=True)

            # Additional comparative analyses: 5, 10, 15, 20 years (portfolio vs benchmark)
            st.subheader("ניתוחים נוספים: השוואת תיק מול Benchmark (5/10/15/20 שנים)")
            compare_periods = {
                '5 שנים': 1260,
                '10 שנים': 2520,
                '15 שנים': 3780,
                '20 שנים': 5040
            }
            for label_ep, days_ep in compare_periods.items():
                ep_end = pd.Timestamp(end_date)
                ep_start = ep_end - pd.Timedelta(days=days_ep)
                # fetch data
                ep_portfolio_data = fetch_data(list(portfolio.keys()), ep_start, ep_end)
                ep_bench_data = fetch_data([benchmark], ep_start, ep_end)
                if not ep_portfolio_data or not ep_bench_data:
                    st.info(f"{label_ep}: אין מספיק נתונים לכל הרכיבים.")
                    continue
                # Portfolio metrics
                ep_df = pd.DataFrame(ep_portfolio_data).fillna(method='ffill')
                ep_returns = ep_df.pct_change().dropna()
                if ep_returns.empty:
                    st.info(f"{label_ep}: אין נתוני תשואות תקפים לתיק.")
                    continue
                ep_weights = np.array(list(portfolio.values())) / 100
                if ep_returns.shape[1] != len(ep_weights):
                    try:
                        ep_df_aligned = ep_df[list(portfolio.keys())]
                        ep_returns = ep_df_aligned.pct_change().dropna()
                    except Exception:
                        st.info(f"{label_ep}: אי התאמה בין משקולות לעמודות נתונים.")
                        continue
                ep_port_ret = (ep_returns * ep_weights).sum(axis=1)
                ep_cum = (1 + ep_port_ret).cumprod()
                ep_total_return = (ep_cum.iloc[-1] - 1) * 100
                ep_vol = ep_port_ret.std() * np.sqrt(252) * 100
                ep_sharpe = (ep_port_ret.mean() * 252 - risk_free_rate) / (ep_port_ret.std() * np.sqrt(252))
                ep_log = np.log1p(ep_port_ret)
                ep_t = len(ep_log)
                mu_ep = ep_log.mean()
                sig_ep = ep_log.std()
                if sig_ep == 0:
                    p_no_loss_ep = 1.0 if mu_ep > 0 else 0.0
                else:
                    mean_sum_ep = mu_ep * ep_t
                    std_sum_ep = sig_ep * np.sqrt(ep_t)
                    z_ep = (0 - mean_sum_ep) / std_sum_ep
                    cdf_ep = 0.5 * (1 + erf(z_ep / msqrt(2)))
                    p_no_loss_ep = 1 - cdf_ep
                # Benchmark metrics
                ep_bench_series = pd.Series(ep_bench_data[benchmark]).dropna()
                ep_bench_ret = ep_bench_series.pct_change().dropna()
                if ep_bench_ret.empty:
                    st.info(f"{label_ep}: אין נתוני תשואות תקפים ל-Benchmark.")
                    continue
                ep_bench_cum = (1 + ep_bench_ret).cumprod()
                ep_bench_total_return = (ep_bench_cum.iloc[-1] - 1) * 100
                ep_bench_vol = ep_bench_ret.std() * np.sqrt(252) * 100
                ep_bench_sharpe = (ep_bench_ret.mean() * 252 - risk_free_rate) / (ep_bench_ret.std() * np.sqrt(252))
                ep_bench_log = np.log1p(ep_bench_ret)
                ep_bt = len(ep_bench_log)
                mu_b = ep_bench_log.mean()
                sig_b = ep_bench_log.std()
                if sig_b == 0:
                    p_no_loss_bench = 1.0 if mu_b > 0 else 0.0
                else:
                    mean_sum_b = mu_b * ep_bt
                    std_sum_b = sig_b * np.sqrt(ep_bt)
                    z_b = (0 - mean_sum_b) / std_sum_b
                    cdf_b = 0.5 * (1 + erf(z_b / msqrt(2)))
                    p_no_loss_bench = 1 - cdf_b
                # Display side-by-side
                st.markdown(f"**{label_ep}**")
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1:
                    st.markdown("**מדד**")
                    st.write("תשואה כוללת")
                    st.write("Sharpe Ratio")
                    st.write("תנודתיות")
                    st.write("סיכוי לא להפסיד")
                with c2:
                    st.markdown("**תיק**")
                    st.write(f"{ep_total_return:.2f}%")
                    st.write(f"{ep_sharpe:.2f}")
                    st.write(f"{ep_vol:.2f}%")
                    st.write(f"{p_no_loss_ep*100:.1f}%")
                with c3:
                    st.markdown("**Benchmark**")
                    st.write(f"{ep_bench_total_return:.2f}%")
                    st.write(f"{ep_bench_sharpe:.2f}")
                    st.write(f"{ep_bench_vol:.2f}%")
                    st.write(f"{p_no_loss_bench*100:.1f}%")
                with c4:
                    st.markdown("**הפרש (תיק - Benchmark)**")
                    st.write(f"{ep_total_return - ep_bench_total_return:.2f}%")
                    st.write(f"{ep_sharpe - ep_bench_sharpe:.2f}")
                    st.write(f"{ep_vol - ep_bench_vol:.2f}%")
                    st.write(f"{(p_no_loss_ep - p_no_loss_bench)*100:.1f}%")
                with c5:
                    st.empty()
            
            # PDF Export
            st.subheader("ייצוא PDF")
            
            def generate_pdf():
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter)
                story = []
                
                # Title
                styles = getSampleStyleSheet()
                title = Paragraph("דוח ביצועי תיק השקעות - WhatIfWealth", styles['Title'])
                story.append(title)
                story.append(Spacer(1, 12))
                
                # Summary
                summary = Paragraph(f"""
                <b>סיכום:</b><br/>
                תאריך התחלה: {start_date}<br/>
                תאריך סיום: {end_date}<br/>
                תשואה כוללת: {total_return:.2f}%<br/>
                Benchmark: {benchmark} ({benchmark_total_return:.2f}%)<br/>
                """, styles['Normal'])
                story.append(summary)
                story.append(Spacer(1, 12))
                
                # Portfolio composition
                story.append(Paragraph("<b>הרכב התיק:</b>", styles['Heading2']))
                portfolio_data_for_table = [['מניה', 'אחוז השקעה', 'תשואה כוללת']]
                for ticker, weight in portfolio.items():
                    ticker_return = ((portfolio_df[ticker].iloc[-1] / portfolio_df[ticker].iloc[0]) - 1) * 100
                    portfolio_data_for_table.append([ticker, f"{weight}%", f"{ticker_return:.2f}%"])
                
                portfolio_table = Table(portfolio_data_for_table)
                portfolio_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(portfolio_table)
                story.append(Spacer(1, 12))
                
                # Performance metrics
                story.append(Paragraph("<b>מדדי ביצוע:</b>", styles['Heading2']))
                metrics_data_for_table = [['מדד', 'תיק השקעות', f'Benchmark ({benchmark})', 'הפרש']]
                metrics_data_for_table.extend([
                    ['תשואה כוללת', f"{total_return:.2f}%", f"{benchmark_total_return:.2f}%", f"{total_return - benchmark_total_return:.2f}%"],
                    ['תשואה שנתית', f"{volatility:.2f}%", f"{benchmark_volatility:.2f}%", f"{volatility - benchmark_volatility:.2f}%"],
                    ['Sharpe Ratio', f"{sharpe_ratio:.2f}", f"{benchmark_sharpe:.2f}", f"{sharpe_ratio - benchmark_sharpe:.2f}"],
                    ['Max Drawdown', f"{max_drawdown:.2f}%", f"{benchmark_max_drawdown:.2f}%", f"{max_drawdown - benchmark_max_drawdown:.2f}%"]
                ])
                
                metrics_table = Table(metrics_data_for_table)
                metrics_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(metrics_table)
                
                doc.build(story)
                buffer.seek(0)
                return buffer
            
            pdf_buffer = generate_pdf()
            st.download_button(
                label="הורד דוח PDF",
                data=pdf_buffer.getvalue(),
                file_name=f"portfolio_analysis_{start_date}_{end_date}.pdf",
                mime="application/pdf"
            )

elif run_analysis:
    if not portfolio:
        st.error("אנא הכנס לפחות מניה אחת")
    elif total_percentage != 100:
        st.error(f"סה״כ האחוזים צריך להיות 100%. כרגע: {total_percentage}%")

# Portfolio optimization section
if suggest_combination and portfolio and total_percentage == 100:
    with st.spinner("מחפש שילובים אופטימליים לתקופות שונות..."):
        periods = {
            '3 חודשים': 63,   # ~63 trading days
            '6 חודשים': 126,  # ~126 trading days
            '1 שנה': 252,     # ~252 trading days
            '2 שנים': 504,    # ~504 trading days
            '5 שנים': 1260,   # ~1260 trading days
            '10 שנים': 2520,  # ~2520 trading days
            '15 שנים': 3780   # ~3780 trading days
        }
        results = {}
        for label, days in periods.items():
            # Limit the date range for each period
            period_end = pd.Timestamp(end_date)
            period_start = period_end - pd.Timedelta(days=days)
            # Fetch data for user stocks only
            @st.cache_data
            def fetch_period_data(stocks, start, end):
                data = {}
                for stock in stocks:
                    try:
                        ticker = yf.Ticker(stock)
                        hist = ticker.history(start=start, end=end)
                        if not hist.empty:
                            data[stock] = hist['Close']
                    except Exception as e:
                        continue
                return data
            period_data = fetch_period_data(list(portfolio.keys()), period_start, period_end)
            if len(period_data) < 2:
                continue
            returns_df = pd.DataFrame(period_data).pct_change().dropna()
            best_score = -999
            best_portfolio = None
            best_metrics = None
            trading_days = len(returns_df)
            # Build baseline weights vector aligned to available columns and normalized to 100
            cols = list(returns_df.columns)
            baseline_raw = np.array([portfolio.get(sym, 0) for sym in cols], dtype=float)
            baseline_sum = baseline_raw.sum()
            if baseline_sum == 0:
                baseline_weights = np.zeros_like(baseline_raw)
            else:
                baseline_weights = baseline_raw / baseline_sum * 100
            # Build locking mask aligned to available columns
            locked_mask = np.array([1 if sym in locked_tickers else 0 for sym in cols], dtype=int)
            locked_weights = baseline_weights * locked_mask
            locked_total = locked_weights.sum()
            all_locked = int((locked_mask == 1).all())
            for i in range(5000):
                if all_locked:
                    # No suggestion possible if everything is locked
                    continue
                # Randomize only the unlocked portion and normalize to remaining budget
                rand = np.random.random(len(cols))
                rand = rand * (1 - locked_mask)  # zero for locked
                if rand.sum() == 0:
                    # if random produced zeros for all unlocked, try again
                    continue
                rand = rand / rand.sum() * max(0.0, 100.0 - locked_total)
                weights = locked_weights + rand
                portfolio_returns = (returns_df * (weights / 100)).sum(axis=1)
                risk_free_rate = 0.02
                sharpe = (portfolio_returns.mean() * 252 - risk_free_rate) / (portfolio_returns.std() * np.sqrt(252))
                total_return = ((1 + portfolio_returns).cumprod().iloc[-1] - 1) * 100
                volatility = portfolio_returns.std() * np.sqrt(252) * 100
                cumulative = (1 + portfolio_returns).cumprod()
                rolling_max = cumulative.expanding().max()
                drawdown = (cumulative - rolling_max) / rolling_max
                max_dd = drawdown.min() * 100
                # Estimate probability of not losing money over the period using normal approximation on log-returns
                log_returns = np.log1p(portfolio_returns)
                mu_log = log_returns.mean()
                sigma_log = log_returns.std()
                if sigma_log == 0:
                    p_no_loss = 1.0 if mu_log > 0 else 0.0
                else:
                    mean_sum = mu_log * trading_days
                    std_sum = sigma_log * np.sqrt(trading_days)
                    z = (0 - mean_sum) / std_sum
                    # Standard normal CDF via erf
                    cdf = 0.5 * (1 + erf(z / msqrt(2)))
                    p_no_loss = 1 - cdf
                # Filter by user-selected safety level
                if p_no_loss * 100 < safety_level:
                    continue
                # Enforce max 45% total change (L1 distance in percentage points)
                l1_change = float(np.abs(weights - baseline_weights).sum())
                if l1_change > 45:
                    continue
                # Score: 60% Sharpe, 40% total return
                score = sharpe * 0.6 + (total_return / 100) * 0.4
                if score > best_score:
                    best_score = score
                    best_portfolio = dict(zip(returns_df.columns, weights))
                    best_metrics = {
                        'sharpe': sharpe,
                        'total_return': total_return,
                        'volatility': volatility,
                        'max_drawdown': max_dd,
                        'p_no_loss': p_no_loss * 100
                    }
            if best_portfolio:
                results[label] = {
                    'portfolio': best_portfolio,
                    'metrics': best_metrics
                }
        if results:
            st.success("✅ נמצאו המלצות אופטימליות לכל התקופות!")
            for label, res in results.items():
                st.subheader(f"{label} - השילוב המומלץ")
                df = pd.DataFrame({
                    'מניה': list(res['portfolio'].keys()),
                    'אחוז השקעה מוצע': [f"{w:.1f}%" for w in res['portfolio'].values()]
                })
                st.dataframe(df, use_container_width=True)
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Sharpe Ratio", f"{res['metrics']['sharpe']:.2f}")
                with col2:
                    st.metric("תשואה כוללת", f"{res['metrics']['total_return']:.2f}%")
                with col3:
                    st.metric("תנודתיות", f"{res['metrics']['volatility']:.2f}%")
                with col4:
                    st.metric("Max Drawdown", f"{res['metrics']['max_drawdown']:.2f}%")
                with col5:
                    st.metric("סיכוי לא להפסיד", f"{res['metrics']['p_no_loss']:.1f}%")
        else:
            st.error("לא ניתן לבצע אופטימיזציה - נדרשות לפחות 2 מניות עם נתונים זמינים בכל תקופה")

elif suggest_combination:
    if not portfolio:
        st.error("אנא הכנס לפחות מניה אחת")
    elif total_percentage != 100:
        st.error(f"סה״כ האחוזים צריך להיות 100%. כרגע: {total_percentage}%")


# Footer
st.markdown("---")
st.markdown("**WhatIfWealth** - כלי לניתוח ביצועי תיק השקעות היסטורי") 