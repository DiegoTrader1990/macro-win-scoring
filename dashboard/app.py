"""
Dashboard Profissional Avançado - Macro Scoring WIN v3.0
=========================================================
Mesa de trading completa com todas as informações para decisão rápida.
Inspirado em terminais Bloomberg/Refinitiv com melhorias significativas.

Seções:
1. BARRA DE STATUS - WIN, Dólar, Hora, Status conexão
2. SCORE GLOBAL - Score, direção, confiança, zone bar
3. INDICADORES POR GRUPO - Moedas/Juros, Exterior, ADRs, Setoriais
4. SINAL DE ENTRADA - Tipo, score, filtros, timing
5. FILTRO DE ENTRADA - Confluências, multi-TF, price action, cesta
6. DIVERGÊNCIA - Score vs WIN
7. NÍVEIS-CHAVE WIN - Suporte/Resistência
8. LOG DE SINAIS - Histórico recente
9. GRÁFICO HISTÓRICO - Score ao longo do tempo

Para rodar: streamlit run dashboard/app.py
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go

from config import (
    MT5_CONFIG, DUAL_SOURCE_ASSETS, YF_SYMBOLS, MACRO_WEIGHTS,
    SIGNAL_CONFIG, CATEGORIES, DASHBOARD_CONFIG, LOG_CONFIG,
    WIN_TRACKING, DIVERGENCE_CONFIG, UI_CONFIG
)
from data_sources.data_manager import DataManager
from scoring.macro_score import MacroScorer
from scoring.delta import DeltaAnalyzer
from scoring.divergence import DivergenceDetector
from utils.helpers import format_change, format_price, get_change_color, get_score_color
from utils.macro_logger import MacroLogger
from dashboard.analysis_tab import render_analysis_tab

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UI = UI_CONFIG

# ============================================================
# CONFIGURACAO DA PAGINA
# ============================================================
st.set_page_config(
    page_title="Macro WIN",
    page_icon="W",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(f"""
<style>
    .stApp {{ background-color: {UI['bg_primary']}; color: {UI['text_primary']}; }}
    .block-container {{
        padding-top: 0.15rem; padding-bottom: 0.15rem;
        padding-left: {UI['panel_padding']}px; padding-right: {UI['panel_padding']}px;
        max-width: {UI['panel_width']}px;
        font-family: {UI['font_family_ui']};
    }}
    section[data-testid="stSidebar"] {{ display: none; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* === STATUS BAR (topo) === */
    .status-bar {{
        display: flex; align-items: center; gap: 0;
        background: {UI['bg_secondary']}; border-bottom: 1px solid {UI['border_color']};
        font-family: {UI['font_family_data']}; font-size: 9px;
    }}
    .sb-cell {{
        padding: 0.2rem 0.4rem; border-right: 1px solid {UI['border_color']};
        display: flex; align-items: center; gap: 0.2rem; white-space: nowrap;
    }}
    .sb-cell:last-child {{ border-right: none; }}
    .sb-label {{ color: {UI['text_muted']}; font-size: 7px; text-transform: uppercase; }}
    .sb-value {{ font-weight: 700; font-size: 9px; }}

    /* === SCORE GLOBAL === */
    .score-global {{
        display: flex; align-items: center; gap: 0.4rem;
        padding: 0.3rem 0.4rem; background: {UI['bg_secondary']};
        border-bottom: 1px solid {UI['border_color']};
    }}
    .sg-direction {{
        font-size: 18px; font-weight: 900; font-family: {UI['font_family_data']};
        letter-spacing: 1px; min-width: 70px; text-align: center;
        padding: 0.2rem; border-radius: 3px;
    }}
    .sg-center {{ flex: 1; text-align: center; }}
    .sg-score-num {{
        font-size: 32px; font-weight: 900; font-family: {UI['font_family_data']};
        line-height: 1; letter-spacing: -1px;
    }}
    .sg-score-glow {{ text-shadow: 0 0 20px currentColor, 0 0 40px currentColor; }}
    .sg-trend {{ font-size: 8px; color: {UI['text_secondary']}; letter-spacing: 1px; margin-top: 0.1rem; }}
    .sg-right {{ text-align: right; min-width: 100px; }}
    .sg-conf {{ font-size: 8px; color: {UI['text_muted']}; }}
    .sg-raw {{ font-size: 7px; color: {UI['text_muted']}; }}

    /* Zone bar */
    .zone-bar {{
        width: 100%; height: 3px; margin-top: 0.15rem;
        background: linear-gradient(to right,
            {UI['negative']} 0%, {UI['negative']} 15%,
            #FF7043 20%, {UI['warning']} 35%, {UI['warning']} 65%,
            #66BB6A 80%, {UI['positive']} 85%, {UI['positive']} 100%);
        position: relative; border-radius: 1px;
    }}
    .zone-ind {{
        position: absolute; top: -4px; width: 3px; height: 11px;
        background: white; border-radius: 1px;
    }}

    /* === METRIC STRIP (delta/momentum/confluência) === */
    .m-strip {{
        display: flex; background: {UI['bg_secondary']};
        border-bottom: 1px solid {UI['border_color']};
    }}
    .m-cell {{
        flex: 1; text-align: center; padding: 0.15rem 0;
        border-right: 1px solid {UI['border_color']};
    }}
    .m-cell:last-child {{ border-right: none; }}
    .m-val {{ font-size: 12px; font-weight: 800; font-family: {UI['font_family_data']}; line-height: 1.1; }}
    .m-lbl {{ font-size: 6px; color: {UI['text_muted']}; text-transform: uppercase; letter-spacing: 0.5px; }}

    /* === SIGNAL BANNER === */
    .sig-banner {{
        text-align: center; padding: 0.2rem; margin: 0.1rem 0;
        border-radius: 3px; border: 1px solid;
    }}
    .sig-type {{ font-size: 12px; font-weight: 800; letter-spacing: 1px; font-family: {UI['font_family_data']}; }}
    .sig-action {{ font-size: 8px; color: {UI['text_secondary']}; }}

    /* === SECTION HEADER === */
    .sec-hdr {{
        font-size: 7px; font-weight: 700; color: {UI['text_muted']};
        padding: 0.15rem 0.3rem; letter-spacing: 2px; text-transform: uppercase;
        border-bottom: 1px solid {UI['border_color']}; margin-top: 0.1rem;
        font-family: {UI['font_family_data']};
        display: flex; justify-content: space-between; align-items: center;
    }}
    .sec-hdr-right {{ font-size: 7px; color: {UI['text_secondary']}; }}

    /* === GROUP ROW (Indicadores por Grupo) === */
    .grp-row {{
        display: flex; align-items: center; padding: 0.12rem 0.3rem;
        border-bottom: 1px solid {UI['bg_secondary']}; font-size: 9px;
    }}
    .grp-name {{ min-width: 80px; color: {UI['text_secondary']}; font-size: 9px; }}
    .grp-items {{ flex: 1; display: flex; gap: 0.3rem; flex-wrap: wrap; }}
    .grp-item {{
        font-size: 8px; font-family: {UI['font_family_data']};
        display: flex; align-items: center; gap: 0.15rem;
    }}
    .grp-arrow {{ font-size: 7px; }}
    .grp-score {{ font-weight: 800; font-family: {UI['font_family_data']}; min-width: 32px; text-align: right; font-size: 9px; }}

    /* === ASSET MINI TABLE === */
    .mini-tbl {{ width: 100%; border-collapse: collapse; }}
    .mini-tbl th {{
        text-align: left; padding: 0.08rem 0.25rem;
        color: {UI['text_muted']}; font-size: 7px; text-transform: uppercase;
        letter-spacing: 0.5px; border-bottom: 1px solid {UI['border_color']};
        font-family: {UI['font_family_data']};
    }}
    .mini-tbl td {{
        padding: 0.08rem 0.25rem; border-bottom: 1px solid {UI['bg_secondary']};
        font-family: {UI['font_family_data']}; font-size: 9px; height: 18px; line-height: 18px;
    }}
    .mini-tbl tr:hover {{ background-color: {UI['bg_tertiary']}; }}

    /* === FILTER ROW (Filtro de Entrada) === */
    .filter-row {{
        display: flex; align-items: center; gap: 0.3rem;
        padding: 0.08rem 0.3rem; font-size: 8px;
        border-bottom: 1px solid {UI['bg_secondary']};
    }}
    .filter-icon {{ font-size: 9px; min-width: 12px; text-align: center; }}
    .filter-text {{ color: {UI['text_secondary']}; }}
    .filter-value {{ font-weight: 700; font-family: {UI['font_family_data']}; }}

    /* === DIVERGENCE === */
    .div-row {{
        display: flex; align-items: center; gap: 0.3rem;
        padding: 0.12rem 0.3rem; border-left: 3px solid;
        font-size: 8px; background: {UI['bg_secondary']};
        margin: 0.05rem 0;
    }}
    .div-label {{ font-weight: 700; font-family: {UI['font_family_data']}; font-size: 9px; }}
    .div-desc {{ color: {UI['text_secondary']}; font-size: 7px; }}

    /* === LEVELS TABLE === */
    .lvl-tbl {{ width: 100%; border-collapse: collapse; }}
    .lvl-tbl td {{
        padding: 0.05rem 0.25rem; font-family: {UI['font_family_data']};
        font-size: 8px; height: 15px; line-height: 15px;
    }}
    .lvl-tbl tr:hover {{ background-color: {UI['bg_tertiary']}; }}

    /* === SIGNAL LOG === */
    .log-tbl {{ width: 100%; border-collapse: collapse; }}
    .log-tbl th {{
        text-align: left; padding: 0.06rem 0.2rem; color: {UI['text_muted']};
        font-size: 6px; text-transform: uppercase; letter-spacing: 0.5px;
        border-bottom: 1px solid {UI['border_color']};
        font-family: {UI['font_family_data']};
    }}
    .log-tbl td {{
        padding: 0.06rem 0.2rem; border-bottom: 1px solid {UI['bg_secondary']};
        font-family: {UI['font_family_data']}; font-size: 8px;
    }}

    .pos {{ color: {UI['positive']}; }}
    .neg {{ color: {UI['negative']}; }}
    .neu {{ color: {UI['neutral']}; }}
    .wrn {{ color: {UI['warning']}; }}
    .src-m {{ font-size: 6px; background: #1b5e2022; color: #4CAF50; padding: 0 2px; border-radius: 1px; }}
    .src-y {{ font-size: 6px; background: #0d47a122; color: #42A5F5; padding: 0 2px; border-radius: 1px; }}
    .divider {{ border-top: 1px solid {UI['border_color']}; margin: 0.05rem 0; }}

    /* Controls */
    .stButton>button {{
        background: {UI['bg_tertiary']}; color: {UI['text_secondary']};
        border: 1px solid {UI['border_light']}; font-size: 9px;
        font-weight: 600; border-radius: 2px; padding: 0.1rem 0.4rem;
        font-family: {UI['font_family_ui']};
    }}
    .stButton>button:hover {{
        background: {UI['border_light']}; color: {UI['text_primary']};
        border-color: {UI['accent']};
    }}
    .stSelectbox div[data-baseweb="select"] {{
        background: {UI['bg_tertiary']}; border: 1px solid {UI['border_light']};
        border-radius: 2px; min-height: 1.3rem; font-size: 9px;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0; background: {UI['bg_secondary']};
        border-bottom: 1px solid {UI['border_color']};
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 1.5rem; font-size: 8px; font-weight: 700;
        letter-spacing: 1px; color: {UI['text_muted']};
        padding: 0 0.6rem; font-family: {UI['font_family_data']};
    }}
    .stTabs [aria-selected="true"] {{
        color: {UI['accent']} !important;
        border-bottom: 2px solid {UI['accent']} !important;
        background: {UI['bg_primary']};
    }}
    .stTabs [data-baseweb="tab-panel"] {{ padding: 0; }}
</style>
""", unsafe_allow_html=True)


# ============================================================
# INICIALIZACAO
# ============================================================
def init_session_state():
    if "data_manager" not in st.session_state:
        dm = DataManager(
            mt5_config=MT5_CONFIG, dual_source=DUAL_SOURCE_ASSETS,
            yf_only=YF_SYMBOLS, win_tracking=WIN_TRACKING,
        )
        st.session_state.data_manager = dm
        st.session_state.scorer = MacroScorer(MACRO_WEIGHTS, SIGNAL_CONFIG)
        st.session_state.delta_analyzer = DeltaAnalyzer(SIGNAL_CONFIG)
        st.session_state.divergence_detector = DivergenceDetector(DIVERGENCE_CONFIG)
        st.session_state.macro_logger = MacroLogger(LOG_CONFIG)
        st.session_state.score_history = []
        st.session_state.signal_log = []
        st.session_state.last_data = {}
        st.session_state.mt5_status = None
        st.session_state.refresh_count = 0
        st.session_state.interval = 30
        st.session_state.win_price = None
        st.session_state.win_change = None
        st.session_state.win_prev_close = None

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
    win_data = all_data.get("WIN") or all_data.get("EWZ")
    if win_data and win_data.get("current_price"):
        st.session_state.win_price = win_data["current_price"]
        st.session_state.win_change = win_data.get("change_pct")
        st.session_state.win_prev_close = win_data.get("previous_close")
        div_detector.update_win_price(win_data["current_price"])
    divergence_result = div_detector.check_divergence()
    st.session_state.divergence_result = divergence_result

    now = datetime.now()
    st.session_state.score_history.append({
        "timestamp": now,
        "score": score_result["score"],
        "signal_type": score_result["signal"]["type"],
        "delta": delta_result.get("delta", 0),
        "momentum": delta_result.get("momentum", 0),
    })
    if len(st.session_state.score_history) > 500:
        st.session_state.score_history = st.session_state.score_history[-500:]

    # Signal log
    entry = delta_result.get("entry_signal", {})
    if entry.get("type", "NEUTRO") != "NEUTRO":
        st.session_state.signal_log.append({
            "time": now.strftime("%H:%M:%S"),
            "direction": entry.get("label", ""),
            "score": score_result["score"],
            "delta": delta_result.get("delta", 0),
            "win_pts": st.session_state.win_price or 0,
            "confidence": entry.get("confidence", ""),
        })
        if len(st.session_state.signal_log) > 50:
            st.session_state.signal_log = st.session_state.signal_log[-50:]

    st.session_state.refresh_count += 1
    st.session_state.last_refresh = now

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


def get_group_data(all_data, score_result):
    """Agrupa ativos por categoria com suas variações."""
    asset_signals = score_result.get("asset_signals", {})
    groups = {}
    for cat_name, cat_info in CATEGORIES.items():
        assets_in_cat = cat_info.get("assets", [])
        items = []
        for a in assets_in_cat:
            sig = asset_signals.get(a, {})
            raw = all_data.get(a, {})
            items.append({
                "name": a,
                "change": sig.get("change_pct"),
                "contribution": sig.get("contribution", 0),
                "direction": sig.get("direction", 1),
                "source": sig.get("source", ""),
                "price": raw.get("current_price"),
            })
        cat_score_data = score_result.get("category_scores", {}).get(cat_name, {})
        groups[cat_name] = {
            "icon": cat_info.get("icon", ""),
            "color": cat_info.get("color", "#888"),
            "score": cat_score_data.get("normalized", 0),
            "items": items,
        }
    return groups


# ============================================================
# LAYOUT
# ============================================================
tab_mesa, tab_analysis = st.tabs(["MESA", "ANALISE"])

with tab_mesa:

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
    all_data = st.session_state.get("last_data", {})
    groups = get_group_data(all_data, score_result)

    # ============================================================
    # 1. BARRA DE STATUS
    # ============================================================
    win_ch = st.session_state.get("win_change")
    win_pr = st.session_state.win_price
    win_str = f"{win_pr:,.0f}" if win_pr else "---"
    win_ch_str = f"{win_ch:+.2f}%" if win_ch is not None else "---"
    win_ch_cls = "pos" if (win_ch or 0) > 0 else "neg" if (win_ch or 0) < 0 else "neu"

    # DXY
    dxy_data = all_data.get("DXY", {})
    dxy_price = dxy_data.get("current_price")
    dxy_change = dxy_data.get("change_pct")
    dxy_str = f"{dxy_price:.3f}" if dxy_price else "---"
    dxy_cls = "pos" if (dxy_change or 0) > 0 else "neg" if (dxy_change or 0) < 0 else "neu"
    dxy_ch_str = f"{dxy_change:+.2f}%" if dxy_change is not None else "---"

    # VIX
    vix_data = all_data.get("VIX", {})
    vix_price = vix_data.get("current_price")
    vix_str = f"{vix_price:.1f}" if vix_price else "---"

    last_r = st.session_state.get("last_refresh", datetime.now())
    mt5_on = st.session_state.get("mt5_status", {}).get("success", False) if st.session_state.get("mt5_status") else False
    src_tag = '<span class="src-m">MT5</span>' if mt5_on else '<span class="src-y">YF</span>'
    avail = score_result.get("assets_available", 0)
    total = score_result.get("assets_total", 0)

    st.markdown(f"""
    <div class="status-bar">
        <div class="sb-cell" style="background:#1a2535;">
            <span class="sb-label">AO VIVO</span>
        </div>
        <div class="sb-cell">
            <span class="sb-value" style="color:{UI['warning']}">{last_r.strftime("%H:%M:%S")}</span>
        </div>
        <div class="sb-cell">
            <span class="sb-label">WIN</span>
            <span class="sb-value">{win_str}</span>
            <span class="sb-value {win_ch_cls}">{win_ch_str}</span>
        </div>
        <div class="sb-cell">
            <span class="sb-label">DXY</span>
            <span class="sb-value">{dxy_str}</span>
            <span class="sb-value {dxy_cls}">{dxy_ch_str}</span>
        </div>
        <div class="sb-cell">
            <span class="sb-label">VIX</span>
            <span class="sb-value" style="color:{UI['warning']}">{vix_str}</span>
        </div>
        <div class="sb-cell">
            {src_tag}
            <span class="sb-value" style="color:{UI['text_muted']}">{avail}/{total}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # 2. SCORE GLOBAL
    # ============================================================
    direction_text = "COMPRA" if score > 0 else "VENDA" if score < 0 else "NEUTRO"
    direction_bg = f"{UI['positive']}22" if score > 0 else f"{UI['negative']}22" if score < 0 else f"{UI['neutral']}22"
    direction_color = UI['positive'] if score > 0 else UI['negative'] if score < 0 else UI['neutral']

    # Trend text
    if delta_val > 5:
        trend_text = "MELHORANDO"
    elif delta_val < -5:
        trend_text = "PIORANDO"
    else:
        trend_text = "ESTAVEL"

    if confluence.get("score_delta_aligned"):
        trend_text += " | CONFLUENCIA CONFIRMADA"
    elif confluence.get("reversal_detected"):
        trend_text += " | REVERSAO DETECTADA"

    indicator_pct = max(0, min(100, (score + 100) / 200 * 100))
    glow = "sg-score-glow" if UI.get("score_glow", True) else ""

    st.markdown(f"""
    <div class="score-global">
        <div class="sg-direction" style="color:{direction_color}; background:{direction_bg};">
            {direction_text}
        </div>
        <div class="sg-center">
            <div class="sg-score-num {glow}" style="color:{score_color}">{score:+.1f}</div>
            <div class="sg-trend">{trend_text}</div>
            <div class="zone-bar"><div class="zone-ind" style="left:{indicator_pct}%"></div></div>
        </div>
        <div class="sg-right">
            <div class="sg-conf">conf: {signal.get('confidence', '---')}</div>
            <div class="sg-raw">raw: {score_result.get('raw_score', 0):.4f}</div>
            <div class="sg-raw">w: {score_result.get('total_weight_used', 0):.3f}</div>
            <div class="sg-raw">leituras: {st.session_state.refresh_count}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # 3. METRIC STRIP
    # ============================================================
    delta_cls = "pos" if delta_val > 0 else "neg" if delta_val < 0 else "neu"
    mom_cls = "pos" if momentum_val > 0 else "neg" if momentum_val < 0 else "neu"

    # Score acceleration
    score_history = st.session_state.score_history
    accel = 0
    if len(score_history) >= 3:
        d1 = score_history[-1]["score"] - score_history[-2]["score"]
        d2 = score_history[-2]["score"] - score_history[-3]["score"]
        accel = d1 - d2
    accel_cls = "pos" if accel > 2 else "neg" if accel < -2 else "neu"
    accel_label = "acelerando" if accel > 5 else "desacelerando" if accel < -5 else "estavel"

    # Score in zone
    zone_label = "FORTE" if abs(score) > 60 else "MODERADA" if abs(score) > 30 else "NEUTRA"

    st.markdown(f"""
    <div class="m-strip">
        <div class="m-cell">
            <div class="m-val {delta_cls}">{delta_val:+.1f}</div>
            <div class="m-lbl">Delta</div>
        </div>
        <div class="m-cell">
            <div class="m-val {mom_cls}">{momentum_val:+.1f}</div>
            <div class="m-lbl">Momentum</div>
        </div>
        <div class="m-cell">
            <div class="m-val {accel_cls}">{accel:+.1f}</div>
            <div class="m-lbl">{accel_label}</div>
        </div>
        <div class="m-cell">
            <div class="m-val" style="color:{score_color}">{zone_label}</div>
            <div class="m-lbl">Zona</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # 4. SINAL DE ENTRADA
    # ============================================================
    etype = entry.get("type", "NEUTRO")
    elabel = entry.get("label", "SEM SINAL")
    econf = entry.get("confidence", "")
    eaction = entry.get("action", "")

    if "COMPRA_FORTE" in etype:
        sbg, sb, sc = "#0a2e0a", UI['positive'], UI['positive']
    elif "COMPRA" in etype:
        sbg, sb, sc = "#0a1f0a", "#66BB6A", "#66BB6A"
    elif "VENDA_FORTE" in etype:
        sbg, sb, sc = "#2e0a0a", UI['negative'], UI['negative']
    elif "VENDA" in etype:
        sbg, sb, sc = "#1f0a0a", "#EF5350", "#EF5350"
    elif "REVERSAO" in etype:
        sbg, sb, sc = "#2e2a0a", UI['warning'], UI['warning']
    else:
        sbg, sb, sc = UI['bg_secondary'], UI['border_color'], UI['neutral']

    st.markdown(f"""
    <div class="sig-banner" style="background:{sbg}; border-color:{sb}30;">
        <div class="sig-type" style="color:{sc}">{elabel} <span style="font-size:7px;color:{sb}88">{econf}</span></div>
        <div class="sig-action">{eaction}</div>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # 5. INDICADORES POR GRUPO
    # ============================================================
    st.markdown('<div class="sec-hdr">INDICADORES POR GRUPO <span class="sec-hdr-right">variacao intraday</span></div>', unsafe_allow_html=True)

    for cat_name, cat_data in groups.items():
        cat_score = cat_data["score"]
        cat_color = get_score_color(cat_score)
        cat_icon = cat_data["icon"]
        items_html = ""

        for item in cat_data["items"]:
            ch = item["change"]
            ch_str = f"{ch:+.2f}%" if ch is not None else "---"
            ch_cls = "pos" if (ch or 0) > 0 else "neg" if (ch or 0) < 0 else "neu"
            arrow = "&#9650;" if (ch or 0) > 0 else "&#9660;" if (ch or 0) < 0 else "&#9644;"
            src_cls = "src-m" if "mt5" in item.get("source", "") else "src-y"
            items_html += f'<span class="grp-item"><span class="{src_cls}">{item["name"]}</span> <span class="{ch_cls} grp-arrow">{arrow}</span> <span class="{ch_cls}">{ch_str}</span></span>'

        st.markdown(f"""
        <div class="grp-row">
            <span class="grp-name" style="color:{cat_data['color']}">{cat_icon} {cat_name}</span>
            <span class="grp-items">{items_html}</span>
            <span class="grp-score" style="color:{cat_color}">{cat_score:+.0f}</span>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # 6. FILTRO DE ENTRADA (confluências e verificações)
    # ============================================================
    st.markdown('<div class="sec-hdr">FILTRO DE ENTRADA</div>', unsafe_allow_html=True)

    # Score na zona
    score_in_zone = abs(score) < 4
    zone_cls = "wrn" if score_in_zone else "pos"
    zone_icon = "&#9888;" if score_in_zone else "&#10003;"

    # Confirmado > 2 min
    confirm_text = "Sim"
    confirm_cls = "pos"
    confirm_icon = "&#10003;"
    if len(score_history) >= 4:
        recent_scores = [h["score"] for h in score_history[-4:]]
        same_dir = all(s > 0 for s in recent_scores) or all(s < 0 for s in recent_scores)
        if same_dir:
            confirm_text = f"Confirmado >2min"
            confirm_cls = "pos"
            confirm_icon = "&#10003;"
        else:
            confirm_text = "Instavel"
            confirm_cls = "wrn"
            confirm_icon = "&#9888;"

    # Aceleracao
    accel_text = "estavel"
    accel_cls = "neu"
    if accel > 5:
        accel_text = "acelerando alta"
        accel_cls = "pos"
    elif accel < -5:
        accel_text = "acelerando baixa"
        accel_cls = "neg"

    # Cesta: Dolar, VALE+PETR, DI
    usdbrl_data = all_data.get("DXY", {})
    usd_dir = "subindo" if (usdbrl_data.get("change_pct") or 0) > 0 else "caindo" if (usdbrl_data.get("change_pct") or 0) < 0 else "plano"
    usd_cls = "pos" if usd_dir == "subindo" and score < 0 else "neg" if usd_dir == "subindo" and score > 0 else "neu"

    vale_adr = all_data.get("VALE_ADR", {})
    petr_adr = all_data.get("PETR_ADR", {})
    vale_ch = vale_adr.get("change_pct") or 0
    petr_ch = petr_adr.get("change_pct") or 0
    cesta_br = "positivas" if (vale_ch + petr_ch) > 0.5 else "negativas" if (vale_ch + petr_ch) < -0.5 else "neutras"
    cesta_cls = "pos" if cesta_br == "positivas" else "neg" if cesta_br == "negativas" else "neu"

    # Divergencia status
    div_type = divergence.get("type", "INDEFINIDO") if divergence else "INDEFINIDO"
    div_ok = div_type not in ("DIVERGENCIA_ALTA", "DIVERGENCIA_BAIXA")
    div_text = "Sem conflito" if div_ok else "DIVERGENTE"
    div_cls = "pos" if div_ok else "wrn"

    filters = [
        (zone_icon, f"Score na zona (±4)", f"{score:+.1f}", zone_cls),
        (confirm_icon, f"Estabilidade", confirm_text, confirm_cls),
        ("&#9670;", f"Aceleracao", accel_text, accel_cls),
        ("&#9670;", f"Divergencia Score vs WIN", div_text, div_cls),
        ("$", f"Dolar {usd_dir}", f"{usdbrl_data.get('change_pct', 0):+.2f}%", usd_cls),
        ("&#9679;", f"VALE+PETR", cesta_br, cesta_cls),
    ]

    filters_html = ""
    for icon, text, value, cls in filters:
        filters_html += f"""
        <div class="filter-row">
            <span class="filter-icon {cls}">{icon}</span>
            <span class="filter-text">{text}</span>
            <span class="filter-value {cls}">{value}</span>
        </div>
        """

    st.markdown(filters_html, unsafe_allow_html=True)

    # Divergence alert box
    if divergence and div_type not in ("INDEFINIDO",):
        div_color = divergence.get("color", UI['neutral'])
        div_label = divergence.get("label", "")
        div_desc = divergence.get("description", "")
        div_bg = f"{UI['warning']}10" if "DIVERGENCIA" in div_type else f"{UI['positive']}10"

        st.markdown(f"""
        <div class="div-row" style="background:{div_bg}; border-left-color:{div_color};">
            <span class="div-label" style="color:{div_color}">{divergence.get('icon', '')} {div_label}</span>
            <span class="div-desc">{div_desc[:100]}</span>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # 7. ATIVOS DETALHADOS
    # ============================================================
    asset_signals = score_result.get("asset_signals", {})
    st.markdown('<div class="sec-hdr">ATIVOS <span class="sec-hdr-right">contribuicao ponderada</span></div>', unsafe_allow_html=True)

    sorted_assets = sorted(
        asset_signals.items(),
        key=lambda x: abs(x[1].get("contribution", 0)),
        reverse=True
    )

    asset_rows = ""
    for asset_name, data in sorted_assets:
        change = data.get("change_pct")
        contribution = data.get("contribution", 0)
        direction = data.get("direction", 1)
        source = data.get("source", "")
        price = data.get("current_price")
        corr = data.get("correlation", 0)
        weight = data.get("weight", 0)

        ch_str = format_change(change) if change is not None else "---"
        ch_cls = "pos" if (change or 0) > 0 else "neg" if (change or 0) < 0 else "neu"
        co_cls = "pos" if contribution > 0.001 else "neg" if contribution < -0.001 else "neu"
        dir_icon = "&#9650;" if direction > 0 else "&#9660;"
        dir_cls = "pos" if direction > 0 else "neg"
        src_cls = "src-m" if "mt5" in source else "src-y"
        src_txt = "M" if "mt5" in source else "Y"
        price_str = format_price(price) if price else "---"

        asset_rows += f"""
        <tr>
            <td><span class="{src_cls}">{src_txt}</span> {asset_name}</td>
            <td style="text-align:right;color:{UI['text_muted']}">{price_str}</td>
            <td style="text-align:right" class="{ch_cls}">{ch_str}</td>
            <td style="text-align:center" class="{dir_cls}">{dir_icon}</td>
            <td style="text-align:right;color:{UI['text_muted']}">{corr:+.2f}</td>
            <td style="text-align:right;color:{UI['text_muted']}">{weight:.0%}</td>
            <td style="text-align:right" class="{co_cls}">{contribution:+.3f}</td>
        </tr>"""

    st.markdown(f"""
    <table class="mini-tbl">
        <thead><tr>
            <th>Ativo</th><th style="text-align:right">Preco</th>
            <th style="text-align:right">Var</th><th style="text-align:center">Dir</th>
            <th style="text-align:right">Corr</th><th style="text-align:right">Peso</th>
            <th style="text-align:right">Contrib</th>
        </tr></thead>
        <tbody>{asset_rows}</tbody>
    </table>
    """, unsafe_allow_html=True)

    # ============================================================
    # 8. LOG DE SINAIS
    # ============================================================
    sig_log = st.session_state.signal_log
    st.markdown(f'<div class="sec-hdr">LOG DE SINAIS ({len(sig_log)})</div>', unsafe_allow_html=True)

    if sig_log:
        log_rows = ""
        for sl in sig_log[-8:][::-1]:
            dir_cls = "pos" if "COMPRA" in sl["direction"] else "neg" if "VENDA" in sl["direction"] else "wrn"
            log_rows += f"""
            <tr>
                <td>{sl['time']}</td>
                <td class="{dir_cls}">{sl['direction']}</td>
                <td>{sl['score']:+.1f}</td>
                <td>{sl['delta']:+.1f}</td>
                <td>{sl['confidence']}</td>
            </tr>"""

        st.markdown(f"""
        <table class="log-tbl">
            <thead><tr><th>Hora</th><th>Direcao</th><th>Score</th><th>Delta</th><th>Conf</th></tr></thead>
            <tbody>{log_rows}</tbody>
        </table>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="padding:0.2rem;color:{UI["text_muted"]};font-size:8px;text-align:center;">Nenhum sinal gerado nesta sessao</div>', unsafe_allow_html=True)

    # ============================================================
    # 9. GRAFICO HISTORICO
    # ============================================================
    if len(score_history) >= 2:
        st.markdown('<div class="sec-hdr">HISTORICO SCORE</div>', unsafe_allow_html=True)
        timestamps = [h["timestamp"] for h in score_history]
        scores = [h["score"] for h in score_history]
        deltas = [h.get("delta", 0) for h in score_history]

        fig = go.Figure()
        # Score line
        fig.add_trace(go.Scatter(
            x=timestamps, y=scores, mode='lines', name='Score',
            line=dict(color=UI['accent'], width=1.5, shape='spline'),
            fill='tozeroy', fillcolor=f"rgba(79, 195, 247, 0.05)",
        ))
        # Delta bars
        if any(d != 0 for d in deltas):
            delta_colors = [UI['positive'] if d >= 0 else UI['negative'] for d in deltas]
            fig.add_trace(go.Bar(
                x=timestamps, y=deltas, name='Delta',
                marker_color=delta_colors, marker_line_width=0,
                opacity=0.4, yaxis='y2',
            ))

        fig.add_hline(y=60, line_dash="dash", line_color=f"{UI['positive']}25", line_width=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#66BB6A15", line_width=1)
        fig.add_hline(y=0, line_dash="solid", line_color="#ffffff08", line_width=0.5)
        fig.add_hline(y=-30, line_dash="dot", line_color="#EF535015", line_width=1)
        fig.add_hline(y=-60, line_dash="dash", line_color=f"{UI['negative']}25", line_width=1)

        fig.update_layout(
            height=110, margin=dict(l=25, r=10, t=3, b=12),
            yaxis=dict(range=[-100, 100], title="",
                       tickfont=dict(size=6, color=UI['text_muted']),
                       gridcolor=UI['bg_tertiary'], zeroline=False),
            yaxis2=dict(range=[-30, 30], overlaying='y', side='right',
                        tickfont=dict(size=5, color=UI['text_muted']),
                        gridcolor=UI['bg_secondary'], showgrid=False),
            xaxis=dict(title="", tickfont=dict(size=5, color=UI['text_muted']),
                       gridcolor=UI['bg_secondary']),
            template="plotly_dark",
            paper_bgcolor=UI['bg_primary'],
            plot_bgcolor=UI['bg_primary'],
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ============================================================
    # CONTROLS
    # ============================================================
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
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

    missing = score_result.get("missing_assets", [])
    if missing:
        st.markdown(f'<div style="color:{UI["negative"]};font-size:7px;text-align:center;">Sem dados: {", ".join(missing[:5])}</div>', unsafe_allow_html=True)

    refresh_seconds = st.session_state.interval
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;padding:0.1rem 0.3rem;background:{UI['bg_secondary']};border-top:1px solid {UI['border_color']};">
        <span style="font-size:7px;color:{UI['text_muted']};font-family:{UI['font_family_data']};">auto-refresh {refresh_seconds}s | #{st.session_state.refresh_count}</span>
        <span style="font-size:7px;color:{UI['text_muted']};font-family:{UI['font_family_data']};">v3.0</span>
    </div>
    <script>
        setTimeout(function() {{ window.location.reload(); }}, {refresh_seconds * 1000});
    </script>
    """, unsafe_allow_html=True)


# ============================================================
# TAB: ANALISE
# ============================================================
with tab_analysis:
    render_analysis_tab()
