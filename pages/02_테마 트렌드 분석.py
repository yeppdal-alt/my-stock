import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from zoneinfo import ZoneInfo

# ----------------------------------------------------
# 기본 설정
# ----------------------------------------------------
st.set_page_config(
    page_title="테마 트렌드 분석",
    page_icon="🧭",
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
# 테마별 대표 종목 (테마당 5개, 전부 미국 상장·USD 표시)
# ----------------------------------------------------
THEMES = {
    "AI 반도체": ["NVDA", "AMD", "AVGO", "TSM", "ASML"],
    "양자컴퓨팅": ["IONQ", "RGTI", "QBTS", "QUBT", "IBM"],
    "원자력/SMR": ["CEG", "VST", "OKLO", "SMR", "CCJ"],
    "비만치료제(GLP-1)": ["LLY", "NVO", "VKTX", "AMGN", "PFE"],
    "방위산업/우주": ["LMT", "RTX", "NOC", "PLTR", "RKLB"],
    "로보틱스/자동화": ["ISRG", "ROK", "SYM", "TER", "PATH"],
    "사이버보안": ["CRWD", "PANW", "ZS", "FTNT", "S"],
    "클라우드/SaaS": ["MSFT", "CRM", "NOW", "SNOW", "DDOG"],
    "전기차/배터리": ["TSLA", "RIVN", "LI", "ALB", "XPEV"],
    "비트코인/블록체인": ["COIN", "MSTR", "MARA", "RIOT", "HOOD"],
    "중국 기술주": ["BABA", "PDD", "JD", "BIDU", "NIO"],
    "그린수소/재생에너지": ["ENPH", "FSLR", "PLUG", "BE", "NEE"],
}

ALL_TICKERS = sorted({t for tickers in THEMES.values() for t in tickers})

# ----------------------------------------------------
# 데이터 로딩 (캐시) - 전체 종목 일괄 다운로드
# ----------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def load_all_history(tickers: list, period: str = "6mo") -> pd.DataFrame:
    data = yf.download(
        tickers=tickers, period=period, interval="1d",
        group_by="ticker", auto_adjust=True, threads=True, progress=False,
    )
    return data


def get_close_series(data: pd.DataFrame, ticker: str) -> pd.Series:
    try:
        if isinstance(data.columns, pd.MultiIndex):
            s = data[ticker]["Close"]
        else:
            s = data["Close"]
        return s.dropna()
    except Exception:
        return pd.Series(dtype=float)


def compute_returns(close: pd.Series):
    """(현재가, 1개월수익률, 3개월수익률, 6개월수익률) 튜플 반환. 거래일수 21/63/126일 기준."""
    if close.empty:
        return None, None, None, None
    last = close.iloc[-1]

    def ret(n_days):
        if len(close) > n_days:
            base = close.iloc[-(n_days + 1)]
        else:
            base = close.iloc[0]
        return (last / base - 1) if base else None

    return last, ret(21), ret(63), ret(126)


def fmt_pct(x):
    return f"{x * 100:+.2f}%" if isinstance(x, (int, float)) else "N/A"


def fmt_num(x, decimals=2):
    return f"{x:,.{decimals}f}" if isinstance(x, (int, float)) else "N/A"


# ----------------------------------------------------
# 사이드바
# ----------------------------------------------------
st.sidebar.header("⚙️ 분석 옵션")

selected_theme_names = st.sidebar.multiselect(
    "분석할 테마 (기본: 전체)",
    options=list(THEMES.keys()),
    default=list(THEMES.keys()),
)

top_n = st.sidebar.slider("카테고리별 표시 테마 수", min_value=2, max_value=6, value=4)

st.sidebar.caption("데이터 출처: Yahoo Finance (yfinance) · 종목당 1개월(21거래일)/3개월(63거래일)/6개월(126거래일) 수익률 기준")

# ----------------------------------------------------
# 메인 화면
# ----------------------------------------------------
col_title, col_time = st.columns([5, 2])
with col_title:
    st.title("🧭 테마 트렌드 분석")
    st.caption("주요 투자 테마의 실시간 가격 모멘텀을 계산해 상승/하락/잠재 성장 테마로 자동 분류합니다")
with col_time:
    st.markdown(
        f"""<div style='text-align:right; padding-top:20px; color:gray; font-size:0.85rem; line-height:1.5;'>
        🕒 마지막 새로고침<br>{now_kst_et_str()}</div>""",
        unsafe_allow_html=True,
    )
    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.info(
    "ℹ️ **분류 방식**: 테마는 사전에 큐레이션된 12개 대표 섹터이며, '주목받는/하락/잠재 성장' 라벨은 고정된 것이 아니라 "
    "각 테마 구성 종목 5개의 **실시간 가격 수익률 평균**으로 매번 새로 계산됩니다. 🔥 상승 테마 = 최근 1개월 수익률 상위, "
    "📉 하락 테마 = 최근 1개월 수익률 하위, 🌱 잠재 성장 테마 = 6개월 추세는 견조하지만 아직 단기 급등(상승 테마 상위권)에는 "
    "포함되지 않은 테마입니다."
)

if not selected_theme_names:
    st.warning("왼쪽 사이드바에서 테마를 하나 이상 선택해 주세요.")
    st.stop()

active_themes = {name: THEMES[name] for name in selected_theme_names}
active_tickers = sorted({t for tickers in active_themes.values() for t in tickers})

with st.spinner("전체 종목 가격 데이터 불러오는 중... (테마 수에 따라 다소 시간이 걸릴 수 있습니다)"):
    raw_data = load_all_history(active_tickers, period="6mo")

# ---- 종목별 수익률 테이블 생성 ----
rows = []
last_dates = []
for theme_name, tickers in active_themes.items():
    for ticker in tickers:
        close = get_close_series(raw_data, ticker)
        if not close.empty:
            last_dates.append(close.index.max())
        last, r1m, r3m, r6m = compute_returns(close)
        rows.append({
            "테마": theme_name, "티커": ticker,
            "현재가": last, "1개월": r1m, "3개월": r3m, "6개월": r6m,
        })

df_all = pd.DataFrame(rows)

if last_dates:
    latest_date = pd.to_datetime(max(last_dates)).strftime("%Y-%m-%d")
    st.caption(f"📅 데이터 기준일(최근 거래일): **{latest_date}**")

# ---- 테마별 평균 수익률 집계 ----
theme_stats = df_all.groupby("테마")[["1개월", "3개월", "6개월"]].mean().reset_index()
theme_stats = theme_stats.sort_values("1개월", ascending=False).reset_index(drop=True)

# ---- 전체 테마 랭킹 개요 차트 ----
st.subheader("📊 전체 테마 모멘텀 랭킹 (1개월 평균 수익률)")
colors = ["rgba(220,20,60,0.8)" if v < 0 else "rgba(34,139,34,0.8)" for v in theme_stats["1개월"]]
fig_overview = go.Figure(go.Bar(
    x=theme_stats["1개월"] * 100, y=theme_stats["테마"],
    orientation="h", marker_color=colors,
    text=[f"{v*100:+.1f}%" for v in theme_stats["1개월"]], textposition="outside",
))
fig_overview.update_layout(
    height=100 + 40 * len(theme_stats), xaxis_title="1개월 평균 수익률 (%)",
    margin=dict(l=10, r=40, t=20, b=20), yaxis=dict(autorange="reversed"),
)
st.plotly_chart(fig_overview, use_container_width=True)

st.divider()

# ---- 카테고리 분류 ----
rising_themes = theme_stats.head(top_n)["테마"].tolist()

falling_themes = theme_stats.sort_values("1개월", ascending=True).head(top_n)["테마"].tolist()
falling_themes = [t for t in falling_themes if t not in rising_themes]

growth_candidates = theme_stats[
    (~theme_stats["테마"].isin(rising_themes)) &
    (~theme_stats["테마"].isin(falling_themes)) &
    (theme_stats["6개월"] > 0)
].sort_values("6개월", ascending=False)
growth_themes = growth_candidates.head(top_n)["테마"].tolist()


def render_theme_section(title: str, theme_list: list, empty_msg: str):
    st.subheader(title)
    if not theme_list:
        st.info(empty_msg)
        return
    for theme_name in theme_list:
        stat_row = theme_stats[theme_stats["테마"] == theme_name].iloc[0]
        with st.expander(
            f"{theme_name}  ·  1개월 {fmt_pct(stat_row['1개월'])}  "
            f"·  3개월 {fmt_pct(stat_row['3개월'])}  ·  6개월 {fmt_pct(stat_row['6개월'])}",
            expanded=True,
        ):
            theme_df = df_all[df_all["테마"] == theme_name].sort_values("1개월", ascending=False).reset_index(drop=True)
            theme_df.insert(0, "순위", range(1, len(theme_df) + 1))

            col_chart, col_table = st.columns([1, 1])
            with col_chart:
                bar_colors = ["rgba(220,20,60,0.75)" if v < 0 else "rgba(65,105,225,0.75)"
                              for v in theme_df["1개월"]]
                fig = go.Figure(go.Bar(
                    x=theme_df["티커"], y=theme_df["1개월"] * 100,
                    marker_color=bar_colors,
                    text=[f"{v*100:+.1f}%" if pd.notna(v) else "N/A" for v in theme_df["1개월"]],
                    textposition="outside",
                ))
                fig.update_layout(
                    title="종목별 1개월 수익률 (%)", height=320,
                    margin=dict(l=10, r=10, t=40, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_table:
                display_df = theme_df.copy()
                display_df["현재가"] = display_df["현재가"].apply(lambda x: fmt_num(x))
                display_df["1개월"] = display_df["1개월"].apply(fmt_pct)
                display_df["3개월"] = display_df["3개월"].apply(fmt_pct)
                display_df["6개월"] = display_df["6개월"].apply(fmt_pct)
                st.dataframe(
                    display_df[["순위", "티커", "현재가", "1개월", "3개월", "6개월"]],
                    use_container_width=True, hide_index=True, height=250,
                )


render_theme_section(
    "🔥 최근 주목받는 테마 (Top 종목 5개씩)",
    rising_themes,
    "조건을 만족하는 상승 테마가 없습니다.",
)

st.divider()

render_theme_section(
    "📉 하락 테마 (Top 종목 5개씩)",
    falling_themes,
    "조건을 만족하는 하락 테마가 없습니다.",
)

st.divider()

render_theme_section(
    "🌱 잠재 성장 테마 (Top 종목 5개씩)",
    growth_themes,
    "현재 조건(6개월 수익률 플러스이면서 단기 급등에 포함되지 않은 테마)을 만족하는 테마가 없습니다. "
    "사이드바에서 '카테고리별 표시 테마 수'를 조정해보세요.",
)

st.divider()
st.caption(
    "※ 상단의 새로고침 시각은 페이지가 로드된 시각입니다. 가격 데이터는 30분 캐시(TTL)로 관리되어 실제 시세와 "
    "차이가 날 수 있습니다. 즉시 최신화하려면 상단 '🔄 새로고침' 버튼을 눌러주세요. 테마 분류와 종목 구성은 "
    "투자 참고용 큐레이션이며, 투자 판단의 책임은 본인에게 있습니다."
)
