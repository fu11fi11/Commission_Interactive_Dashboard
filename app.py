"""
배달 플랫폼 수익 시뮬레이터 — Streamlit + Plotly 버전
원본: week4_interactive3.ipynb + bypromo_interactive.ipynb
실행: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import itertools

# ─────────────────────────────────────────────
# 0. 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="배달 플랫폼 수익 시뮬레이터",
    page_icon="🛵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0f1117; }
    section[data-testid="stSidebar"] { background-color: #161b27; border-right: 1px solid #2a3148; }
    .main-title { font-family: 'Noto Sans KR', sans-serif; font-size: 1.6rem; font-weight: 700; color: #e8eaf6; margin-bottom: 0.2rem; }
    .sub-title { font-size: 0.85rem; color: #7986cb; margin-bottom: 1.2rem; }
    .metric-card { background: #1a2035; border: 1px solid #2a3148; border-radius: 10px; padding: 14px 18px; text-align: center; }
    .metric-label { font-size: 0.75rem; color: #7986cb; margin-bottom: 4px; }
    .metric-value { font-size: 1.4rem; font-weight: 700; color: #e8eaf6; }
    .metric-delta-pos { font-size: 0.8rem; color: #66bb6a; }
    .metric-delta-neg { font-size: 0.8rem; color: #ef5350; }
    .section-header { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: #5c6bc0; margin: 1.2rem 0 0.5rem 0; }
    .mobile-warning { background: #1c2033; border-left: 3px solid #f9a825; border-radius: 6px; padding: 10px 16px; color: #fdd835; font-size: 0.82rem; margin-bottom: 1rem; }
    hr { border-color: #2a3148; margin: 0.8rem 0; }
</style>
""", unsafe_allow_html=True)

# ① 세로화면 경고 (최상단)
st.markdown("""
<div class="mobile-warning">
    📱 <b>스마트폰 세로 화면</b>에서는 차트와 사이드바가 제대로 표시되지 않을 수 있습니다.
    가로 방향으로 전환하거나 PC/태블릿 환경을 권장합니다.
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 1. 데이터 로드
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("food_orders_new_delhi.csv")
    df["Discounts and Offers"] = df["Discounts and Offers"].fillna("0")
    for label in df["Discounts and Offers"].unique():
        idx = df["Discounts and Offers"] == label
        if "%" in str(label):
            df.loc[idx, "Discount"] = float(str(label).split("%")[0]) * 0.01 * df.loc[idx, "Order Value"]
        elif str(label) == "0":
            df.loc[idx, "Discount"] = 0
        else:
            df.loc[idx, "Discount"] = 50
        df.loc[idx, "Paid"] = df.loc[idx, "Order Value"] - df.loc[idx, "Discount"]
    df["Payment Processing Fee"] = df["Paid"] * 0.033
    def parse_promo(label):
        if "%" in str(label):
            return float(str(label).split("%")[0])
        elif "50" in str(label):
            return -1.0
        else:
            return 0.0
    df["promo_pct"] = df["Discounts and Offers"].apply(parse_promo)
    return df

@st.cache_data
def compute_baseline(_df):
    pp = _df["Commission Fee"] - _df["Delivery Fee"] - _df["Discount"]
    mp = _df["Order Value"] - _df["Commission Fee"] - _df["Payment Processing Fee"] - 0.5 * _df["Order Value"]
    df2 = _df.copy()
    df2["pp"] = pp; df2["mp"] = mp
    by_promo = df2.groupby("Discounts and Offers").apply(
        lambda g: pd.Series({
            "platform_margin": g["pp"].sum() / g["Commission Fee"].sum(),
            "merchant_margin":  g["mp"].sum() / g["Order Value"].sum(),
        })
    ).reset_index()
    return dict(
        platform_margin   = pp.sum() / _df["Commission Fee"].sum(),
        merchant_margin   = mp.sum() / _df["Order Value"].sum(),
        platform_loss_pct = (pp < 0).mean() * 100,
        merchant_loss_pct = (mp < 0).mean() * 100,
        by_promo          = by_promo,
    )

df_raw   = load_data()
BASELINE = compute_baseline(df_raw)
AB_STEP  = 0.1
ab_range = np.round(np.arange(0.0, 1.01, AB_STEP), 2)
a_3d     = ab_range[:, None, None]
b_3d     = ab_range[None, :, None]
B_MIN    = 300
DIVISOR  = 5

# ─────────────────────────────────────────────
# 2. 사이드바
# ─────────────────────────────────────────────
PLATFORM_COLOR  = "#5c6bc0"
PLATFORM_COLOR_ORIG = "#c07f5c"
MERCHANT_COLOR  = "#ef7c5a"
MERCHANT_COLOR_ORIG = "#5aefc6"
BASE_LINE_COLOR = "#f9a825"   # ② 눈에 띄는 노란색

with st.sidebar:
    st.markdown('<div class="main-title">🛵 수익 시뮬레이터</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">변동 커미션 × α/β 부담 분배</div>', unsafe_allow_html=True)
    sim_mode = st.radio("시뮬레이션 모드", ["📦 구간별 커미션", "🎁 프로모별 커미션"], horizontal=True)
    st.markdown('<hr>', unsafe_allow_html=True)

    if sim_mode == "📦 구간별 커미션":
        st.markdown('<div class="section-header">① 구간 경계 (Paid 기준 ₹)</div>', unsafe_allow_html=True)
        b1 = st.slider("경계 1 — 소액|중간", 400, 1800, 650, step=50)
        b2 = st.slider("경계 2 — 중간|고액", 400, 1800, 1050, step=50)
        if b1 >= b2:
            st.error(f"⚠️ 경계1({b1}) ≥ 경계2({b2})")
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">② 구간별 커미션율</div>', unsafe_allow_html=True)
        r1 = st.slider("소액 구간 커미션율", 18, 40, 29, format="%d%%") / 100
        r2 = st.slider("중간 구간 커미션율", 12, 40, 26, format="%d%%") / 100
        r3 = st.slider("고액 구간 커미션율",  8, 40, 24, format="%d%%") / 100
        if not (r1 > r2 > r3):
            st.error(f"⚠️ 소액 > 중간 > 고액 순서 필요")
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">③ α/β 상세 탐색</div>', unsafe_allow_html=True)
        a_sel = st.slider("α — 플랫폼 배달비 부담", 0.0, 1.0, 0.5, step=0.1)
        b_sel = st.slider("β — 플랫폼 할인 부담",  0.0, 1.0, 0.5, step=0.1)
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">④ 히트맵 지표</div>', unsafe_allow_html=True)
        metric_options = {
            "플랫폼 마진율": "platform_margin", "식당 마진율": "merchant_margin",
            "플랫폼 주문당 이익(₹)": "platform_avg", "식당 주문당 이익(₹)": "merchant_avg",
            "플랫폼 손실 주문(%)": "platform_loss_pct", "식당 손실 주문(%)": "merchant_loss_pct",
        }
        metric_label = st.selectbox("지표 선택", list(metric_options.keys()))
        metric = metric_options[metric_label]

    else:
        st.markdown('<div class="section-header">① 기본 커미션율 (base)</div>', unsafe_allow_html=True)
        p_base = st.slider("기본 커미션율", 10, 20, 14, format="%d%%") / 100
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">② 할인율 → 추가 커미션 계수</div>', unsafe_allow_html=True)
        st.caption(f"추가율 = 할인율 ÷ {DIVISOR} × multiplier")
        p_mult = st.slider("multiplier", 6, 14, 10, format="%d%%") / 100
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">③ 정액 할인(₹50) 추가 커미션율</div>', unsafe_allow_html=True)
        p_flat = st.slider("flat_extra", 10, 20, 14, format="%d%%") / 100
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">④ α/β (배달비·할인 부담)</div>', unsafe_allow_html=True)
        pa_sel = st.slider("α — 배달비 부담", 0.0, 1.0, 1.0, step=0.1, key="pa")
        pb_sel = st.slider("β — 할인 부담",  0.0, 1.0, 1.0, step=0.1, key="pb")
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">⑤ 히트맵 지표 (base × multiplier)</div>', unsafe_allow_html=True)
        p_metric_options = {
            "플랫폼 마진율": "platform_margin", "식당 마진율": "merchant_margin",
            "플랫폼 주문당 이익(₹)": "platform_avg", "식당 주문당 이익(₹)": "merchant_avg",
            "플랫폼 손실 주문(%)": "platform_loss_pct", "식당 손실 주문(%)": "merchant_loss_pct",
        }
        p_metric_label = st.selectbox("지표 선택", list(p_metric_options.keys()), key="pm")
        p_metric = p_metric_options[p_metric_label]

# ─────────────────────────────────────────────
# 공통 헬퍼
# ─────────────────────────────────────────────
def delta_html(v, base, invert=False):
    d = v - base
    sign = "+" if d >= 0 else ""
    good = (d >= 0) if not invert else (d <= 0)
    cls = "metric-delta-pos" if good else "metric-delta-neg"
    return f'<span class="{cls}">({sign}{d:.1f}pp vs 기존)</span>'

def dark_layout(fig, title_text, height=320):
    fig.update_layout(
        title=dict(text=title_text, font=dict(size=12, color="#c5cae9")),
        paper_bgcolor="#1a2035", plot_bgcolor="#1a2035",
        font=dict(color="#c5cae9"),
        yaxis=dict(tickfont=dict(color="#9fa8da"), gridcolor="#2a3148"),
        xaxis=dict(tickfont=dict(size=11, color="#c5cae9")),
        legend=dict(font=dict(size=9), bgcolor="#1a2035"),
        height=height, margin=dict(l=50, r=20, t=50, b=40),
    )

def make_bar_fig(categories, values, bases, title, ylabel, alpha=None, beta=None):
    deltas = [v - b for v, b in zip(values, bases)]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories, y=values,
        marker_color=[PLATFORM_COLOR, MERCHANT_COLOR],
        text=[f"{v:.1f}%<br><span style='font-size:10px'>({'+' if d>=0 else ''}{d:.1f}pp)</span>"
              for v, d in zip(values, deltas)],
        textposition="outside", textfont=dict(size=11, color="#c5cae9"),
        hovertemplate="%{x}: %{y:.2f}%<extra></extra>", width=0.45,
    ))
    # ② 노란 점선 + ③ 가로 길이 확장 (-0.45 ~ +0.45)
    for i, base in enumerate(bases):
        fig.add_shape(type="line", x0=i-0.45, x1=i+0.45, y0=base, y1=base,
            line=dict(color=BASE_LINE_COLOR, width=2.5, dash="dash"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
        line=dict(color=BASE_LINE_COLOR, width=2.5, dash="dash"), name="기존 기준"))
    ab_str = f"  α={alpha:.1f}  β={beta:.1f}" if alpha is not None else ""
    dark_layout(fig, f"<b>{title}</b>{ab_str}", height=320)
    fig.update_layout(yaxis_title=ylabel, showlegend=True)
    return fig

def kpi_row(vals):
    """vals: list of (label, value, baseline, invert)"""
    cols = st.columns(4)
    for col, (label, val, base, invert) in zip(cols, vals):
        col.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{val:.1f}%</div>
            {delta_html(val, base, invert)}
        </div>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# MODE A: 구간별 커미션
# ═══════════════════════════════════════════
if sim_mode == "📦 구간별 커미션":

    @st.cache_data
    def compute_grid_tier(b1, b2, r1, r2, r3):
        df_f  = df_raw[df_raw["Paid"] >= B_MIN].reset_index(drop=True)
        paid  = df_f["Paid"].values; ov = df_f["Order Value"].values
        deliv = df_f["Delivery Fee"].values; disc = df_f["Discount"].values
        proc  = df_f["Payment Processing Fee"].values
        m0 = paid < b1; m1 = (paid >= b1) & (paid < b2); m2 = paid >= b2
        comm = paid * (r1*m0 + r2*m1 + r3*m2)
        pp = comm - deliv*a_3d - disc*b_3d
        mp = ov - deliv*(1-a_3d) - disc*(1-b_3d) - comm - proc - 0.5*ov
        cs = comm.sum(); os = ov.sum()
        
        def seg(mask):
            m3 = mask[np.newaxis, np.newaxis, :]
            cs_k = float((comm*mask).sum()); os_k = float((ov*mask).sum())
            return ((pp*m3).sum(axis=2)/cs_k if cs_k>0 else np.full((11,11),np.nan),
                    (mp*m3).sum(axis=2)/os_k if os_k>0 else np.full((11,11),np.nan))
        pm0,mm0 = seg(m0); pm1,mm1 = seg(m1); pm2,mm2 = seg(m2)

        # 기존 구조(원래 Commission Fee 그대로)로 구간별 마진 계산
        orig_comm = df_f["Commission Fee"].values  # 이미 df_f 범위로 필터됨
        orig_pp   = orig_comm - deliv - disc       # α=β=원래구조 → 배달비·할인 전액 플랫폼 부담
        orig_mp   = ov - orig_comm - proc - 0.5*ov

        def orig_seg(mask):
            cs_k = float((orig_comm * mask).sum())
            os_k = float((ov * mask).sum())
            pm = float((orig_pp * mask).sum()) / cs_k if cs_k > 0 else np.nan
            mm = float((orig_mp * mask).sum()) / os_k if os_k > 0 else np.nan
            return pm, mm

        orig_pm0, orig_mm0 = orig_seg(m0)
        orig_pm1, orig_mm1 = orig_seg(m1)
        orig_pm2, orig_mm2 = orig_seg(m2)

        return dict(
            platform_margin=pp.sum(axis=2)/cs, merchant_margin=mp.sum(axis=2)/os,
            platform_avg=pp.mean(axis=2), merchant_avg=mp.mean(axis=2),
            platform_loss_pct=(pp<0).mean(axis=2)*100, merchant_loss_pct=(mp<0).mean(axis=2)*100,
            platform_margin_seg=(pm0,pm1,pm2), merchant_margin_seg=(mm0,mm1,mm2),
            baseline_seg_pm = (orig_pm0, orig_pm1, orig_pm2),
            baseline_seg_mm = (orig_mm0, orig_mm1, orig_mm2),
        )

    if b1 >= b2 or not (r1 > r2 > r3):
        st.warning("사이드바의 경고를 해결하면 차트가 표시됩니다.")
        st.stop()

    res = compute_grid_tier(b1, b2, r1, r2, r3)
    ai = int(round(a_sel/AB_STEP)); bi_i = int(round(b_sel/AB_STEP))
    pm_sel  = float(res["platform_margin"][ai, bi_i])
    mm_sel  = float(res["merchant_margin"][ai, bi_i])
    plp_sel = float(res["platform_loss_pct"][ai, bi_i])
    mlp_sel = float(res["merchant_loss_pct"][ai, bi_i])
    pm_seg  = [float(res["platform_margin_seg"][k][ai, bi_i]) for k in range(3)]
    mm_seg  = [float(res["merchant_margin_seg"][k][ai, bi_i]) for k in range(3)]

    kpi_row([
        ("플랫폼 마진율",   pm_sel*100,  BASELINE["platform_margin"]*100,  False),
        ("식당 마진율",     mm_sel*100,  BASELINE["merchant_margin"]*100,   False),
        ("플랫폼 손실 주문", plp_sel,    BASELINE["platform_loss_pct"],     True),
        ("식당 손실 주문",  mlp_sel,     BASELINE["merchant_loss_pct"],     True),
    ])

    # 히트맵
    gv   = res[metric]
    gv_f = gv.T[::-1, :]
    fmt_map = {"platform_margin":".2f","merchant_margin":".2f","platform_avg":".0f",
               "merchant_avg":".0f","platform_loss_pct":".1f","merchant_loss_pct":".1f"}
    fmt = fmt_map[metric]
    fig_hm = go.Figure(go.Heatmap(
        z=gv_f, x=[f"{v:.1f}" for v in ab_range], y=[f"{v:.1f}" for v in ab_range[::-1]],
        colorscale="RdYlGn", reversescale=(metric in ("platform_loss_pct","merchant_loss_pct")),
        text=[[f"{gv_f[i][j]:{fmt}}" for j in range(11)] for i in range(11)],
        texttemplate="%{text}", textfont={"size":9},
        hovertemplate="α=%{x}  β=%{y}<br>값=%{z:.3f}<extra></extra>", showscale=True,
    ))
    fig_hm.update_layout(
        title=dict(text=f"<b>{metric_label}</b>  |  boundary=[{b1},{b2}]  rates=[{r1:.0%},{r2:.0%},{r3:.0%}]",
                   font=dict(size=13, color="#c5cae9")),
        xaxis=dict(title="α  (플랫폼 배달비 부담 비율)", tickfont=dict(size=10, color="#9fa8da")),
        yaxis=dict(title="β  (플랫폼 할인 부담 비율)  ↑높음", tickfont=dict(size=10, color="#9fa8da")),
        paper_bgcolor="#1a2035", plot_bgcolor="#1a2035", font=dict(color="#c5cae9"),
        height=420, margin=dict(l=60, r=20, t=50, b=50),
    )
    st.plotly_chart(fig_hm, use_container_width=True)

    # 마진율 / 손실 바
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(make_bar_fig(
            ["플랫폼\n마진율","식당\n마진율"],
            [pm_sel*100, mm_sel*100],
            [BASELINE["platform_margin"]*100, BASELINE["merchant_margin"]*100],
            "마진율 비교","마진율 (%)", a_sel, b_sel), use_container_width=True)
    with c2:
        st.plotly_chart(make_bar_fig(
            ["플랫폼\n손실 주문","식당\n손실 주문"],
            [plp_sel, mlp_sel],
            [BASELINE["platform_loss_pct"], BASELINE["merchant_loss_pct"]],
            "손실 주문 비율","비율 (%)", a_sel, b_sel), use_container_width=True)

    # 구간별 마진율
    seg_lbl = [f"소액 (< {b1}₹)", f"중간 ({b1}–{b2}₹)", f"고액 (≥ {b2}₹)"]
    h_pm = [v*100 if np.isfinite(v) else 0 for v in pm_seg]
    h_mm = [v*100 if np.isfinite(v) else 0 for v in mm_seg]

    # ③ 구간별 마진율 기준선 (기존 구조)
    seg_pm_base = [v * 100 if np.isfinite(v) else None for v in res["baseline_seg_pm"]]
    seg_mm_base = [v * 100 if np.isfinite(v) else None for v in res["baseline_seg_mm"]]

    # 텍스트에 "(+x.xpp)" 형식으로 기존 대비 차이 표시
    pm_text = []
    mm_text = []
    for v, base in zip(h_pm, seg_pm_base):
        if base is None:
            pm_text.append(f"{v:.1f}%")
        else:
            d = v - base
            sign = "+" if d >= 0 else ""
            pm_text.append(f"{v:.1f}%<br><span style='font-size:10px'>({sign}{d:.1f}pp)</span>")
    for v, base in zip(h_mm, seg_mm_base):
        if base is None:
            mm_text.append(f"{v:.1f}%")
        else:
            d = v - base
            sign = "+" if d >= 0 else ""
            mm_text.append(f"{v:.1f}%<br><span style='font-size:10px'>({sign}{d:.1f}pp)</span>")

    fig_seg = go.Figure()
    fig_seg.add_trace(go.Bar(name="플랫폼 마진율", x=seg_lbl, y=h_pm, marker_color=PLATFORM_COLOR,
        text=pm_text, textposition="outside",
        textfont=dict(size=10, color="#9fa8da"), width=0.35,
        hovertemplate="%{x}<br>플랫폼: %{y:.1f}%<extra></extra>"))
    fig_seg.add_trace(go.Bar(name="식당 마진율", x=seg_lbl, y=h_mm, marker_color=MERCHANT_COLOR,
        text=mm_text, textposition="outside",
        textfont=dict(size=10, color="#9fa8da"), width=0.35,
        hovertemplate="%{x}<br>식당: %{y:.1f}%<extra></extra>"))
    for i in range(len(seg_lbl)):
        # 플랫폼 기존기준 
        if seg_pm_base[i] is not None:
            fig_seg.add_shape(type="line",
                x0=i - 0.45, x1=i - 0.02,
                y0=seg_pm_base[i], y1=seg_pm_base[i],
                line=dict(color=PLATFORM_COLOR_ORIG, width=2, dash="dash"), opacity=0.8)
        # 식당 기존기준 — 식당 바 위치만 (x0=i+0.02 ~ x1=i+0.45)
        if seg_mm_base[i] is not None:
            fig_seg.add_shape(type="line",
                x0=i + 0.02, x1=i + 0.45,
                y0=seg_mm_base[i], y1=seg_mm_base[i],
                line=dict(color=MERCHANT_COLOR_ORIG, width=2, dash="dash"), opacity=0.8)

    fig_seg.add_trace(go.Scatter(x=[None],y=[None],mode="lines",
        line=dict(color=PLATFORM_COLOR,width=2,dash="dash"), name="플랫폼 기존기준", opacity=0.8))
    fig_seg.add_trace(go.Scatter(x=[None],y=[None],mode="lines",
        line=dict(color=MERCHANT_COLOR,width=2,dash="dash"), name="식당 기존기준", opacity=0.8))
    fig_seg.add_hline(y=0, line_width=1, line_color="#546e7a")
    dark_layout(fig_seg,
        f"<b>구간별 마진율</b>  α={a_sel:.1f}  β={b_sel:.1f}  |  플랫폼=구간 커미션 합 대비 / 식당=구간 주문금액 합 대비",
        height=340)
    fig_seg.update_layout(barmode="group", yaxis_title="마진율 (%)", bargap=0.25,
        legend=dict(orientation="h", x=0.5, y=1.13, font=dict(size=9), bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig_seg, use_container_width=True)


# ═══════════════════════════════════════════
# MODE B: 프로모별 커미션
# ═══════════════════════════════════════════
else:
    MIN_PAID = 500
    df_f     = df_raw[df_raw["Paid"] >= MIN_PAID].copy()
    # 프로모 유형을 표시용 레이블로 정렬 (카테고리 순서 고정)
    promo_order = sorted(df_f["Discounts and Offers"].unique().tolist())
 
    ov_np    = df_f["Order Value"].values
    deliv_np = df_f["Delivery Fee"].values
    disc_np  = df_f["Discount"].values
    proc_np  = df_f["Payment Processing Fee"].values
    pct_np   = df_f["promo_pct"].values
    promo_np = df_f["Discounts and Offers"].values
    mask_none = pct_np == 0.0
    mask_flat = pct_np == -1.0
    mask_pct  = pct_np > 0
 
    @st.cache_data
    def compute_promo_grid(p_base, p_mult, p_flat, pa, pb):
        bv = np.round(np.arange(0.10, 0.205, 0.02), 4)
        mv = np.round(np.arange(0.06, 0.145, 0.02), 4)
        n_b, n_m = len(bv), len(mv)
        gpm=np.zeros((n_b,n_m)); gmm=np.zeros_like(gpm)
        gpa=np.zeros_like(gpm);  gma=np.zeros_like(gpm)
        gplp=np.zeros_like(gpm); gmlp=np.zeros_like(gpm)
        os_sum = ov_np.sum()
        for i, b_ in enumerate(bv):
            for j, m_ in enumerate(mv):
                ar  = np.where(mask_none, 0., np.where(mask_flat, p_flat, pct_np*mask_pct/DIVISOR*m_))
                c_  = ov_np * (b_ + ar)
                pp_ = c_ - deliv_np*pa - disc_np*pb
                mp_ = ov_np - deliv_np*(1-pa) - disc_np*(1-pb) - c_ - proc_np - 0.5*ov_np
                cs_ = c_.sum()
                gpm[i,j]=pp_.sum()/cs_;  gmm[i,j]=mp_.sum()/os_sum
                gpa[i,j]=pp_.mean();     gma[i,j]=mp_.mean()
                gplp[i,j]=(pp_<0).mean()*100; gmlp[i,j]=(mp_<0).mean()*100
        return dict(base_vals=bv, mult_vals=mv,
            platform_margin=gpm, merchant_margin=gmm,
            platform_avg=gpa,    merchant_avg=gma,
            platform_loss_pct=gplp, merchant_loss_pct=gmlp)
 
    @st.cache_data
    def compute_promo_point(p_base, p_mult, p_flat, pa, pb):
        ar   = np.where(mask_none, 0., np.where(mask_flat, p_flat, pct_np*mask_pct/DIVISOR*p_mult))
        comm = ov_np * (p_base + ar)
        pp   = comm - deliv_np*pa - disc_np*pb
        mp   = ov_np - deliv_np*(1-pa) - disc_np*(1-pb) - comm - proc_np - 0.5*ov_np
        cs = comm.sum(); os = ov_np.sum()
        rows = []
        for pt in promo_order:
            mask = promo_np == pt
            if not mask.any(): continue
            cs_k = float(comm[mask].sum()); os_k = float(ov_np[mask].sum())
            rows.append({
                "프로모 유형":   pt,
                "건수":          int(mask.sum()),
                "플랫폼 마진율": pp[mask].sum()/cs_k if cs_k > 0 else np.nan,
                "식당 마진율":   mp[mask].sum()/os_k if os_k > 0 else np.nan,
                "플랫폼 손실%":  (pp[mask] < 0).mean() * 100,
                "식당 손실%":    (mp[mask] < 0).mean() * 100,
            })
        return dict(
            platform_margin   = pp.sum() / cs,
            merchant_margin   = mp.sum() / os,
            platform_loss_pct = (pp < 0).mean() * 100,
            merchant_loss_pct = (mp < 0).mean() * 100,
            by_promo          = pd.DataFrame(rows),   # 이미 promo_order 순서
        )
 
    pgrid = compute_promo_grid(p_base, p_mult, p_flat, pa_sel, pb_sel)
    pres  = compute_promo_point(p_base, p_mult, p_flat, pa_sel, pb_sel)
 
    # KPI
    kpi_row([
        ("플랫폼 마진율",    pres["platform_margin"]*100,  BASELINE["platform_margin"]*100,  False),
        ("식당 마진율",      pres["merchant_margin"]*100,  BASELINE["merchant_margin"]*100,   False),
        ("플랫폼 손실 주문", pres["platform_loss_pct"],    BASELINE["platform_loss_pct"],     True),
        ("식당 손실 주문",   pres["merchant_loss_pct"],    BASELINE["merchant_loss_pct"],     True),
    ])
 
    # ── base × multiplier 히트맵 ──────────────────────────────
    bv = pgrid["base_vals"]; mv = pgrid["mult_vals"]
    gv = pgrid[p_metric];    gv_f = gv[::-1, :]
    fmt_map = {"platform_margin":".2f","merchant_margin":".2f","platform_avg":".0f",
               "merchant_avg":".0f","platform_loss_pct":".1f","merchant_loss_pct":".1f"}
    p_fmt  = fmt_map[p_metric]
    p_text = [[f"{gv_f[i][j]:{p_fmt}}" for j in range(len(mv))] for i in range(len(bv))]
    bi_idx = int(np.argmin(np.abs(bv - p_base)))
    mi_idx = int(np.argmin(np.abs(mv - p_mult)))
    n_row  = len(bv) - 1 - bi_idx
 
    fig_phm = go.Figure(go.Heatmap(
        z=gv_f,
        x=[f"{v:.0%}" for v in mv],
        y=[f"{v:.0%}" for v in bv[::-1]],
        colorscale="RdYlGn",
        reversescale=(p_metric in ("platform_loss_pct", "merchant_loss_pct")),
        text=p_text, texttemplate="%{text}", textfont={"size": 10},
        hovertemplate="multiplier=%{x}<br>base=%{y}<br>값=%{z:.3f}<extra></extra>",
        showscale=True,
    ))
    fig_phm.add_shape(type="rect",
        x0=mi_idx-0.5, x1=mi_idx+0.5, y0=n_row-0.5, y1=n_row+0.5,
        xref="x", yref="y", line=dict(color=BASE_LINE_COLOR, width=3))
    fig_phm.update_layout(
        title=dict(
            text=f"<b>{p_metric_label}</b>  |  flat={p_flat:.0%}  α={pa_sel:.1f}  β={pb_sel:.1f}",
            font=dict(size=13, color="#c5cae9")),
        xaxis=dict(title="multiplier (할인율 → 추가 커미션 계수)",
                   type="category", tickfont=dict(size=10, color="#9fa8da")),
        yaxis=dict(title="base_rate (기본 커미션율)",
                   type="category", tickfont=dict(size=10, color="#9fa8da")),
        paper_bgcolor="#1a2035", plot_bgcolor="#1a2035", font=dict(color="#c5cae9"),
        height=360, margin=dict(l=60, r=20, t=55, b=50),
    )
    st.plotly_chart(fig_phm, use_container_width=True)
 
    # ── 전체 마진율 / 손실 바 ─────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(make_bar_fig(
            ["플랫폼\n마진율", "식당\n마진율"],
            [pres["platform_margin"]*100, pres["merchant_margin"]*100],
            [BASELINE["platform_margin"]*100, BASELINE["merchant_margin"]*100],
            "전체 마진율 비교", "마진율 (%)", pa_sel, pb_sel), use_container_width=True)
    with c2:
        st.plotly_chart(make_bar_fig(
            ["플랫폼\n손실 주문", "식당\n손실 주문"],
            [pres["platform_loss_pct"], pres["merchant_loss_pct"]],
            [BASELINE["platform_loss_pct"], BASELINE["merchant_loss_pct"]],
            "전체 손실 주문 비율", "비율 (%)", pa_sel, pb_sel), use_container_width=True)
 
    # ── 프로모별 마진율 비교 ──────────────────────────────────
    bp  = pres["by_promo"]
    bl  = BASELINE["by_promo"].set_index("Discounts and Offers")
    pts = bp["프로모 유형"].tolist()   # promo_order 순서 보장
 
    pm_vals = [v * 100 for v in bp["플랫폼 마진율"]]
    mm_vals = [v * 100 for v in bp["식당 마진율"]]
    pm_base = [bl.loc[pt, "platform_margin"] * 100 if pt in bl.index else np.nan for pt in pts]
    mm_base = [bl.loc[pt, "merchant_margin"] * 100  if pt in bl.index else np.nan for pt in pts]
 
    # x축을 category로 강제 → add_shape의 x 좌표가 인덱스 정수로 정확히 대응
    fig_promo = go.Figure()
    fig_promo.add_trace(go.Bar(
        name="플랫폼 마진율", x=pts, y=pm_vals,
        marker_color=PLATFORM_COLOR,
        text=[f"{v:.1f}%" for v in pm_vals],
        textposition="outside", textfont=dict(size=9, color="#9fa8da"),
        hovertemplate="%{x}<br>플랫폼: %{y:.1f}%<extra></extra>",
        width=0.35,
    ))
    fig_promo.add_trace(go.Bar(
        name="식당 마진율", x=pts, y=mm_vals,
        marker_color=MERCHANT_COLOR,
        text=[f"{v:.1f}%" for v in mm_vals],
        textposition="outside", textfont=dict(size=9, color="#9fa8da"),
        hovertemplate="%{x}<br>식당: %{y:.1f}%<extra></extra>",
        width=0.35,
    ))
    # 기존 기준 점선: category 축에서 정수 인덱스로 위치 지정
    # grouped bar에서 플랫폼 바 중심 = i-0.175, 식당 바 중심 = i+0.175
    for i, (pb_v, mb_v) in enumerate(zip(pm_base, mm_base)):
        if not np.isnan(pb_v):
            fig_promo.add_shape(type="line",
                xref="x", yref="y",
                x0=i - 0.45, x1=i - 0.02,
                y0=pb_v, y1=pb_v,
                line=dict(color=BASE_LINE_COLOR, width=2.5, dash="dash"))
        if not np.isnan(mb_v):
            fig_promo.add_shape(type="line",
                xref="x", yref="y",
                x0=i + 0.02, x1=i + 0.45,
                y0=mb_v, y1=mb_v,
                line=dict(color=BASE_LINE_COLOR, width=2.5, dash="dash"))
    fig_promo.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines",
        line=dict(color=BASE_LINE_COLOR, width=2.5, dash="dash"),
        name="기존 기준"))
    fig_promo.add_hline(y=0, line_width=1, line_color="#546e7a")
    dark_layout(fig_promo,
        f"<b>프로모 유형별 마진율</b>  base={p_base:.0%}  mult={p_mult:.0%}  flat={p_flat:.0%}",
        height=400)
    fig_promo.update_layout(
        barmode="group",
        yaxis_title="마진율 (%)",
        bargap=0.3,
        xaxis=dict(type="category", tickfont=dict(size=10, color="#c5cae9")),
        legend=dict(orientation="h", x=0.6, y=1.1, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_promo, use_container_width=True)
 
    # # ── 프로모별 손실 주문 ────────────────────────────────────
    # plp_vals = bp["플랫폼 손실%"].tolist()
    # mlp_vals = bp["식당 손실%"].tolist()
 
    # fig_ploss = go.Figure()
    # fig_ploss.add_trace(go.Bar(
    #     name="플랫폼 손실%", x=pts, y=plp_vals,
    #     marker_color=PLATFORM_COLOR,
    #     text=[f"{v:.1f}%" for v in plp_vals],
    #     textposition="outside", textfont=dict(size=9, color="#9fa8da"),
    #     hovertemplate="%{x}<br>플랫폼: %{y:.1f}%<extra></extra>",
    #     width=0.35,
    # ))
    # fig_ploss.add_trace(go.Bar(
    #     name="식당 손실%", x=pts, y=mlp_vals,
    #     marker_color=MERCHANT_COLOR,
    #     text=[f"{v:.1f}%" for v in mlp_vals],
    #     textposition="outside", textfont=dict(size=9, color="#9fa8da"),
    #     hovertemplate="%{x}<br>식당: %{y:.1f}%<extra></extra>",
    #     width=0.35,
    # ))
    # fig_ploss.add_hline(y=0, line_width=1, line_color="#546e7a")
    # dark_layout(fig_ploss, "<b>프로모 유형별 손실 주문 비율</b>", height=360)
    # fig_ploss.update_layout(
    #     barmode="group",
    #     yaxis_title="손실 주문 비율 (%)",
    #     bargap=0.3,
    #     xaxis=dict(type="category", tickfont=dict(size=10, color="#c5cae9")),
    #     legend=dict(orientation="h", x=0.7, y=1.1, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
    # )
    # st.plotly_chart(fig_ploss, use_container_width=True)
 
    # ── 상세 테이블 ───────────────────────────────────────────
    with st.expander("📋 프로모별 상세 수치"):
        disp = bp.copy()
        disp["플랫폼 마진율"] = disp["플랫폼 마진율"].map(lambda x: f"{x*100:.1f}%")
        disp["식당 마진율"]   = disp["식당 마진율"].map(lambda x: f"{x*100:.1f}%")
        disp["플랫폼 손실%"] = disp["플랫폼 손실%"].map(lambda x: f"{x:.1f}%")
        disp["식당 손실%"]   = disp["식당 손실%"].map(lambda x: f"{x:.1f}%")
        st.dataframe(disp, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# 푸터
# ─────────────────────────────────────────────
st.markdown("""
<hr style='border-color:#2a3148;margin-top:2rem'>
<div style='text-align:center;color:#3d4f7c;font-size:0.75rem;padding-bottom:1rem'>
    배달 플랫폼 수익 시뮬레이터 · 데이터: Kaggle - food_orders_new_delhi.csv (1,000건)
</div>
""", unsafe_allow_html=True)