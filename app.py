"""
배달 플랫폼 수익 시뮬레이터 — Streamlit + Plotly 버전
원본: week4_interactive3.ipynb
실행: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    /* 전체 배경 */
    .stApp { background-color: #0f1117; }
    section[data-testid="stSidebar"] { background-color: #161b27; border-right: 1px solid #2a3148; }
    /* 제목 스타일 */
    .main-title {
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 1.6rem; font-weight: 700;
        color: #e8eaf6; margin-bottom: 0.2rem;
    }
    .sub-title { font-size: 0.85rem; color: #7986cb; margin-bottom: 1.2rem; }
    /* 메트릭 카드 */
    .metric-card {
        background: #1a2035; border: 1px solid #2a3148;
        border-radius: 10px; padding: 14px 18px; text-align: center;
    }
    .metric-label { font-size: 0.75rem; color: #7986cb; margin-bottom: 4px; }
    .metric-value { font-size: 1.4rem; font-weight: 700; color: #e8eaf6; }
    .metric-delta-pos { font-size: 0.8rem; color: #66bb6a; }
    .metric-delta-neg { font-size: 0.8rem; color: #ef5350; }
    /* 섹션 헤더 */
    .section-header {
        font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em;
        text-transform: uppercase; color: #5c6bc0;
        margin: 1.2rem 0 0.5rem 0;
    }
    hr { border-color: #2a3148; margin: 0.8rem 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 1. 데이터 로드 & 전처리 (캐시)
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("food_orders_new_delhi.csv")
    df["Discounts and Offers"] = df["Discounts and Offers"].fillna("0")
    for label in df["Discounts and Offers"].unique():
        idx = df["Discounts and Offers"] == label
        if "%" in str(label):
            df.loc[idx, "Discount"] = float(label.split("%")[0]) * 0.01 * df.loc[idx, "Order Value"]
        elif str(label) == "0":
            df.loc[idx, "Discount"] = 0
        else:
            df.loc[idx, "Discount"] = 50
        df.loc[idx, "Paid"] = df.loc[idx, "Order Value"] - df.loc[idx, "Discount"]
    df["Payment Processing Fee"] = df["Paid"] * 0.033
    return df

@st.cache_data
def compute_baseline(df):
    pp = df["Commission Fee"] - df["Delivery Fee"] - df["Discount"]
    mp = df["Order Value"] - df["Commission Fee"] - df["Payment Processing Fee"] - 0.5 * df["Order Value"]
    return dict(
        platform_margin   = pp.sum() / df["Commission Fee"].sum(),
        merchant_margin   = mp.sum() / df["Order Value"].sum(),
        platform_loss_pct = (pp < 0).mean() * 100,
        merchant_loss_pct = (mp < 0).mean() * 100,
    )

@st.cache_data
def compute_baseline_seg(b1, b2):
    """구간(b1,b2)별 기존(원본 커미션) 플랫폼/식당 마진율 — compute_grid와 동일 필터·구간 정의."""
    df_f = df_raw[df_raw["Paid"] >= B_MIN].reset_index(drop=True)
    comm = df_f["Commission Fee"].values
    ov = df_f["Order Value"].values
    deliv = df_f["Delivery Fee"].values
    disc = df_f["Discount"].values
    proc = df_f["Payment Processing Fee"].values
    paid = df_f["Paid"].values
    pp = comm - deliv - disc
    mp = ov - comm - proc - 0.5 * ov
    m0 = paid < b1
    m1 = (paid >= b1) & (paid < b2)
    m2 = paid >= b2
    pm_list, mm_list = [], []
    for mask in (m0, m1, m2):
        cs_k = float((comm * mask).sum())
        os_k = float((ov * mask).sum())
        pm_list.append(float((pp * mask).sum()) / cs_k * 100 if cs_k > 0 else float("nan"))
        mm_list.append(float((mp * mask).sum()) / os_k * 100 if os_k > 0 else float("nan"))
    return dict(platform_seg=pm_list, merchant_seg=mm_list)

df_raw  = load_data()
BASELINE = compute_baseline(df_raw)
AB_STEP  = 0.1
ab_range = np.round(np.arange(0.0, 1.01, AB_STEP), 2)
a_3d     = ab_range[:, None, None]
b_3d     = ab_range[None, :, None]
B_MIN    = 300

# ─────────────────────────────────────────────
# 2. 사이드바 — 컨트롤
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="main-title">🛵 수익 시뮬레이터</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">변동 커미션 + 배달비/프로모션비 부담 분배</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">① 구간 경계 (최소 주문금액 400루피)</div>', unsafe_allow_html=True)
    b1 = st.slider("경계 1 — 소액|중간", min_value=400, max_value=1800, value=650, step=50)
    b2 = st.slider("경계 2 — 중간|고액", min_value=400, max_value=1800, value=1050, step=50)
    if b1 >= b2:
        st.error(f"⚠️ 경계1({b1}) ≥ 경계2({b2}) — 경계1 < 경계2 이어야 합니다.")

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">② 구간별 커미션율</div>', unsafe_allow_html=True)
    r1 = st.slider("소액 구간 커미션율", 18, 40, 29, format="%d%%") / 100
    r2 = st.slider("중간 구간 커미션율", 12, 40, 26, format="%d%%") / 100
    r3 = st.slider("고액 구간 커미션율",  8, 40, 24, format="%d%%") / 100
    if not (r1 > r2 > r3):
        st.error(f"⚠️ 커미션율 조건 위반: 소액({r1:.0%}) > 중간({r2:.0%}) > 고액({r3:.0%}) 이어야 합니다.")

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">③ 배달비/프로모션비 부담 시뮬레이션</div>', unsafe_allow_html=True)
    a_sel = st.slider("플랫폼 배달비 부담", 0.0, 1.0, 0.5, step=0.1)
    b_sel = st.slider("플랫폼 할인 부담",  0.0, 1.0, 0.5, step=0.1)

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">④ 히트맵 지표</div>', unsafe_allow_html=True)
    metric_options = {
        "플랫폼 마진율":          "platform_margin",
        "식당 마진율":            "merchant_margin",
        "플랫폼 주문당 이익(₹)":  "platform_avg",
        "식당 주문당 이익(₹)":    "merchant_avg",
        "플랫폼 손실 주문(%)":    "platform_loss_pct",
        "식당 손실 주문(%)":      "merchant_loss_pct",
    }
    metric_label = st.selectbox("지표 선택", list(metric_options.keys()))
    metric = metric_options[metric_label]

# ─────────────────────────────────────────────
# 3. 그리드 계산
# ─────────────────────────────────────────────
@st.cache_data
def compute_grid(b1, b2, r1, r2, r3):
    df_f  = df_raw[df_raw["Paid"] >= B_MIN].reset_index(drop=True)
    paid  = df_f["Paid"].values
    ov    = df_f["Order Value"].values
    deliv = df_f["Delivery Fee"].values
    disc  = df_f["Discount"].values
    proc  = df_f["Payment Processing Fee"].values

    m0 = paid < b1
    m1 = (paid >= b1) & (paid < b2)
    m2 = paid >= b2
    comm = ov * (r1*m0 + r2*m1 + r3*m2)

    pp = comm - deliv*a_3d - disc*b_3d
    mp = ov - deliv*(1-a_3d) - disc*(1-b_3d) - comm - proc - 0.5*ov
    cs = comm.sum(); os = ov.sum()

    def seg_margins(mask):
        m3 = mask[np.newaxis, np.newaxis, :]
        cs_k = float((comm * mask).sum())
        os_k = float((ov   * mask).sum())
        pm = (pp*m3).sum(axis=2)/cs_k if cs_k > 0 else np.full((11,11), np.nan)
        mm = (mp*m3).sum(axis=2)/os_k if os_k > 0 else np.full((11,11), np.nan)
        return pm, mm

    pm0, mm0 = seg_margins(m0)
    pm1, mm1 = seg_margins(m1)
    pm2, mm2 = seg_margins(m2)

    return dict(
        platform_margin       = pp.sum(axis=2) / cs,
        merchant_margin       = mp.sum(axis=2) / os,
        platform_avg          = pp.mean(axis=2),
        merchant_avg          = mp.mean(axis=2),
        platform_loss_pct     = (pp < 0).mean(axis=2) * 100,
        merchant_loss_pct     = (mp < 0).mean(axis=2) * 100,
        platform_margin_seg   = (pm0, pm1, pm2),
        merchant_margin_seg   = (mm0, mm1, mm2),
    )

# 유효성 검사
if b1 >= b2 or not (r1 > r2 > r3):
    st.warning("사이드바의 경고를 해결하면 차트가 표시됩니다.")
    st.stop()

res = compute_grid(b1, b2, r1, r2, r3)
BASELINE_SEG = compute_baseline_seg(b1, b2)

# 선택 포인트 인덱스
ai = int(round(a_sel / AB_STEP))
bi = int(round(b_sel / AB_STEP))
pm_sel  = float(res["platform_margin"][ai, bi])
mm_sel  = float(res["merchant_margin"][ai, bi])
plp_sel = float(res["platform_loss_pct"][ai, bi])
mlp_sel = float(res["merchant_loss_pct"][ai, bi])
pm_seg  = [float(res["platform_margin_seg"][k][ai, bi]) for k in range(3)]
mm_seg  = [float(res["merchant_margin_seg"][k][ai, bi]) for k in range(3)]

# ─────────────────────────────────────────────
# 4. 상단 KPI 카드
# ─────────────────────────────────────────────
def delta_html(v, base, invert=False):
    d = v - base
    sign = "+" if d >= 0 else ""
    good = d >= 0 if not invert else d <= 0
    cls = "metric-delta-pos" if good else "metric-delta-neg"
    return f'<span class="{cls}">({sign}{d:.1f}pp)</span>'

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
for col, label, val, base, invert in [
    (kpi1, "플랫폼 마진율",   pm_sel*100,  BASELINE["platform_margin"]*100,   False),
    (kpi2, "식당 마진율",     mm_sel*100,  BASELINE["merchant_margin"]*100,    False),
    (kpi3, "플랫폼 손실 주문", plp_sel,    BASELINE["platform_loss_pct"],      True),
    (kpi4, "식당 손실 주문",  mlp_sel,     BASELINE["merchant_loss_pct"],      True),
]:
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{val:.1f}%</div>
        {delta_html(val, base, invert)}
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 5. 히트맵
# ─────────────────────────────────────────────
grid_vals = res[metric]
grid_flip = grid_vals.T[::-1, :]
y_labels  = [f"{v:.1f}" for v in ab_range[::-1]]
x_labels  = [f"{v:.1f}" for v in ab_range]

cmap_map = {
    "platform_loss_pct": "RdYlGn_r",
    "merchant_loss_pct": "RdYlGn_r",
}
colorscale = "RdYlGn" if metric not in cmap_map else "RdYlGn"
reversescale = metric in cmap_map

fmt_map = {
    "platform_margin": ".2f", "merchant_margin": ".2f",
    "platform_avg": ".0f",    "merchant_avg": ".0f",
    "platform_loss_pct": ".1f", "merchant_loss_pct": ".1f",
}
fmt = fmt_map[metric]

text_vals = [[f"{grid_flip[i][j]:{fmt}}" for j in range(11)] for i in range(11)]

fig_heatmap = go.Figure(go.Heatmap(
    z=grid_flip,
    x=x_labels,
    y=y_labels,
    colorscale=colorscale,
    reversescale=reversescale,
    text=text_vals,
    texttemplate="%{text}",
    textfont={"size": 9},
    hovertemplate="α=%{x}  β=%{y}<br>값=%{z:.3f}<extra></extra>",
    showscale=True,
))

# # 선택 포인트 하이라이트
# ai_x = a_sel
# bi_y = f"{b_sel:.1f}"
# fig_heatmap.add_shape(
#     type="rect",
#     x0=str(float(ai_x) - 0.5) if False else ai_x - 0.5,
#     x1=ai_x + 0.5,
#     y0=b_sel - 0.5,
#     y1=b_sel + 0.5,
#     xref="x", yref="y",
#     line=dict(color="#7986cb", width=3),
# )
# fig_heatmap.add_annotation(
#     x=a_sel, y=b_sel,
#     text=f"●",
#     font=dict(size=18, color="#7986cb"),
#     showarrow=False,
# )

fig_heatmap.update_layout(
    title=dict(
        text=f"<b>{metric_label}</b>  |  boundary=[{b1}, {b2}]  rates=[{r1:.0%}, {r2:.0%}, {r3:.0%}]",
        font=dict(size=13, color="#c5cae9"),
    ),
    xaxis=dict(title="α  (플랫폼 배달비 부담 비율)", tickfont=dict(size=10, color="#9fa8da")),
    yaxis=dict(title="β  (플랫폼 할인 부담 비율)  ↑높음", tickfont=dict(size=10, color="#9fa8da")),
    paper_bgcolor="#1a2035",
    plot_bgcolor="#1a2035",
    font=dict(color="#c5cae9"),
    height=420,
    margin=dict(l=60, r=20, t=50, b=50),
)

st.plotly_chart(fig_heatmap, use_container_width=True)

# ─────────────────────────────────────────────
# 6. 마진율 바 + 손실 주문 바
# ─────────────────────────────────────────────
col_bar1, col_bar2 = st.columns(2)

PLATFORM_COLOR = "#5c6bc0"
MERCHANT_COLOR = "#ef7c5a"
BASE_LINE_COLOR = "#90a4ae"

def make_bar_fig(categories, values, bases, title, ylabel, invert_delta=False):
    deltas = [v - b for v, b in zip(values, bases)]
    colors = [PLATFORM_COLOR, MERCHANT_COLOR]
    bar_colors = []
    for i, (v, b) in enumerate(zip(values, bases)):
        bar_colors.append(colors[i])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories, y=values,
        marker_color=bar_colors,
        text=[f"{v:.1f}%<br><span style='font-size:10px'>({'+' if d>=0 else ''}{d:.1f}pp)</span>"
              for v, d in zip(values, deltas)],
        textposition="outside",
        textfont=dict(size=11, color="#c5cae9"),
        hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
        width=0.45,
    ))
    # 기존 기준선
    for i, (cat, base) in enumerate(zip(categories, bases)):
        fig.add_shape(type="line",
            x0=i-0.3, x1=i+0.3, y0=base, y1=base,
            line=dict(color=BASE_LINE_COLOR, width=1.5, dash="dash"))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines",
        line=dict(color=BASE_LINE_COLOR, width=1.5, dash="dash"),
        name="기존 기준"
    ))
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>  α={a_sel:.1f}  β={b_sel:.1f}", font=dict(size=12, color="#c5cae9")),
        yaxis=dict(title=ylabel, tickfont=dict(color="#9fa8da"), gridcolor="#2a3148"),
        xaxis=dict(tickfont=dict(size=12, color="#c5cae9")),
        paper_bgcolor="#1a2035", plot_bgcolor="#1a2035",
        font=dict(color="#c5cae9"),
        legend=dict(font=dict(size=9), bgcolor="#1a2035"),
        height=320, margin=dict(l=50, r=20, t=45, b=40),
        showlegend=True,
    )
    return fig

with col_bar1:
    st.plotly_chart(
        make_bar_fig(
            ["플랫폼\n마진율", "식당\n마진율"],
            [pm_sel*100, mm_sel*100],
            [BASELINE["platform_margin"]*100, BASELINE["merchant_margin"]*100],
            "마진율 비교", "마진율 (%)"
        ), use_container_width=True
    )

with col_bar2:
    st.plotly_chart(
        make_bar_fig(
            ["플랫폼\n손실 주문", "식당\n손실 주문"],
            [plp_sel, mlp_sel],
            [BASELINE["platform_loss_pct"], BASELINE["merchant_loss_pct"]],
            "손실 주문 비율", "비율 (%)", invert_delta=True
        ), use_container_width=True
    )

# ─────────────────────────────────────────────
# 7. 구간별 마진율 (하단 전체 너비)
# ─────────────────────────────────────────────
seg_lbl = [
    f"소액 (Paid < {b1}₹)",
    f"중간 ({b1}₹ ≤ P < {b2}₹)",
    f"고액 (P ≥ {b2}₹)",
]
h_pm = [v*100 if np.isfinite(v) else 0 for v in pm_seg]
h_mm = [v*100 if np.isfinite(v) else 0 for v in mm_seg]
seg_x = [0, 1, 2]
bpm_base = BASELINE_SEG["platform_seg"]
bmm_base = BASELINE_SEG["merchant_seg"]

fig_seg = go.Figure()
fig_seg.add_trace(go.Bar(
    name="플랫폼 마진율", x=seg_x, y=h_pm,
    marker_color=PLATFORM_COLOR,
    text=[f"{v:.1f}%" for v in h_pm],
    textposition="outside", textfont=dict(size=10, color="#9fa8da"),
    hovertemplate="%{x}<br>플랫폼: %{y:.1f}%<extra></extra>",
    width=0.35,
))
fig_seg.add_trace(go.Bar(
    name="식당 마진율", x=seg_x, y=h_mm,
    marker_color=MERCHANT_COLOR,
    text=[f"{v:.1f}%" for v in h_mm],
    textposition="outside", textfont=dict(size=10, color="#9fa8da"),
    hovertemplate="%{x}<br>식당: %{y:.1f}%<extra></extra>",
    width=0.35,
))
# 구간별 기존 기준선 (그룹 막대: 좌=플랫폼, 우=식당)
for i in seg_x:
    if np.isfinite(bpm_base[i]):
        fig_seg.add_shape(
            type="line",
            x0=i - 0.22,
            x1=i - 0.02,
            y0=bpm_base[i],
            y1=bpm_base[i],
            line=dict(color=BASE_LINE_COLOR, width=1.5, dash="dash"),
            layer="above",
        )
    if np.isfinite(bmm_base[i]):
        fig_seg.add_shape(
            type="line",
            x0=i + 0.02,
            x1=i + 0.22,
            y0=bmm_base[i],
            y1=bmm_base[i],
            line=dict(color=BASE_LINE_COLOR, width=1.5, dash="dash"),
            layer="above",
        )
fig_seg.add_trace(go.Scatter(
    x=[None],
    y=[None],
    mode="lines",
    line=dict(color=BASE_LINE_COLOR, width=1.5, dash="dash"),
    name="기존 기준",
))
fig_seg.add_hline(y=0, line_width=1, line_color="#546e7a")
fig_seg.update_xaxes(
    tickmode="array",
    tickvals=seg_x,
    ticktext=seg_lbl,
    tickfont=dict(size=11, color="#c5cae9"),
)
fig_seg.update_layout(
    barmode="group",
    title=dict(
        text=f"<b>구간별 마진율</b>  α={a_sel:.1f}  β={b_sel:.1f}  |  플랫폼=구간 커미션 합 대비 / 식당=구간 주문금액 합 대비",
        font=dict(size=12, color="#c5cae9"),
    ),
    yaxis=dict(title="마진율 (%)", tickfont=dict(color="#9fa8da"), gridcolor="#2a3148"),
    paper_bgcolor="#1a2035", plot_bgcolor="#1a2035",
    font=dict(color="#c5cae9"),
    legend=dict(orientation="h", x=0.75, y=1.12, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
    height=320, margin=dict(l=50, r=20, t=55, b=40),
    bargap=0.25,
)

st.plotly_chart(fig_seg, use_container_width=True)

# ─────────────────────────────────────────────
# 8. 푸터
# ─────────────────────────────────────────────
st.markdown("""
<hr style='border-color:#2a3148;margin-top:2rem'>
<div style='text-align:center;color:#3d4f7c;font-size:0.75rem;padding-bottom:1rem'>
    배달 플랫폼 수익 시뮬레이터 · 데이터: food_orders_new_delhi.csv (1,000건)
</div>
""", unsafe_allow_html=True)
