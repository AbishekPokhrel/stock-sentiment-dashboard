import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from auth import init_session_state, show_landing_page
from database import (
    get_search_history,
    delete_history_record,
    update_history_sentiment,
    save_search,
)
from sentiment_utils import fetch_news, analyze_articles, classify_sentiment
from stock_utils import get_company_name, get_stock_data
from ui_styles import apply_global_styles


st.set_page_config(
    page_title="AI Stock Sentiment Dashboard",
    page_icon="📈",
    layout="wide"
)

apply_global_styles()
init_session_state()

# ---------------------------------------------------
# PUBLIC LANDING PAGE BEFORE LOGIN
# ---------------------------------------------------
if not st.session_state.logged_in:
    show_landing_page()
    st.stop()

# ---------------------------------------------------
# DASHBOARD AFTER LOGIN
# ---------------------------------------------------
st.markdown(f"""
<div class="topbar">
    <div class="topbar-left">📈 AI Stock Sentiment Dashboard</div>
    <div class="topbar-right">Welcome, {st.session_state.get("username", "User")}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-box">
    <div class="hero-title">Smarter Stock Research, Without the Noise</div>
    <div class="hero-subtitle">
        Analyze financial news, detect sentiment, and track stock trends in one place.
    </div>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-label">Live Analysis</div>
        <div class="metric-value">Real-Time</div>
        <div class="metric-change">Updated with latest news</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-label">Sentiment Engine</div>
        <div class="metric-value">AI Based</div>
        <div class="metric-change">Positive / Neutral / Negative</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-label">Stock Tracking</div>
        <div class="metric-value">Charts</div>
        <div class="metric-change">View recent closing prices</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.user_email = ""
        st.session_state.username = ""
        st.session_state.selected_ticker = ""
        st.rerun()

NEWS_API_KEY = None
try:
    NEWS_API_KEY = st.secrets["NEWS_API_KEY"]
except Exception:
    NEWS_API_KEY = st.text_input("Enter your NewsAPI key", type="password")

st.markdown('<div class="section-label">Search a Stock</div>', unsafe_allow_html=True)

c1, c2 = st.columns([5, 1])
with c1:
    ticker = st.text_input(
        "Ticker",
        value=st.session_state.selected_ticker,
        placeholder="Enter ticker like AAPL, TSLA, NVDA",
        label_visibility="collapsed"
    )

with c2:
    analyze = st.button("Analyze")

st.markdown('<div class="quick-title">Popular Tickers</div>', unsafe_allow_html=True)
q1, q2, q3, q4, q5 = st.columns(5)

with q1:
    if st.button("AAPL"):
        st.session_state.selected_ticker = "AAPL"
        st.rerun()

with q2:
    if st.button("TSLA"):
        st.session_state.selected_ticker = "TSLA"
        st.rerun()

with q3:
    if st.button("NVDA"):
        st.session_state.selected_ticker = "NVDA"
        st.rerun()

with q4:
    if st.button("MSFT"):
        st.session_state.selected_ticker = "MSFT"
        st.rerun()

with q5:
    if st.button("AMZN"):
        st.session_state.selected_ticker = "AMZN"
        st.rerun()


def prepare_stock_dataframe(stock_df_raw):
    """
    Prepare stock dataframe safely for charts and metrics.
    """
    if stock_df_raw is None or stock_df_raw.empty:
        return pd.DataFrame(), None

    stock_df = stock_df_raw.copy().reset_index()

    # Find date column safely
    date_col = None
    for col in stock_df.columns:
        if str(col).lower() in ["date", "datetime"]:
            date_col = col
            break

    if date_col is None:
        date_col = stock_df.columns[0]

    # Flatten possible multi-index / tuple columns
    cleaned_columns = []
    for col in stock_df.columns:
        if isinstance(col, tuple):
            cleaned_columns.append(str(col[0]))
        else:
            cleaned_columns.append(str(col))
    stock_df.columns = cleaned_columns

    # Rename first column to Date if needed
    if stock_df.columns[0] != "Date":
        stock_df = stock_df.rename(columns={stock_df.columns[0]: "Date"})
    else:
        stock_df["Date"] = stock_df["Date"]

    # Ensure Close exists and is numeric
    if "Close" in stock_df.columns:
        stock_df["Close"] = pd.to_numeric(stock_df["Close"], errors="coerce")

    return stock_df, "Date"


if analyze:
    if not ticker.strip():
        st.warning("Please enter a stock ticker.")
    elif not NEWS_API_KEY:
        st.warning("Please enter your NewsAPI key.")
    else:
        ticker = ticker.strip().upper()
        st.session_state.selected_ticker = ticker

        company_name = get_company_name(ticker)
        articles = fetch_news(company_name, NEWS_API_KEY)

        if not articles:
            st.error("No news articles found.")
        else:
            df = analyze_articles(articles)

            if df.empty:
                st.error("No analyzable news data found.")
            else:
                avg_score = df["score"].mean()
                overall_sentiment = classify_sentiment(avg_score)

                positive_count = (df["sentiment"] == "Positive").sum()
                neutral_count = (df["sentiment"] == "Neutral").sum()
                negative_count = (df["sentiment"] == "Negative").sum()

                save_search(
                    st.session_state.user_id,
                    ticker,
                    company_name,
                    overall_sentiment,
                    avg_score
                )

                stock_df_raw = get_stock_data(ticker)
                stock_df, date_col = prepare_stock_dataframe(stock_df_raw)
                latest_price = None

                if not stock_df.empty and "Close" in stock_df.columns:
                    close_values = stock_df["Close"].dropna()
                    if len(close_values) > 0:
                        latest_price = float(close_values.iloc[-1])

                st.success(f"Overall Sentiment for {company_name} ({ticker}): {overall_sentiment}")

                m1, m2, m3, m4 = st.columns(4)

                with m1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Company</div>
                        <div class="metric-value">{company_name}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with m2:
                    price_text = f"${latest_price:.2f}" if latest_price is not None else "N/A"
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Latest Price</div>
                        <div class="metric-value">{price_text}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with m3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Sentiment</div>
                        <div class="metric-value">{overall_sentiment}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with m4:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Articles</div>
                        <div class="metric-value">{len(df)}</div>
                    </div>
                    """, unsafe_allow_html=True)

                gauge_fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=avg_score,
                    title={"text": "Overall Sentiment Score"},
                    gauge={
                        "axis": {"range": [-1, 1]},
                        "bar": {"color": "#4f8cff"},
                        "steps": [
                            {"range": [-1, -0.05], "color": "#f28b82"},
                            {"range": [-0.05, 0.05], "color": "#f6e58d"},
                            {"range": [0.05, 1], "color": "#9be7a8"}
                        ]
                    }
                ))
                gauge_fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white")
                )
                st.plotly_chart(gauge_fig, use_container_width=True)

                tab1, tab2, tab3 = st.tabs(["Overview", "Charts", "Articles"])

                with tab1:
                    st.subheader("Overview")
                    st.write(f"**Company:** {company_name}")
                    st.write(f"**Ticker:** {ticker}")
                    st.write(f"**Average Sentiment Score:** {avg_score:.3f}")
                    st.write(f"**Overall Sentiment:** {overall_sentiment}")
                    if latest_price is not None:
                        st.write(f"**Latest Closing Price:** ${latest_price:.2f}")

                with tab2:
                    sentiment_counts = pd.DataFrame({
                        "Sentiment": ["Positive", "Neutral", "Negative"],
                        "Count": [positive_count, neutral_count, negative_count]
                    })

                    fig_bar = px.bar(
                        sentiment_counts,
                        x="Sentiment",
                        y="Count",
                        text="Count",
                        title="News Sentiment Breakdown"
                    )
                    fig_bar.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="white"),
                        title_font=dict(size=20),
                        xaxis_title="Sentiment",
                        yaxis_title="Article Count"
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

                    if stock_df.empty:
                        st.warning("No stock data available for chart.")
                    elif "Close" not in stock_df.columns:
                        st.error("Stock data missing 'Close' column.")
                    else:
                        close_data = stock_df["Close"].dropna()

                        if close_data.empty:
                            st.warning("No valid closing price data available.")
                        else:
                            fig_line = px.line(
                                stock_df,
                                x="Date",
                                y="Close",
                                title=f"{ticker} Closing Price Trend",
                                markers=True
                            )

                            fig_line.update_traces(
                                line=dict(width=3),
                                hovertemplate="<b>Date:</b> %{x}<br><b>Close:</b> $%{y:.2f}<extra></extra>"
                            )

                            fig_line.update_layout(
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                font=dict(color="white"),
                                title_font=dict(size=20),
                                xaxis_title="Date",
                                yaxis_title="Closing Price (USD)",
                                xaxis=dict(showgrid=False),
                                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)"),
                                hovermode="x unified"
                            )

                            st.plotly_chart(fig_line, use_container_width=True)

                with tab3:
                    for _, row in df.iterrows():
                        title = row["title"] if pd.notna(row["title"]) else "No title"
                        source = row["source"] if pd.notna(row["source"]) else "Unknown source"
                        published = row["publishedAt"] if pd.notna(row["publishedAt"]) else "Unknown date"
                        sentiment = row["sentiment"] if pd.notna(row["sentiment"]) else "Unknown"
                        description = row["description"] if pd.notna(row["description"]) else "No description available."
                        url = row["url"] if pd.notna(row["url"]) else "#"

                        st.markdown(f"""
                        <div class="article-card">
                            <div class="article-title">{title}</div>
                            <div class="article-meta">
                                Source: {source} | Date: {published} | Sentiment: {sentiment}
                            </div>
                            <div class="article-desc">
                                {description}
                            </div>
                            <a href="{url}" target="_blank">Read full article</a>
                        </div>
                        """, unsafe_allow_html=True)

st.markdown("## Saved Search History")
history = get_search_history(st.session_state.user_id)

if history:
    history_df = pd.DataFrame(history)
    cols_to_show = ["ticker", "company_name", "sentiment", "score", "searched_at"]
    existing_cols = [c for c in cols_to_show if c in history_df.columns]
    st.dataframe(history_df[existing_cols], use_container_width=True)

    st.markdown("### Manage History")
    for row in history:
        record_id = row.get("id")
        ticker_val = row.get("ticker", "")
        company_val = row.get("company_name", "")
        sentiment_val = row.get("sentiment", "")
        score_val = row.get("score", "")
        searched_val = row.get("searched_at", "")

        with st.expander(f"{ticker_val} - {company_val} - {sentiment_val}"):
            st.write(f"**Score:** {score_val}")
            st.write(f"**Searched At:** {searched_val}")

            c1, c2 = st.columns(2)

            with c1:
                if st.button(f"Delete {record_id}", key=f"delete_{record_id}"):
                    delete_history_record(record_id, st.session_state.user_id)
                    st.success("Record deleted.")
                    st.rerun()

            with c2:
                new_sentiment = st.selectbox(
                    f"Update sentiment for {ticker_val}",
                    ["Positive", "Neutral", "Negative"],
                    index=["Positive", "Neutral", "Negative"].index(sentiment_val)
                    if sentiment_val in ["Positive", "Neutral", "Negative"] else 1,
                    key=f"sentiment_{record_id}"
                )
                if st.button(f"Update {record_id}", key=f"update_{record_id}"):
                    update_history_sentiment(record_id, st.session_state.user_id, new_sentiment)
                    st.success("Record updated.")
                    st.rerun()
else:
    st.info("No saved history yet.")
