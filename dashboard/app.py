"""
Dashboard Profissional - Macro Scoring WIN
============================================
Mesa de trading 600x1000 para acompanhamento em tempo real.
Design inspirado em terminais Bloomberg/Refinitiv.

Para rodar: streamlit run dashboard/app.py
"""

import sys
import os
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config import (
    MT5_CONFIG, DUAL_SOURCE_ASSETS, YF_SYMBOLS, MACRO_WEIGHTS,
    SIGNAL_CONFIG, CATEGORIES, DASHBOARD_CONFIG, LOG_CONFIG,
    WIN_TRACKING, DIVERGENCE_CONFIG
)
from data_sources.data_manager import DataManager
from scoring.macro_score import MacroScorer
from scoring.delta import DeltaAnalyzer
from scoring.divergence import DivergenceDetector
from utils.helpers import format_change, format_price, get_change_color, get_score_color
from utils.macro_logger import MacroLogger
from dashboard.analysis_tab import render_analysis_tab

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACAO DA PAGINA
# ============================================================
st.set_page_config(
    page_title="Macro WIN",
    page_icon="W",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# CSS PROFISSIONAL - MESA DE TRADING
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600;700;800&display=swap');

    /* ROOT */
    .stApp { background-color: #0a0e14; color: #c8d0d8; }

    /* CONTAINER - 600px */
    .block-container {
        padding-top: 0.3rem; padding-bottom: 0.3rem;
        padding-left: 0.6rem; padding-right: 0.6rem;
        max-width: 580px;
        font-family: 'Inter', sans-serif;
    }

    /* HIDE UI */
    section[data-testid="stSidebar"] { display: none; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ---- TOP BAR ---- */
    .top-bar {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.35rem 0.5rem; background: #0f1923;
        border-bottom: 1px solid #1c2a3a; border-radius: 0;
    }
    .top-title { font-size: 0.72rem; font-weight: 700; color: #4fc3f7; letter-spacing: 2px; font-family: 'JetBrains Mono', monospace; }
    .top-status { font-size: 0.58rem; color: #546e7a; font-family: 'JetBrains Mono', monospace; }

    /* ---- SCORE GAUGE AREA ---- */
    .score-area {
        display: flex; align-items: center; justify-content: center;
        padding: 0.4rem 0; margin: 0.1rem 0;
        background: linear-gradient(180deg, #0d1520 0%, #0a0e14 100%);
        border-bottom: 1px solid #1c2a3a;
    }
    .score-big { font-size: 3.2rem; font-weight: 900; line-height: 1; font-family: 'JetBrains Mono', monospace; letter-spacing: -1px; }
    .score-label { font-size: 0.7rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-top: 0.15rem; }
    .score-sublabel { font-size: 0.55rem; color: #546e7a; margin-top: 0.05rem; }

    /* ---- METRIC STRIP ---- */
    .metric-strip {
        display: flex; justify-content: space-around; align-items: stretch;
        padding: 0.25rem 0; background: #0f1923;
        border-bottom: 1px solid #1c2a3a;
    }
    .metric-item { text-align: center; flex: 1; border-right: 1px solid #1c2a3a; padding: 0.15rem 0; }
    .metric-item:last-child { border-right: none; }
    .metric-val { font-size: 0.95rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; line-height: 1.1; }
    .metric-lbl { font-size: 0.5rem; color: #546e7a; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 0.05rem; }

    /* ---- SIGNAL BANNER ---- */
    .signal-banner {
        text-align: center; padding: 0.3rem; margin: 0.15rem 0;
        border-radius: 4px; font-weight: 700;
    }
    .signal-type { font-size: 0.85rem; font-weight: 800; letter-spacing: 1px; }
    .signal-action { font-size: 0.58rem; color: #b0bec5; margin-top: 0.05rem; }

    /* ---- DIVERGENCE ALERT ---- */
    .divergence-alert {
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.25rem 0.5rem; border-radius: 3px; margin: 0.1rem 0;
        border-left: 3px solid; font-size: 0.65rem;
    }
    .div-label { font-weight: 700; font-size: 0.7rem; }
    .div-desc { font-size: 0.55rem; color: #90a4ae; }

    /* ---- SECTION HEADER ---- */
    .section-header {
        font-size: 0.6rem; font-weight: 700; color: #546e7a;
        padding: 0.25rem 0.3rem 0.1rem; letter-spacing: 1.5px;
        text-transform: uppercase; border-bottom: 1px solid #1c2a3a;
        margin-top: 0.15rem;
        font-family: 'JetBrains Mono', monospace;
    }

    /* ---- CATEGORY BAR ---- */
    .cat-row {
        display: flex; align-items: center; padding: 0.2rem 0.3rem;
        border-bottom: 1px solid #111a24; font-size: 0.65rem;
    }
    .cat-icon { font-size: 0.55rem; font-weight: 700; min-width: 28px; color: #546e7a; font-family: 'JetBrains Mono', monospace; }
    .cat-name { flex: 1; color: #90a4ae; font-size: 0.65rem; }
    .cat-score { font-weight: 800; font-family: 'JetBrains Mono', monospace; min-width: 40px; text-align: right; font-size: 0.72rem; }
    .cat-bar-container { width: 120px; height: 4px; background: #1c2a3a; border-radius: 2px; margin: 0 0.4rem; }
    .cat-bar-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }

    /* ---- ASSET TABLE ---- */
    .asset-table { width: 100%; border-collapse: collapse; font-size: 0.62rem; }
    .asset-table th {
        text-align: left; padding: 0.15rem 0.3rem; color: #37474f;
        font-size: 0.5rem; text-transform: uppercase; letter-spacing: 0.5px;
        border-bottom: 1px solid #1c2a3a; font-family: 'JetBrains Mono', monospace;
    }
    .asset-table td {
        padding: 0.15rem 0.3rem; border-bottom: 1px solid #0f1923;
        font-family: 'JetBrains Mono', monospace;
    }
    .asset-table tr:hover { background-color: #111a24; }
    .positive { color: #00E676; }
    .negative { color: #FF1744; }
    .neutral { color: #78909C; }
    .src-badge { font-size: 0.5rem; padding: 0 3px; border-radius: 2px; font-weight: 600; }
    .src-mt5 { background: #1b5e2033; color: #4CAF50; }
    .src-yf { background: #0d47a133; color: #42A5F5; }

    /* ---- STAT CARDS (analysis) ---- */
    .stat-card { text-align: center; padding: 0.2rem; background: #0f1923; border-radius: 4px; border: 1px solid #1c2a3a; }
    .stat-value { font-size: 1.1rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; line-height: 1.2; }
    .stat-label { font-size: 0.5rem; color: #546e7a; text-transform: uppercase; letter-spacing: 0.5px; }

    /* ---- SUGGESTION ---- */
    .suggestion-item { padding: 0.15rem 0.3rem; border-bottom: 1px solid #0f1923; display: flex; gap: 0.4rem; }

    /* ---- DIVIDER ---- */
    .thin-divider { border-top: 1px solid #1c2a3a; margin: 0.15rem 0; }

    /* ---- CONTROLS BAR ---- */
    .controls-bar {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.2rem 0.3rem; background: #0f1923;
        border-top: 1px solid #1c2a3a; margin-top: 0.1rem;
    }
    .ctrl-info { font-size: 0.55rem; color: #37474f; font-family: 'JetBrains Mono', monospace; }

    /* ---- TABS ---- */
    .stTabs [data-baseweb="tab-list"] { gap: 0; background: #0f1923; border-bottom: 1px solid #1c2a3a; }
    .stTabs [data-baseweb="tab"] { height: 2rem; font-size: 0.7rem; font-weight: 700; letter-spacing: 1px; color: #546e7a; padding: 0 1rem; }
    .stTabs [aria-selected="true"] { color: #4fc3f7 !important; border-bottom: 2px solid #4fc3f7 !important; background: #0d1520; }
    .stTabs [data-baseweb="tab-panel"] { padding: 0; }

    /* ---- BUTTONS ---- */
    .stButton>button {
        background: #1c2a3a; color: #90a4ae; border: 1px solid #263849;
        font-size: 0.65rem; font-weight: 600; border-radius: 3px;
        padding: 0.2rem 0.6rem; font-family: 'Inter', sans-serif;
        transition: all 0.15s;
    }
    .stButton>button:hover { background: #263849; color: #c8d0d8; border-color: #4fc3f7; }

    /* ---- SELECTBOX ---- */
    .stSelectbox div[data-baseweb="select"] {
        background: #1c2a3a; border: 1px solid #263849; border-radius: 3px;
        min-height: 1.6rem; font-size: 0.65rem;
    }
    .stSelectbox label { font-size: 0.55rem; color: #546e7a; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# INICIALIZACAO
# ============================================================
def init_session_state():
    if "data_manager" not in st.session_state:
        dm = DataManager(mt5_config=MT5_CONFIG, dual_source=DUAL_SOURCE_ASSETS, yf_only=YF_SYMBOLS)
        st.session_state.data_manager = dm
        st.session_state.scorer = MacroScorer(MACRO_WEIGHTS, SIGNAL_CONFIG)
        st.session_state.delta_analyzer = DeltaAnalyzer(SIGNAL_CONFIG)
        st.session_state.divergence_detector = DivergenceDetector(DIVERGENCE_CONFIG)
        st.session_state.macro_logger = MacroLogger(LOG_CONFIG)
        st.session_state.score_history = []
        st.session_state.last_data = {}
        st.session_state.mt5_status = None
        st.session_state.refresh_count = 0
        st.session_state.interval = 30
        st.session_state.win_price = None
        st.session_state.win_change = None

init_session_state()


def refresh_data():
    dm = st.session_state.data_manager
    all_data = dm.get_all_data()
    st.session_state.last_data = all_data

    scorer = st.session_state.scorer
    score_result = scorer.calculate_score(all_data)
    st.session_state.score_result = score_result

    delta_analyzer = st.session_state.delta_analyzer
    delta_analyzer.update(score_result["score"])
    delta_result = delta_analyzer.get_entry_signal(score_result)
    st.session_state.delta_result = delta_result

    # Divergence
    div_detector = st.session_state.divergence_detector
    div_detector.update_score(score_result["score"])

    # Track WIN price for divergence
    win_data = all_data.get("WIN") or all_data.get("EWZ")
    if win_data:
        win_price = win_data.get("current_price")
        if win_price:
            st.session_state.win_price = win_price
            st.session_state.win_change = win_data.get("change_pct")
            div_detector.update_win_price(win_price)

    divergence_result = div_detector.check_divergence()
    st.session_state.divergence_result = divergence_result

    st.session_state.score_history.append({
        "timestamp": datetime.now(),
        "score": score_result["score"],
        "signal_type": score_result["signal"]["type"],
    })
    if len(st.session_state.score_history) > 500:
        st.session_state.score_history = st.session_state.score_history[-500:]

    st.session_state.refresh_count += 1
    st.session_state.last_refresh = datetime.now()

    # LOGS
    mlog = st.session_state.macro_logger
    mlog.log_full_cycle(score_result, delta_result, all_data)
    if divergence_result and divergence_result.get("type") not in ("INDEFINIDO", "NEUTRO"):
        mlog._log_session_event("DIVERGENCE", {
            "type": divergence_result["type"],
            "label": divergence_result["label"],
            "severity": divergence_result["severity"],
        })

    return score_result


def get_entry_badge(entry: dict) -> str:
    """Retorna HTML do badge de entrada profissional."""
    etype = entry.get("type", "NEUTRO")
    label = entry.get("label", "SEM SINAL")
    confidence = entry.get("confidence", "")
    action = entry.get("action", "")

    if "COMPRA_FORTE" in etype:
        bg, border, color = "#0a2e0a", "#00E676", "#00E676"
    elif "COMPRA" in etype:
        bg, border, color = "#0a1f0a", "#66BB6A", "#66BB6A"
    elif "VENDA_FORTE" in etype:
        bg, border, color = "#2e0a0a", "#FF1744", "#FF1744"
    elif "VENDA" in etype:
        bg, border, color = "#1f0a0a", "#EF5350", "#EF5350"
    elif "REVERSAO" in etype:
        bg, border, color = "#2e2a0a", "#FFD600", "#FFD600"
    else:
        bg, border, color = "#0f1923", "#37474f", "#78909C"

    return f"""
    <div class="signal-banner" style="background:{bg}; border:1px solid {border}40;">
        <div class="signal-type" style="color:{color};">{label} <span style="font-size:0.55rem;color:{border}88;">{confidence}</span></div>
        <div class="signal-action">{action}</div>
    </div>
    """


# ============================================================
# LAYOUT PRINCIPAL
# ============================================================
tab_mesa, tab_analysis = st.tabs(["MESA", "ANALISE"])

# ============================================================
# TAB: MESA DE TRADING
# ============================================================
with tab_mesa:

    # Busca dados iniciais
    if not st.session_state.get("score_result"):
        with st.spinner("Conectando..."):
            refresh_data()

    score_result = st.session_state.get("score_result", {})
    if not score_result:
        st.error("Sem dados. Verifique conexao.")
        st.stop()

    score = score_result.get("score", 0)
    signal = score_result.get("signal", {})
    score_color = get_score_color(score)
    delta_result = st.session_state.get("delta_result", {})
    delta_val = delta_result.get("delta", 0)
    momentum_val = delta_result.get("momentum", 0)
    entry = delta_result.get("entry_signal", {})
    confluence = delta_result.get("confluence", {})
    divergence = st.session_state.get("divergence_result", {})

    # ---- TOP BAR ----
    avail = score_result.get("assets_available", 0)
    total = score_result.get("assets_total", 0)
    last_r = st.session_state.get("last_refresh", datetime.now())
    mt5_on = st.session_state.get("mt5_status", {}).get("success", False) if st.session_state.get("mt5_status") else False
    src_txt = "MT5" if mt5_on else "YF"
    src_color = "#4CAF50" if mt5_on else "#42A5F5"

    st.markdown(f"""
    <div class="top-bar">
        <span class="top-title">MACRO SCORING WIN</span>
        <span class="top-status">
            <span style="color:{src_color};">{src_txt}</span>
            {avail}/{total}
            <span style="color:#37474f;">|</span>
            {last_r.strftime("%H:%M:%S")}
            <span style="color:#37474f;">|</span>
            #{st.session_state.refresh_count}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ---- SCORE PRINCIPAL ----
    # Gauge com Plotly
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain=dict(x=[0, 1], y=[0, 1]),
        number=dict(font=dict(size=52, color=score_color, family="JetBrains Mono"), suffix=""),
        gauge=dict(
            axis=dict(range=[-100, 100], tickwidth=0, tickcolor="#0a0e14",
                      tickfont=dict(size=0), ticklen=0),
            bar=dict(color=score_color, thickness=0.15),
            bgcolor="#0a0e14",
            borderwidth=0,
            steps=[
                dict(range=[-100, -60], color="#FF174418"),
                dict(range=[-60, -30], color="#FF572218"),
                dict(range=[-30, 30], color="#FFD60010"),
                dict(range=[30, 60], color="#66BB6A18"),
                dict(range=[60, 100], color="#00E67618"),
            ],
            threshold=dict(line=dict(color="#ffffff30", width=1), thickness=0.6, value=0),
        ),
    ))
    fig_gauge.update_layout(
        height=120, margin=dict(l=15, r=15, t=0, b=0),
        paper_bgcolor="#0a0e14", font=dict(color="#c8d0d8"),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    # Signal label under gauge
    st.markdown(f"""
    <div style="text-align:center; margin-top:-0.5rem; margin-bottom:0.1rem;">
        <span style="color:{score_color}; font-size:0.75rem; font-weight:800; letter-spacing:2px; font-family:'JetBrains Mono',monospace;">
            {signal.get('label', 'N/A')}
        </span>
        <span style="color:#546e7a; font-size:0.55rem; margin-left:0.3rem;">
            {signal.get('confidence', '')}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ---- METRIC STRIP ----
    delta_color = "#00E676" if delta_val > 0 else "#FF1744" if delta_val < 0 else "#78909C"
    mom_color = "#00E676" if momentum_val > 0 else "#FF1744" if momentum_val < 0 else "#78909C"
    win_ch = st.session_state.get("win_change")
    win_str = f"{win_ch:+.2f}%" if win_ch is not None else "N/A"
    win_color = "#00E676" if (win_ch or 0) > 0 else "#FF1744" if (win_ch or 0) < 0 else "#78909C"

    conf_icon = ""
    if confluence.get("score_delta_aligned"):
        conf_icon = '<span style="color:#00E676;">CONFLUI</span>'
    elif confluence.get("reversal_detected"):
        conf_icon = '<span style="color:#FFD600;">REVERT</span>'
    else:
        conf_icon = '<span style="color:#37474f;">---</span>'

    st.markdown(f"""
    <div class="metric-strip">
        <div class="metric-item">
            <div class="metric-val" style="color:{delta_color};">{delta_val:+.1f}</div>
            <div class="metric-lbl">Delta</div>
        </div>
        <div class="metric-item">
            <div class="metric-val" style="color:{mom_color};">{momentum_val:+.1f}</div>
            <div class="metric-lbl">Momentum</div>
        </div>
        <div class="metric-item">
            <div class="metric-val" style="color:{win_color};">{win_str}</div>
            <div class="metric-lbl">WIN/Proxy</div>
        </div>
        <div class="metric-item">
            <div class="metric-val" style="font-size:0.7rem;">{conf_icon}</div>
            <div class="metric-lbl">Confluencia</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- SIGNAL BANNER ----
    st.markdown(get_entry_badge(entry), unsafe_allow_html=True)

    # ---- DIVERGENCE ALERT ----
    if divergence and divergence.get("type") not in ("INDEFINIDO",):
        div_type = divergence.get("type", "NEUTRO")
        div_label = divergence.get("label", "")
        div_color = divergence.get("color", "#78909C")
        div_desc = divergence.get("description", "")
        div_severity = divergence.get("severity", "none")
        bg = "#FFD60008" if "DIVERGENCIA" in div_type else "#00E67608"
        st.markdown(f"""
        <div class="divergence-alert" style="background:{bg}; border-left-color:{div_color};">
            <div>
                <div class="div-label" style="color:{div_color};">{divergence.get('icon', '')} {div_label}</div>
                <div class="div-desc">{div_desc[:80]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ---- CATEGORIAS ----
    category_scores = score_result.get("category_scores", {})
    st.markdown('<div class="section-header">CATEGORIAS</div>', unsafe_allow_html=True)

    for cat_name, cat_data in category_scores.items():
        cat_score = cat_data.get("normalized", 0)
        cat_color = get_score_color(cat_score)

        # Icon
        cat_icon = ""
        for cname, cinfo in CATEGORIES.items():
            if cname == cat_name:
                cat_icon = cinfo.get("icon", "")
                break

        # Bar fill percentage (score -100 to 100 mapped to 0-100%)
        bar_pct = max(0, min(100, (cat_score + 100) / 200 * 100))

        st.markdown(f"""
        <div class="cat-row">
            <span class="cat-icon">{cat_icon}</span>
            <span class="cat-name">{cat_name}</span>
            <div class="cat-bar-container">
                <div class="cat-bar-fill" style="width:{bar_pct}%;background:{cat_color};"></div>
            </div>
            <span class="cat-score" style="color:{cat_color};">{cat_score:+.0f}</span>
        </div>
        """, unsafe_allow_html=True)

    # ---- ATIVOS ----
    asset_signals = score_result.get("asset_signals", {})
    st.markdown('<div class="section-header">ATIVOS</div>', unsafe_allow_html=True)

    # Build asset table HTML
    asset_rows = []
    sorted_assets = sorted(
        asset_signals.items(),
        key=lambda x: abs(x[1].get("contribution", 0)),
        reverse=True
    )

    for asset_name, data in sorted_assets:
        change = data.get("change_pct")
        contribution = data.get("contribution", 0)
        direction = data.get("direction", 1)
        source = data.get("source", "")
        price = data.get("current_price")

        change_str = format_change(change) if change is not None else "N/A"
        change_cls = "positive" if (change or 0) > 0 else "negative" if (change or 0) < 0 else "neutral"
        contrib_cls = "positive" if contribution > 0.001 else "negative" if contribution < -0.001 else "neutral"
        dir_icon = "&#9650;" if direction > 0 else "&#9660;"
        dir_cls = "positive" if direction > 0 else "negative"

        src_cls = "src-mt5" if "mt5" in source else "src-yf"
        src_txt = "M" if "mt5" in source else "Y"

        price_str = format_price(price) if price else "---"

        asset_rows.append(f"""
        <tr>
            <td><span class="src-badge {src_cls}">{src_txt}</span> {asset_name}</td>
            <td style="text-align:right;color:#78909C;">{price_str}</td>
            <td class="{change_cls}" style="text-align:right;font-weight:600;">{change_str}</td>
            <td class="{dir_cls}" style="text-align:center;font-size:0.55rem;">{dir_icon}</td>
            <td class="{contrib_cls}" style="text-align:right;">{contribution:+.3f}</td>
        </tr>
        """)

    st.markdown(f"""
    <table class="asset-table">
        <thead>
            <tr>
                <th>Ativo</th>
                <th style="text-align:right;">Preco</th>
                <th style="text-align:right;">Var</th>
                <th style="text-align:center;">Dir</th>
                <th style="text-align:right;">Contrib</th>
            </tr>
        </thead>
        <tbody>
            {"".join(asset_rows)}
        </tbody>
    </table>
    """, unsafe_allow_html=True)

    # ---- SCORE HISTORY CHART ----
    history = st.session_state.score_history
    if len(history) >= 2:
        st.markdown('<div class="section-header">HISTORICO</div>', unsafe_allow_html=True)
        timestamps = [h["timestamp"] for h in history]
        scores = [h["score"] for h in history]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps, y=scores, mode='lines',
            line=dict(color='#4fc3f7', width=1.5, shape='spline'),
            fill='tozeroy', fillcolor='rgba(79, 195, 247, 0.06)',
        ))
        fig.add_hline(y=60, line_dash="dash", line_color="#00E67630", line_width=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#66BB6A20", line_width=1)
        fig.add_hline(y=0, line_dash="solid", line_color="#ffffff10", line_width=0.5)
        fig.add_hline(y=-30, line_dash="dot", line_color="#EF535020", line_width=1)
        fig.add_hline(y=-60, line_dash="dash", line_color="#FF174430", line_width=1)

        fig.update_layout(
            height=120, margin=dict(l=25, r=10, t=5, b=15),
            yaxis=dict(range=[-100, 100], title="", tickfont=dict(size=8, color='#37474f'), gridcolor='#111a24', zeroline=False),
            xaxis=dict(title="", tickfont=dict(size=7, color='#263849'), gridcolor='#0f1923'),
            template="plotly_dark", paper_bgcolor='#0a0e14', plot_bgcolor='#0a0e14',
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---- CONTROLS ----
    st.markdown('<div class="thin-divider"></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Atualizar", use_container_width=True):
            with st.spinner("..."):
                refresh_data()
    with col2:
        if st.button("MT5", use_container_width=True):
            dm = st.session_state.data_manager
            success, msg = dm.connect_mt5()
            st.session_state.mt5_status = {"success": success, "message": msg}
            st.session_state.macro_logger.log_mt5_event(success, msg)
    with col3:
        interval = st.selectbox("Sec", [15, 30, 60], index=1, label_visibility="collapsed")
        st.session_state.interval = interval

    # Missing assets
    missing = score_result.get("missing_assets", [])
    if missing:
        st.markdown(f'<div style="color:#FF1744;font-size:0.55rem;text-align:center;padding:0.1rem;">Sem dados: {", ".join(missing[:6])}{"..." if len(missing) > 6 else ""}</div>', unsafe_allow_html=True)

    # Auto refresh
    refresh_seconds = st.session_state.interval
    st.markdown(f"""
    <div class="controls-bar">
        <span class="ctrl-info">Auto-refresh {refresh_seconds}s</span>
        <span class="ctrl-info">v2.0</span>
    </div>
    <script>
        setTimeout(function() {{ window.location.reload(); }}, {refresh_seconds * 1000});
    </script>
    """, unsafe_allow_html=True)


# ============================================================
# TAB: ANALISE DE LOGS
# ============================================================
with tab_analysis:
    render_analysis_tab()
