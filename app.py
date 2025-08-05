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
        "AAPL": 30,
        "MSFT": 25,
        "GOOGL": 20,
        "AMZN": 15,
        "TSLA": 10
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
            
            # Display results
            st.header("📊 תוצאות הניתוח")
            
            # Performance comparison
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("תשואה כוללת", f"{total_return:.2f}%", f"{total_return - benchmark_total_return:.2f}%")
            
            with col2:
                st.metric("תשואה שנתית", f"{volatility:.2f}%", f"{volatility - benchmark_volatility:.2f}%")
            
            with col3:
                st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}", f"{sharpe_ratio - benchmark_sharpe:.2f}")
            
            with col4:
                st.metric("Max Drawdown", f"{max_drawdown:.2f}%", f"{max_drawdown - benchmark_max_drawdown:.2f}%")
            
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
            '5 שנים': 1260    # ~1260 trading days
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
            for i in range(5000):
                weights = np.random.random(len(returns_df.columns))
                weights = weights / weights.sum() * 100
                portfolio_returns = (returns_df * (weights / 100)).sum(axis=1)
                risk_free_rate = 0.02
                sharpe = (portfolio_returns.mean() * 252 - risk_free_rate) / (portfolio_returns.std() * np.sqrt(252))
                total_return = ((1 + portfolio_returns).cumprod().iloc[-1] - 1) * 100
                volatility = portfolio_returns.std() * np.sqrt(252) * 100
                cumulative = (1 + portfolio_returns).cumprod()
                rolling_max = cumulative.expanding().max()
                drawdown = (cumulative - rolling_max) / rolling_max
                max_dd = drawdown.min() * 100
                # Score: 60% Sharpe, 40% total return
                score = sharpe * 0.6 + (total_return / 100) * 0.4
                if score > best_score:
                    best_score = score
                    best_portfolio = dict(zip(returns_df.columns, weights))
                    best_metrics = {
                        'sharpe': sharpe,
                        'total_return': total_return,
                        'volatility': volatility,
                        'max_drawdown': max_dd
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
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Sharpe Ratio", f"{res['metrics']['sharpe']:.2f}")
                with col2:
                    st.metric("תשואה כוללת", f"{res['metrics']['total_return']:.2f}%")
                with col3:
                    st.metric("תנודתיות", f"{res['metrics']['volatility']:.2f}%")
                with col4:
                    st.metric("Max Drawdown", f"{res['metrics']['max_drawdown']:.2f}%")
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