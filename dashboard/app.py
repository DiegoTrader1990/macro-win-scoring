"""
Dashboard Streamlit COMPACTO - 600x1000px
==========================================
Painel lateral para acompanhar ao lado da plataforma de operacao.
Tema escuro, layout vertical, info densa.

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
    SIGNAL_CONFIG, CATEGORIES, DASHBOARD_CONFIG, LOG_CONFIG
)
from data_sources.data_manager import DataManager
from scoring.macro_score import MacroScorer
from scoring.delta import DeltaAnalyzer
from utils.helpers import format_change, format_price, get_change_color, get_score_color
from utils.macro_logger import MacroLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACAO DA PAGINA - COMPACTA 600px
# ============================================================
st.set_page_config(
    page_title="Macro WIN",
    page_icon="W",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# CSS COMPACTO - TEMA ESCURO
st.markdown("""
<style>
    /* Fundo escuro */
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    
    /* Remove padding extra */
    .block-container { padding-top: 0.5rem; padding-bottom: 0.5rem; padding-left: 0.8rem; padding-right: 0.8rem; max-width: 580px; }
    
    /* Sidebar escondida */
    section[data-testid="stSidebar"] { display: none; }
    
    /* Header minimal */
    .main-title { font-size: 0.95rem; font-weight: 700; color: #90caf9; text-align: center; padding: 0.2rem 0; letter-spacing: 1px; }
    
    /* Score grande compacto */
    .score-box {
        text-align: center; padding: 0.4rem 0; border-radius: 8px; margin: 0.2rem 0;
    }
    .score-value { font-size: 2.8rem; font-weight: 900; line-height: 1; }
    .score-label { font-size: 0.75rem; font-weight: 600; }
    
    /* Metricas compactas */
    .metric-row { display: flex; justify-content: space-between; padding: 0.15rem 0; }
    .metric-label { font-size: 0.7rem; color: #888; }
    .metric-value { font-size: 0.85rem; font-weight: 700; }
    
    /* Asset row */
    .asset-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.15rem 0.4rem; border-radius: 4px; margin: 1px 0;
        border-left: 3px solid; font-size: 0.72rem;
    }
    .asset-name { font-weight: 700; min-width: 60px; }
    .asset-change { font-weight: 600; min-width: 55px; text-align: right; }
    .asset-contrib { font-size: 0.65rem; color: #888; min-width: 45px; text-align: right; }
    
    /* Category header */
    .cat-header { font-size: 0.7rem; font-weight: 700; color: #666; padding: 0.3rem 0 0.1rem; border-bottom: 1px solid #333; margin-top: 0.4rem; letter-spacing: 0.5px; }
    
    /* Signal box */
    .signal-box { text-align: center; padding: 0.3rem; border-radius: 6px; margin: 0.2rem 0; }
    
    /* Divider fino */
    .thin-divider { border-top: 1px solid #222; margin: 0.3rem 0; }
    
    /* Refresh info */
    .refresh-info { text-align: center; color: #555; font-size: 0.6rem; }
    
    /* Hide streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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
        st.session_state.macro_logger = MacroLogger(LOG_CONFIG)
        st.session_state.score_history = []
        st.session_state.last_data = {}
        st.session_state.mt5_status = None
        st.session_state.refresh_count = 0
        st.session_state.interval = 30

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

    st.session_state.score_history.append({
        "timestamp": datetime.now(),
        "score": score_result["score"],
        "signal_type": score_result["signal"]["type"],
    })
    if len(st.session_state.score_history) > 500:
        st.session_state.score_history = st.session_state.score_history[-500:]

    st.session_state.refresh_count += 1
    st.session_state.last_refresh = datetime.now()

    # GRAVA LOGS
    mlog = st.session_state.macro_logger
    mlog.log_full_cycle(score_result, delta_result, all_data)

    return score_result


# ============================================================
# CONTEUDO PRINCIPAL
# ============================================================

# Header minimal
st.markdown('<div class="main-title">MACRO SCORING - MINI INDICE (WIN)</div>', unsafe_allow_html=True)

# Busca dados iniciais
if not st.session_state.get("score_result"):
    with st.spinner("Carregando..."):
        refresh_data()

score_result = st.session_state.get("score_result", {})
if not score_result:
    st.error("Sem dados. Verifique conexao.")
    st.stop()

score = score_result.get("score", 0)
signal = score_result.get("signal", {})
score_color = get_score_color(score)

# ---- SCORE PRINCIPAL ----
delta_result = st.session_state.get("delta_result", {})
delta_val = delta_result.get("delta", 0)
momentum_val = delta_result.get("momentum", 0)
entry = delta_result.get("entry_signal", {})
confluence = delta_result.get("confluence", {})

st.markdown(f"""
<div class="score-box" style="background-color: {score_color}15; border: 2px solid {score_color}55;">
    <div class="score-value" style="color: {score_color};">{score:+.1f}</div>
    <div class="score-label" style="color: {score_color};">{signal.get('label', 'N/A')} {signal.get('confidence', '')}</div>
</div>
""", unsafe_allow_html=True)

# ---- METRICAS EM LINHA ----
delta_color = "#00C853" if delta_val > 0 else "#D50000" if delta_val < 0 else "#FFC107"
mom_color = "#00C853" if momentum_val > 0 else "#D50000" if momentum_val < 0 else "#FFC107"

entry_color = "#666"
if "COMPRA" in entry.get("type", ""):
    entry_color = "#00C853"
elif "VENDA" in entry.get("type", ""):
    entry_color = "#D50000"
elif "REVERSAO" in entry.get("type", ""):
    entry_color = "#FF9800"

st.markdown(f"""
<div class="metric-row">
    <span class="metric-label">DELTA</span>
    <span class="metric-value" style="color:{delta_color}">{delta_val:+.1f}</span>
    <span class="metric-label">MOM</span>
    <span class="metric-value" style="color:{mom_color}">{momentum_val:+.1f}</span>
    <span class="metric-label">ENTRADA</span>
    <span class="metric-value" style="color:{entry_color}">{entry.get('label', 'N/A')}</span>
</div>
""", unsafe_allow_html=True)

# Confluence indicator
conf_text = ""
if confluence.get("score_delta_aligned"):
    conf_text = '<span style="color:#00C853;font-weight:700;">CONFLUENCIA</span>'
elif confluence.get("reversal_detected"):
    conf_text = '<span style="color:#FF9800;font-weight:700;">REVERSAO</span>'
else:
    conf_text = '<span style="color:#666;">Sem confluencia</span>'

avail = score_result.get("assets_available", 0)
total = score_result.get("assets_total", 0)
last_r = st.session_state.get("last_refresh", datetime.now())

st.markdown(f"""
<div class="metric-row">
    <span>{conf_text}</span>
    <span style="color:#555;font-size:0.65rem;">{avail}/{total} ativos | {last_r.strftime("%H:%M:%S")} | #{st.session_state.refresh_count}</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="thin-divider"></div>', unsafe_allow_html=True)

# ---- BREAKDOWN POR CATEGORIA (COMPACTO) ----
category_scores = score_result.get("category_scores", {})

for cat_name, cat_data in category_scores.items():
    cat_score = cat_data.get("normalized", 0)
    cat_color = get_score_color(cat_score)
    
    # Busca icone da categoria
    cat_icon = ""
    for cname, cinfo in CATEGORIES.items():
        if cname == cat_name:
            cat_icon = cinfo.get("icon", "")
            break
    
    bar_width = int((cat_score + 100) / 200 * 20)
    bar = "+" * max(bar_width, 0) + "-" * max(20 - bar_width, 0)
    
    st.markdown(f"""
    <div class="cat-header">{cat_icon} {cat_name} <span style="color:{cat_color};font-weight:800;">{cat_score:+.0f}</span></div>
    """, unsafe_allow_html=True)

st.markdown('<div class="thin-divider"></div>', unsafe_allow_html=True)

# ---- ATIVOS POR CATEGORIA (LISTA COMPACTA) ----
asset_signals = score_result.get("asset_signals", {})

for cat_name, cat_info in CATEGORIES.items():
    cat_assets = cat_info.get("assets", [])
    cat_icon = cat_info.get("icon", "")
    available = [a for a in cat_assets if a in asset_signals]
    if not available:
        continue

    st.markdown(f'<div class="cat-header">{cat_icon} {cat_name}</div>', unsafe_allow_html=True)
    
    for asset_name in available:
        data = asset_signals[asset_name]
        change = data.get("change_pct")
        contribution = data.get("contribution", 0)
        direction = data.get("direction", 1)
        source = data.get("source", "")

        if change is not None:
            change_str = format_change(change)
            change_color = get_change_color(change)
        else:
            change_str = "N/A"
            change_color = "#666"

        if contribution > 0.001:
            border_color = "#00C853"
        elif contribution < -0.001:
            border_color = "#D50000"
        else:
            border_color = "#444"

        src_icon = "M" if "mt5" in source else "Y"

        st.markdown(f"""
        <div class="asset-row" style="border-left-color:{border_color}; background-color:{border_color}08;">
            <span class="asset-name">{asset_name}<span style="color:#555;font-size:0.55rem;"> {src_icon}</span></span>
            <span class="asset-change" style="color:{change_color}">{change_str}</span>
            <span class="asset-contrib">C:{contribution:+.3f} {'↑' if direction > 0 else '↓'}</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="thin-divider"></div>', unsafe_allow_html=True)

# ---- GRAFICO HISTORICO COMPACTO ----
history = st.session_state.score_history
if len(history) >= 2:
    timestamps = [h["timestamp"] for h in history]
    scores = [h["score"] for h in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps, y=scores, mode='lines',
        line=dict(color='#2196F3', width=1.5),
        fill='tozeroy', fillcolor='rgba(33, 150, 243, 0.08)',
    ))
    fig.add_hline(y=60, line_dash="dash", line_color="#00C85340", line_width=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#4CAF5030", line_width=1)
    fig.add_hline(y=0, line_dash="solid", line_color="#ffffff15", line_width=0.5)
    fig.add_hline(y=-30, line_dash="dot", line_color="#FF572230", line_width=1)
    fig.add_hline(y=-60, line_dash="dash", line_color="#D5000040", line_width=1)

    fig.update_layout(
        height=150, margin=dict(l=25, r=10, t=10, b=20),
        yaxis=dict(range=[-100, 100], title="", tickfont=dict(size=9, color='#666'), gridcolor='#1a1a2e'),
        xaxis=dict(title="", tickfont=dict(size=8, color='#555'), gridcolor='#1a1a2e'),
        template="plotly_dark", paper_bgcolor='#0e1117', plot_bgcolor='#0e1117',
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

# ---- BOTOES COMPACTOS ----
col1, col2, col3 = st.columns(3)
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

# MT5 status
if st.session_state.mt5_status:
    status = st.session_state.mt5_status
    if status["success"]:
        st.markdown('<div style="text-align:center;color:#00C853;font-size:0.65rem;">MT5 Conectado</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:center;color:#FF9800;font-size:0.65rem;">MT5 Off - Usando YF</div>', unsafe_allow_html=True)

# Missing assets
missing = score_result.get("missing_assets", [])
if missing:
    st.markdown(f'<div style="color:#D50000;font-size:0.6rem;text-align:center;">Sem dados: {", ".join(missing)}</div>', unsafe_allow_html=True)

# ---- AUTO REFRESH ----
refresh_seconds = st.session_state.interval
st.markdown(f"""
<div class="refresh-info">Auto-refresh {refresh_seconds}s</div>
<script>
    setTimeout(function() {{ window.location.reload(); }}, {refresh_seconds * 1000});
</script>
""", unsafe_allow_html=True)
