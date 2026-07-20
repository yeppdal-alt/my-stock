import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ----------------------------------------------------
# 기본 설정
# ----------------------------------------------------
st.set_page_config(
    page_title="글로벌 주요 주식 대시보드",
    page_icon="📈",
    layout="wide",
)


def now_kst_et_str() -> str:
    """현재 시각을 한국시간(KST)과 미국 동부시간(ET) 두 줄로 반환."""
    now_utc = datetime.now(ZoneInfo("UTC"))
    kst = now_utc.astimezone(ZoneInfo("Asia/Seoul"))
    et = now_utc.astimezone(ZoneInfo("America/New_York"))
    return (
        f"🇰🇷 KST {kst.strftime('%Y-%m-%d %H:%M:%S')}<br>"
        f"🇺🇸 ET&nbsp;&nbsp;{et.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    )

# ----------------------------------------------------
# 글로벌 주요 종목/지수 목록
# ----------------------------------------------------
TICKERS = {
    # 미국 지수 / 빅테크
    "S&P 500 (지수)": "^GSPC",
    "나스닥 100 (지수)": "^NDX",
    "다우존스 (지수)": "^DJI",
    "Apple (AAPL)": "AAPL",
    "Microsoft (MSFT)": "MSFT",
    "NVIDIA (NVDA)": "NVDA",
    "Amazon (AMZN)": "AMZN",
    "Alphabet (GOOGL)": "GOOGL",
    "Meta (META)": "META",
    "Tesla (TSLA)": "TSLA",
    # 한국
    "코스피 (지수)": "^KS11",
    "코스닥 (지수)": "^KQ11",
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    # 일본 / 중국 / 홍콩
    "니케이225 (지수)": "^N225",
    "상해종합 (지수)": "000001.SS",
    "항셍 (지수)": "^HSI",
    "Toyota (7203.T)": "7203.T",
    # 유럽
    "DAX (독일 지수)": "^GDAXI",
    "FTSE 100 (영국 지수)": "^FTSE",
    "CAC 40 (프랑스 지수)": "^FCHI",
    # 원자재 / 기타
    "금 선물 (GC=F)": "GC=F",
    "WTI 원유 (CL=F)": "CL=F",
    "비트코인 (BTC-USD)": "BTC-USD",
}

PERIOD_OPTIONS = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
    "2년": "2y",
    "5년": "5y",
    "최대": "max",
}

INTERVAL_OPTIONS = {
    "1일": "1d",
    "1주": "1wk",
    "1개월": "1mo",
}

# ----------------------------------------------------
# 데이터 로딩 (캐시)
# ----------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def load_price_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=period, interval=interval)
    df = df.reset_index()
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_info(ticker: str) -> dict:
    try:
        return yf.Ticker(ticker).fast_info
    except Exception:
        return {}


# ----------------------------------------------------
# 사이드바
# ----------------------------------------------------
st.sidebar.header("⚙️ 옵션 설정")

selected_names = st.sidebar.multiselect(
    "종목 선택 (최대 6개 비교 가능)",
    options=list(TICKERS.keys()),
    default=["S&P 500 (지수)", "코스피 (지수)", "니케이225 (지수)"],
    max_selections=6,
)

period_label = st.sidebar.selectbox("조회 기간", list(PERIOD_OPTIONS.keys()), index=3)
interval_label = st.sidebar.selectbox("데이터 간격", list(INTERVAL_OPTIONS.keys()), index=0)
period = PERIOD_OPTIONS[period_label]
interval = INTERVAL_OPTIONS[interval_label]

chart_type = st.sidebar.radio("차트 종류", ["캔들스틱 (개별)", "정규화 비교선그래프"])

st.sidebar.caption("데이터 출처: Yahoo Finance (yfinance)")

# ----------------------------------------------------
# 메인 화면
# ----------------------------------------------------
col_title, col_time = st.columns([5, 2])
with col_title:
    st.title("📈 글로벌 주요 주식 대시보드")
    st.caption("Yahoo Finance 데이터 기반 · Plotly 시각화 · Streamlit Cloud 배포용")
with col_time:
    st.markdown(
        f"""<div style='text-align:right; padding-top:20px; color:gray; font-size:0.85rem; line-height:1.5;'>
        🕒 마지막 새로고침<br>{now_kst_et_str()}</div>""",
        unsafe_allow_html=True,
    )
    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if not selected_names:
    st.info("왼쪽 사이드바에서 종목을 하나 이상 선택해 주세요.")
    st.stop()

selected_tickers = [TICKERS[name] for name in selected_names]

# ---- 요약 지표 카드 ----
st.subheader("📊 요약 지표")
cols = st.columns(len(selected_tickers))

summary_data = {}
for col, name, ticker in zip(cols, selected_names, selected_tickers):
    with st.spinner(f"{name} 로딩 중..."):
        hist = load_price_history(ticker, period="5d", interval="1d")
    if hist.empty or len(hist) < 2:
        col.metric(name, "N/A")
        continue
    last_price = hist["Close"].iloc[-1]
    prev_price = hist["Close"].iloc[-2]
    change = last_price - prev_price
    change_pct = (change / prev_price) * 100
    col.metric(
        label=name,
        value=f"{last_price:,.2f}",
        delta=f"{change:,.2f} ({change_pct:+.2f}%)",
    )
    summary_data[name] = ticker

st.divider()

# ---- 차트 영역 ----
if chart_type == "캔들스틱 (개별)":
    st.subheader("🕯️ 개별 캔들스틱 차트")
    tabs = st.tabs(selected_names)
    for tab, name, ticker in zip(tabs, selected_names, selected_tickers):
        with tab:
            with st.spinner(f"{name} 데이터 불러오는 중..."):
                df = load_price_history(ticker, period, interval)

            if df.empty:
                st.warning(f"{name}({ticker}) 데이터를 불러올 수 없습니다.")
                continue

            date_col = "Date" if "Date" in df.columns else "Datetime"
            last_date = pd.to_datetime(df[date_col].max()).strftime("%Y-%m-%d")
            st.caption(f"📅 데이터 기준일(최근 거래일): **{last_date}**")

            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                row_heights=[0.75, 0.25], vertical_spacing=0.03,
            )
            fig.add_trace(
                go.Candlestick(
                    x=df[date_col],
                    open=df["Open"], high=df["High"],
                    low=df["Low"], close=df["Close"],
                    name=name,
                ),
                row=1, col=1,
            )
            fig.add_trace(
                go.Bar(x=df[date_col], y=df["Volume"], name="거래량", marker_color="rgba(100,149,237,0.5)"),
                row=2, col=1,
            )
            fig.update_layout(
                title=f"{name} ({ticker})",
                xaxis_rangeslider_visible=False,
                height=600,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin=dict(l=10, r=10, t=60, b=10),
            )
            fig.update_yaxes(title_text="가격", row=1, col=1)
            fig.update_yaxes(title_text="거래량", row=2, col=1)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("원본 데이터 보기"):
                st.dataframe(df.tail(50), use_container_width=True)

else:
    st.subheader("📈 정규화 비교 선그래프 (시작일 = 100 기준)")
    fig = go.Figure()
    combined_df = pd.DataFrame()

    for name, ticker in zip(selected_names, selected_tickers):
        with st.spinner(f"{name} 데이터 불러오는 중..."):
            df = load_price_history(ticker, period, interval)
        if df.empty:
            st.warning(f"{name}({ticker}) 데이터를 불러올 수 없습니다.")
            continue

        date_col = "Date" if "Date" in df.columns else "Datetime"
        normalized = df["Close"] / df["Close"].iloc[0] * 100

        fig.add_trace(
            go.Scatter(
                x=df[date_col], y=normalized,
                mode="lines", name=name,
            )
        )
        combined_df[name] = df.set_index(date_col)["Close"]

    fig.update_layout(
        height=600,
        xaxis_title="날짜",
        yaxis_title="정규화 지수 (시작일=100)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    if not combined_df.empty:
        last_date = pd.to_datetime(combined_df.index.max()).strftime("%Y-%m-%d")
        st.caption(f"📅 데이터 기준일(최근 거래일): **{last_date}**")

    with st.expander("원본 종가 데이터 보기"):
        st.dataframe(combined_df.tail(50), use_container_width=True)

st.divider()
st.caption(
    "※ 상단의 새로고침 시각은 페이지가 로드된 시각이며, 가격 데이터는 5분 캐시(TTL)로 관리되어 "
    "실제 시세는 최대 5분 전 값일 수 있습니다. 즉시 최신화하려면 상단 '🔄 새로고침' 버튼을 눌러주세요."
)
