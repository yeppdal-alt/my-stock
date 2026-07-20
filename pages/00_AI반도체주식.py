import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from zoneinfo import ZoneInfo

# ----------------------------------------------------
# 기본 설정
# ----------------------------------------------------
st.set_page_config(
    page_title="AI 반도체 주식 전문 분석",
    page_icon="🔬",
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
# AI 반도체 관련 종목 목록
# ----------------------------------------------------
AI_CHIP_TICKERS = {
    "NVIDIA (NVDA)": "NVDA",
    "AMD (AMD)": "AMD",
    "Broadcom (AVGO)": "AVGO",
    "TSMC (TSM)": "TSM",
    "Intel (INTC)": "INTC",
    "Qualcomm (QCOM)": "QCOM",
    "Micron (MU)": "MU",
    "ASML (ASML)": "ASML",
    "Arm Holdings (ARM)": "ARM",
    "Marvell (MRVL)": "MRVL",
    "Texas Instruments (TXN)": "TXN",
    "Applied Materials (AMAT)": "AMAT",
    "Lam Research (LRCX)": "LRCX",
    "KLA (KLAC)": "KLAC",
    "삼성전자 (005930)": "005930.KS",
    "SK하이닉스 (000660)": "000660.KS",
}

BENCHMARKS = {
    "필라델피아 반도체 ETF (SOXX)": "SOXX",
    "S&P 500 (^GSPC)": "^GSPC",
    "나스닥 100 (^NDX)": "^NDX",
}

PERIOD_OPTIONS = {
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
    "2년": "2y",
    "5년": "5y",
}

# ----------------------------------------------------
# 데이터 로딩 (캐시)
# ----------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def load_history(ticker: str, period: str) -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=period, interval="1d")
    df = df.reset_index()
    return df


@st.cache_data(ttl=600, show_spinner=False)
def get_usd_krw_rate() -> float:
    """실시간 USD/KRW 환율 (1달러 = ?원). 조회 실패 시 대략치로 대체."""
    try:
        df = yf.Ticker("KRW=X").history(period="5d")
        if not df.empty:
            return float(df["Close"].iloc[-1])
    except Exception:
        pass
    return 1380.0


@st.cache_data(ttl=1800, show_spinner=False)
def load_fundamentals(ticker: str) -> dict:
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        info = {}
    now_utc = datetime.now(ZoneInfo("UTC"))
    kst_str = now_utc.astimezone(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    et_str = now_utc.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")
    return {
        "_조회시각": f"KST {kst_str} / ET {et_str}",
        "통화": info.get("currency", "USD"),
        "현재가_raw": info.get("currentPrice") or info.get("regularMarketPrice"),
        "시가총액_raw": info.get("marketCap"),
        "PER(trailing)": info.get("trailingPE"),
        "PER(forward)": info.get("forwardPE"),
        "PBR": info.get("priceToBook"),
        "매출성장률(YoY)": info.get("revenueGrowth"),
        "영업이익률": info.get("operatingMargins"),
        "ROE": info.get("returnOnEquity"),
        "베타": info.get("beta"),
        "배당수익률": info.get("dividendYield"),
        "52주 최고": info.get("fiftyTwoWeekHigh"),
        "52주 최저": info.get("fiftyTwoWeekLow"),
    }


# ----------------------------------------------------
# 기술적 지표 계산 함수
# ----------------------------------------------------
def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def fmt_pct(x):
    return f"{x * 100:.2f}%" if isinstance(x, (int, float)) else "N/A"


def fmt_num(x, decimals=2):
    return f"{x:,.{decimals}f}" if isinstance(x, (int, float)) else "N/A"


# ----------------------------------------------------
# 사이드바
# ----------------------------------------------------
st.sidebar.header("⚙️ 분석 옵션")

selected_names = st.sidebar.multiselect(
    "분석할 AI 반도체 종목",
    options=list(AI_CHIP_TICKERS.keys()),
    default=["NVIDIA (NVDA)", "AMD (AMD)", "Broadcom (AVGO)", "TSMC (TSM)", "ASML (ASML)"],
)

benchmark_label = st.sidebar.selectbox("비교 기준 지수", list(BENCHMARKS.keys()))
benchmark_ticker = BENCHMARKS[benchmark_label]

period_label = st.sidebar.selectbox("조회 기간", list(PERIOD_OPTIONS.keys()), index=2)
period = PERIOD_OPTIONS[period_label]

st.sidebar.divider()
tech_name = st.sidebar.selectbox(
    "기술적 분석 대상 종목",
    options=selected_names if selected_names else list(AI_CHIP_TICKERS.keys()),
)

st.sidebar.caption("데이터 출처: Yahoo Finance (yfinance)")

# ----------------------------------------------------
# 메인 화면
# ----------------------------------------------------
col_title, col_time = st.columns([5, 2])
with col_title:
    st.title("🔬 AI 반도체 주식 전문 분석")
    st.caption("NVIDIA, AMD, TSMC, ASML 등 AI 반도체 밸류체인 핵심 종목 · 밸류에이션 · 기술적 분석 · 상대성과 · 상관관계")
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
    st.info("왼쪽 사이드바에서 분석할 종목을 하나 이상 선택해 주세요.")
    st.stop()

selected_tickers = {name: AI_CHIP_TICKERS[name] for name in selected_names}

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 밸류에이션 비교", "📉 기술적 분석", "📈 상대성과 비교", "🔗 상관관계"]
)

# ----------------------------------------------------
# TAB 1: 밸류에이션 비교
# ----------------------------------------------------
with tab1:
    st.subheader("종목별 핵심 지표 비교")

    fx_rate = get_usd_krw_rate()

    rows = []
    fetch_times = []
    with st.spinner("펀더멘털 데이터 불러오는 중..."):
        for name, ticker in selected_tickers.items():
            f = load_fundamentals(ticker)
            fetch_times.append(f.get("_조회시각"))
            currency = f.get("통화") or "USD"
            price_raw = f["현재가_raw"]
            mc_raw = f["시가총액_raw"]

            if currency == "KRW":
                price_usd = (price_raw / fx_rate) if isinstance(price_raw, (int, float)) else None
                mc_usd_b = (mc_raw / fx_rate / 1e9) if isinstance(mc_raw, (int, float)) else None
            else:
                price_usd = price_raw
                mc_usd_b = (mc_raw / 1e9) if isinstance(mc_raw, (int, float)) else None

            rows.append({
                "종목": name,
                "티커": ticker,
                "원통화": currency,
                "현재가($)": fmt_num(price_usd),
                "시가총액(B$)": fmt_num(mc_usd_b),
                "PER(TTM)": fmt_num(f["PER(trailing)"]),
                "PER(Fwd)": fmt_num(f["PER(forward)"]),
                "PBR": fmt_num(f["PBR"]),
                "매출성장률": fmt_pct(f["매출성장률(YoY)"]),
                "영업이익률": fmt_pct(f["영업이익률"]),
                "ROE": fmt_pct(f["ROE"]),
                "베타": fmt_num(f["베타"]),
                "_marketcap_raw": mc_usd_b,
                "_per_raw": f["PER(trailing)"],
                "_opmargin_raw": f["영업이익률"],
                "_revgrowth_raw": f["매출성장률(YoY)"],
            })

    df_val = pd.DataFrame(rows)
    display_cols = ["종목", "티커", "원통화", "현재가($)", "시가총액(B$)", "PER(TTM)", "PER(Fwd)",
                     "PBR", "매출성장률", "영업이익률", "ROE", "베타"]
    st.dataframe(df_val[display_cols], use_container_width=True, hide_index=True)

    latest_fetch = max([t for t in fetch_times if t], default=None)
    st.caption(f"💱 원화(KRW) 종목은 실시간 환율(1$ ≈ {fx_rate:,.0f}원)로 달러 환산하여 표시했습니다. "
               f"PER·PBR·ROE 등 비율 지표는 통화 환산이 필요 없어 원본 값 그대로입니다.")
    if latest_fetch:
        st.caption(f"📅 펀더멘털 데이터 조회 시각: **{latest_fetch}** (30분 캐시 · Yahoo Finance 실시간 스냅샷 기준)")

    col1, col2 = st.columns(2)
    with col1:
        fig_mc = go.Figure(go.Bar(
            x=df_val["종목"], y=df_val["_marketcap_raw"],
            marker_color="rgba(65,105,225,0.75)",
        ))
        fig_mc.update_layout(title="시가총액 비교 (Billion $)", height=400,
                              margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_mc, use_container_width=True)

        fig_op = go.Figure(go.Bar(
            x=df_val["종목"], y=df_val["_opmargin_raw"] * 100 if df_val["_opmargin_raw"].notna().any() else None,
            marker_color="rgba(60,179,113,0.75)",
        ))
        fig_op.update_layout(title="영업이익률 비교 (%)", height=400,
                              margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_op, use_container_width=True)

    with col2:
        fig_per = go.Figure(go.Bar(
            x=df_val["종목"], y=df_val["_per_raw"],
            marker_color="rgba(255,140,0,0.75)",
        ))
        fig_per.update_layout(title="PER(TTM) 비교", height=400,
                               margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_per, use_container_width=True)

        fig_rev = go.Figure(go.Bar(
            x=df_val["종목"], y=df_val["_revgrowth_raw"] * 100 if df_val["_revgrowth_raw"].notna().any() else None,
            marker_color="rgba(220,20,60,0.75)",
        ))
        fig_rev.update_layout(title="매출성장률(YoY) 비교 (%)", height=400,
                               margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_rev, use_container_width=True)

    st.caption("※ PER이 음수/N/A인 경우 적자 기업이거나 데이터 미제공 종목입니다.")

# ----------------------------------------------------
# TAB 2: 기술적 분석 (캔들스틱 + MA + RSI + MACD)
# ----------------------------------------------------
with tab2:
    tech_ticker = AI_CHIP_TICKERS[tech_name]
    st.subheader(f"{tech_name} 기술적 분석")

    with st.spinner("가격 데이터 불러오는 중..."):
        df = load_history(tech_ticker, period)

    if df.empty:
        st.warning("데이터를 불러올 수 없습니다.")
    else:
        date_col = "Date" if "Date" in df.columns else "Datetime"
        last_date = pd.to_datetime(df[date_col].max()).strftime("%Y-%m-%d")
        st.caption(f"📅 데이터 기준일(최근 거래일): **{last_date}**")
        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA50"] = df["Close"].rolling(50).mean()
        df["MA200"] = df["Close"].rolling(200).mean()
        df["RSI14"] = compute_rsi(df["Close"], 14)
        macd_line, signal_line, hist = compute_macd(df["Close"])
        df["MACD"] = macd_line
        df["MACD_signal"] = signal_line
        df["MACD_hist"] = hist

        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            row_heights=[0.55, 0.2, 0.25], vertical_spacing=0.03,
            subplot_titles=("가격 & 이동평균선", "RSI(14)", "MACD"),
        )

        fig.add_trace(go.Candlestick(
            x=df[date_col], open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name=tech_name,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(x=df[date_col], y=df["MA20"], name="MA20",
                                  line=dict(width=1, color="orange")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df[date_col], y=df["MA50"], name="MA50",
                                  line=dict(width=1, color="blue")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df[date_col], y=df["MA200"], name="MA200",
                                  line=dict(width=1, color="purple")), row=1, col=1)

        fig.add_trace(go.Scatter(x=df[date_col], y=df["RSI14"], name="RSI(14)",
                                  line=dict(color="teal")), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

        fig.add_trace(go.Bar(x=df[date_col], y=df["MACD_hist"], name="MACD 히스토그램",
                              marker_color="rgba(128,128,128,0.5)"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df[date_col], y=df["MACD"], name="MACD",
                                  line=dict(color="blue", width=1)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df[date_col], y=df["MACD_signal"], name="Signal",
                                  line=dict(color="red", width=1)), row=3, col=1)

        fig.update_layout(
            height=850, xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(l=10, r=10, t=60, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        last_rsi = df["RSI14"].dropna().iloc[-1] if df["RSI14"].notna().any() else None
        if last_rsi is not None:
            if last_rsi >= 70:
                st.warning(f"현재 RSI: {last_rsi:.1f} → 과매수(Overbought) 구간")
            elif last_rsi <= 30:
                st.success(f"현재 RSI: {last_rsi:.1f} → 과매도(Oversold) 구간")
            else:
                st.info(f"현재 RSI: {last_rsi:.1f} → 중립 구간")

        with st.expander("원본 데이터 보기"):
            st.dataframe(df.tail(50), use_container_width=True)

# ----------------------------------------------------
# TAB 3: 상대성과 비교 (벤치마크 포함, 정규화 100 기준)
# ----------------------------------------------------
with tab3:
    st.subheader(f"정규화 상대성과 비교 (시작일=100, 기준지수: {benchmark_label})")

    fig_rel = go.Figure()
    last_dates = []
    with st.spinner("데이터 불러오는 중..."):
        for name, ticker in selected_tickers.items():
            df_t = load_history(ticker, period)
            if df_t.empty:
                continue
            date_col = "Date" if "Date" in df_t.columns else "Datetime"
            norm = df_t["Close"] / df_t["Close"].iloc[0] * 100
            fig_rel.add_trace(go.Scatter(x=df_t[date_col], y=norm, name=name, mode="lines"))
            last_dates.append(df_t[date_col].max())

        df_bench = load_history(benchmark_ticker, period)
        if not df_bench.empty:
            date_col_b = "Date" if "Date" in df_bench.columns else "Datetime"
            norm_b = df_bench["Close"] / df_bench["Close"].iloc[0] * 100
            fig_rel.add_trace(go.Scatter(
                x=df_bench[date_col_b], y=norm_b, name=f"{benchmark_label} (기준)",
                mode="lines", line=dict(color="black", dash="dash", width=2),
            ))
            last_dates.append(df_bench[date_col_b].max())

    if last_dates:
        last_date = pd.to_datetime(max(last_dates)).strftime("%Y-%m-%d")
        st.caption(f"📅 데이터 기준일(최근 거래일): **{last_date}**")

    fig_rel.update_layout(
        height=600, xaxis_title="날짜", yaxis_title="정규화 지수 (시작일=100)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified",
    )
    st.plotly_chart(fig_rel, use_container_width=True)

# ----------------------------------------------------
# TAB 4: 상관관계 히트맵 (일별 수익률 기준)
# ----------------------------------------------------
with tab4:
    st.subheader("일별 수익률 상관관계")

    returns_df = pd.DataFrame()
    with st.spinner("데이터 불러오는 중..."):
        for name, ticker in selected_tickers.items():
            df_t = load_history(ticker, period)
            if df_t.empty:
                continue
            date_col = "Date" if "Date" in df_t.columns else "Datetime"
            s = df_t.set_index(date_col)["Close"].pct_change()
            returns_df[name] = s

    if returns_df.shape[1] >= 2:
        corr = returns_df.corr()
        fig_corr = go.Figure(data=go.Heatmap(
            z=corr.values, x=corr.columns, y=corr.columns,
            colorscale="RdBu", zmid=0, zmin=-1, zmax=1,
            text=corr.round(2).values, texttemplate="%{text}",
        ))
        fig_corr.update_layout(height=550, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_corr, use_container_width=True)
        if not returns_df.empty:
            last_date = pd.to_datetime(returns_df.index.max()).strftime("%Y-%m-%d")
            st.caption(f"📅 데이터 기준일(최근 거래일): **{last_date}**")
        st.caption("1에 가까울수록 함께 움직이고, -1에 가까울수록 반대로 움직입니다.")
    else:
        st.info("상관관계를 보려면 2개 이상의 종목을 선택해 주세요.")

st.divider()
st.caption(
    "※ 상단의 새로고침 시각은 페이지가 로드된 시각입니다. 가격 데이터는 10분, 펀더멘털 데이터는 30분 캐시(TTL)로 "
    "관리되어 실제 시세와 최대 그만큼 차이가 날 수 있습니다. 즉시 최신화하려면 상단 '🔄 새로고침' 버튼을 눌러주세요. "
    "투자 참고용이며 투자 판단의 책임은 본인에게 있습니다."
)
