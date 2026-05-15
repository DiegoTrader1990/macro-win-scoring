"""
Dashboard Profissional - Macro Scoring WIN v2.1
=================================================
Mesa de trading 600x1000 para tomada de decisão rápida.
Design de terminal profissional com CSS puro (sem Plotly gauge).
Tudo configurável via UI_CONFIG no config.py.

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

# Unpack UI config for readability
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

# CSS PROFISSIONAL - COM VALORES DO UI_CONFIG
st.markdown(f"""
<style>
    /* === RESET === */
    .stApp {{ background-color: {UI['bg_primary']}; color: {UI['text_primary']}; }}
    .block-container {{
        padding-top: 0.2rem; padding-bottom: 0.2rem;
        padding-left: {UI['panel_padding']}px; padding-right: {UI['panel_padding']}px;
        max-width: {UI['panel_width']}px;
        font-family: {UI['font_family_ui']};
    }}
    section[data-testid="stSidebar"] {{ display: none; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* === TOP BAR === */
    .top-bar {{
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.3rem 0.5rem; background: {UI['bg_secondary']};
        border-bottom: 1px solid {UI['border_color']};
    }}
    .top-title {{
        font-size: {UI['header_title_size']}px; font-weight: 700;
        color: {UI['accent']}; letter-spacing: 2px;
        font-family: {UI['font_family_data']};
    }}
    .top-status {{
        font-size: {UI['header_status_size']}px; color: {UI['text_muted']};
        font-family: {UI['font_family_data']};
    }}

    /* === SCORE DISPLAY (CSS ONLY - NO PLOTLY GAUGE) === */
    .score-panel {{
        position: relative; text-align: center;
        padding: 0.5rem 0 0.3rem;
        background: linear-gradient(180deg, {UI['bg_secondary']} 0%, {UI['bg_primary']} 100%);
        border-bottom: 1px solid {UI['border_color']};
    }}
    .score-number {{
        font-size: {UI['score_font_size']}px; font-weight: 900;
        font-family: {UI['font_family_data']}; line-height: 1;
        letter-spacing: -1px;
    }}
    .score-glow {{
        text-shadow: 0 0 30px currentColor, 0 0 60px currentColor;
    }}
    .score-signal-label {{
        font-size: {UI['score_label_font_size']}px; font-weight: 700;
        letter-spacing: 1.5px; text-transform: uppercase;
        margin-top: 0.2rem; font-family: {UI['font_family_data']};
    }}
    .score-confidence {{
        font-size: 8px; color: {UI['text_muted']};
        letter-spacing: 1px; margin-top: 0.05rem;
    }}

    /* Score zone bar (CSS-based gauge) */
    .zone-bar {{
        width: 90%; height: 4px; margin: 0.4rem auto 0.1rem;
        border-radius: 2px; position: relative;
        background: linear-gradient(to right,
            {UI['negative']} 0%, {UI['negative']} 15%,
            #FF7043 20%, #FF7043 25%,
            {UI['warning']} 35%, {UI['warning']} 65%,
            #66BB6A 75%, #66BB6A 80%,
            {UI['positive']} 85%, {UI['positive']} 100%
        );
    }}
    .zone-indicator {{
        position: absolute; top: -5px; width: 3px; height: 14px;
        background: white; border-radius: 1px;
        transition: left 0.5s ease;
    }}

    /* === METRIC STRIP === */
    .metric-strip {{
        display: flex; justify-content: space-around; align-items: stretch;
        background: {UI['bg_secondary']};
        border-bottom: 1px solid {UI['border_color']};
    }}
    .metric-item {{
        text-align: center; flex: 1;
        border-right: 1px solid {UI['border_color']};
        padding: 0.2rem 0;
    }}
    .metric-item:last-child {{ border-right: none; }}
    .metric-val {{
        font-size: {UI['metric_value_font_size']}px; font-weight: 800;
        font-family: {UI['font_family_data']}; line-height: 1.1;
    }}
    .metric-lbl {{
        font-size: {UI['metric_label_font_size']}px; color: {UI['text_muted']};
        text-transform: uppercase; letter-spacing: 0.5px; margin-top: 0.05rem;
    }}

    /* === SIGNAL BANNER === */
    .signal-banner {{
        text-align: center; padding: 0.25rem 0.5rem; margin: 0.1rem 0;
        border-radius: 3px; font-weight: 700;
        border: 1px solid;
    }}
    .signal-type {{
        font-size: {UI['signal_font_size']}px; font-weight: 800;
        letter-spacing: 1px; font-family: {UI['font_family_data']};
    }}
    .signal-action {{
        font-size: {UI['signal_action_font_size']}px;
        color: {UI['text_secondary']}; margin-top: 0.05rem;
    }}

    /* === DIVERGENCE ALERT === */
    .div-alert {{
        display: flex; align-items: center; gap: 0.4rem;
        padding: 0.2rem 0.4rem; margin: 0.1rem 0;
        border-radius: 2px; border-left: 3px solid;
        font-size: {UI['divergence_font_size']}px;
        background: {UI['bg_secondary']};
    }}
    .div-label {{ font-weight: 700; font-family: {UI['font_family_data']}; }}
    .div-desc {{ font-size: {UI['divergence_desc_size']}px; color: {UI['text_secondary']}; }}

    /* === SECTION HEADER === */
    .section-header {{
        font-size: 8px; font-weight: 700; color: {UI['text_muted']};
        padding: 0.2rem 0.3rem 0.1rem; letter-spacing: 2px;
        text-transform: uppercase; border-bottom: 1px solid {UI['border_color']};
        margin-top: 0.1rem; font-family: {UI['font_family_data']};
    }}

    /* === CATEGORY ROW === */
    .cat-row {{
        display: flex; align-items: center; padding: 0.18rem 0.3rem;
        border-bottom: 1px solid {UI['bg_secondary']};
    }}
    .cat-icon {{
        font-size: 7px; font-weight: 700; min-width: 26px;
        color: {UI['text_muted']}; font-family: {UI['font_family_data']};
    }}
    .cat-name {{
        flex: 1; color: {UI['text_secondary']};
        font-size: {UI['category_font_size']}px;
    }}
    .cat-score {{
        font-weight: 800; font-family: {UI['font_family_data']};
        min-width: 38px; text-align: right;
        font-size: {UI['category_score_font_size']}px;
    }}
    .cat-bar-wrap {{
        width: {UI['category_bar_width']}px;
        height: {UI['category_bar_height']}px;
        background: {UI['bg_tertiary']}; border-radius: 2px;
        margin: 0 0.4rem; overflow: hidden;
    }}
    .cat-bar-fill {{
        height: 100%; border-radius: 2px;
        transition: width 0.4s ease;
    }}

    /* === ASSET TABLE === */
    .ast-table {{ width: 100%; border-collapse: collapse; }}
    .ast-table th {{
        text-align: left; padding: 0.12rem 0.3rem;
        color: {UI['text_muted']}; font-size: {UI['asset_table_header_size']}px;
        text-transform: uppercase; letter-spacing: 0.5px;
        border-bottom: 1px solid {UI['border_color']};
        font-family: {UI['font_family_data']};
    }}
    .ast-table td {{
        padding: 0.12rem 0.3rem;
        border-bottom: 1px solid {UI['bg_secondary']};
        font-family: {UI['font_family_data']};
        font-size: {UI['asset_table_row_size']}px;
        height: {UI['asset_row_height']}px;
        line-height: {UI['asset_row_height']}px;
    }}
    .ast-table tr:hover {{ background-color: {UI['bg_tertiary']}; }}
    .ast-name {{ width: {UI['asset_name_width']}px; font-weight: 600; }}
    .ast-price {{ width: {UI['asset_price_width']}px; text-align: right; color: {UI['text_secondary']}; }}
    .ast-change {{ width: {UI['asset_change_width']}px; text-align: right; font-weight: 600; }}
    .ast-dir {{ width: {UI['asset_dir_width']}px; text-align: center; }}
    .ast-contrib {{ width: {UI['asset_contrib_width']}px; text-align: right; }}
    .pos {{ color: {UI['positive']}; }}
    .neg {{ color: {UI['negative']}; }}
    .neu {{ color: {UI['neutral']}; }}
    .src-m {{ font-size: 7px; background: #1b5e2022; color: #4CAF50; padding: 0 3px; border-radius: 2px; }}
    .src-y {{ font-size: 7px; background: #0d47a122; color: #42A5F5; padding: 0 3px; border-radius: 2px; }}

    /* === DIVIDER === */
    .divider {{ border-top: 1px solid {UI['border_color']}; margin: 0.1rem 0; }}

    /* === CONTROLS === */
    .ctrl-bar {{
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.15rem 0.3rem; background: {UI['bg_secondary']};
        border-top: 1px solid {UI['border_color']}; margin-top: 0.05rem;
    }}
    .ctrl-info {{
        font-size: 8px; color: {UI['text_muted']};
        font-family: {UI['font_family_data']};
    }}

    /* === BUTTONS === */
    .stButton>button {{
        background: {UI['bg_tertiary']}; color: {UI['text_secondary']};
        border: 1px solid {UI['border_light']}; font-size: 10px;
        font-weight: 600; border-radius: 3px; padding: 0.15rem 0.5rem;
        font-family: {UI['font_family_ui']}; transition: all 0.15s;
    }}
    .stButton>button:hover {{
        background: {UI['border_light']}; color: {UI['text_primary']};
        border-color: {UI['accent']};
    }}

    /* === SELECTBOX === */
    .stSelectbox div[data-baseweb="select"] {{
        background: {UI['bg_tertiary']}; border: 1px solid {UI['border_light']};
        border-radius: 3px; min-height: 1.5rem; font-size: 10px;
    }}

    /* === TABS === */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0; background: {UI['bg_secondary']};
        border-bottom: 1px solid {UI['border_color']};
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 1.8rem; font-size: 9px; font-weight: 700;
        letter-spacing: 1px; color: {UI['text_muted']};
        padding: 0 0.8rem; font-family: {UI['font_family_data']};
    }}
    .stTabs [aria-selected="true"] {{
        color: {UI['accent']} !important;
        border-bottom: 2px solid {UI['accent']} !important;
        background: {UI['bg_primary']};
    }}
    .stTabs [data-baseweb="tab-panel"] {{ padding: 0; }}

    /* === STAT CARDS (analysis) === */
    .stat-card {{
        text-align: center; padding: 0.15rem; background: {UI['bg_secondary']};
        border-radius: 3px; border: 1px solid {UI['border_color']};
    }}
    .stat-val {{
        font-size: 14px; font-weight: 800;
        font-family: {UI['font_family_data']}; line-height: 1.2;
    }}
    .stat-lbl {{
        font-size: 7px; color: {UI['text_muted']};
        text-transform: uppercase; letter-spacing: 0.5px;
    }}

    /* === SUGGESTION === */
    .sug-item {{
        padding: 0.12rem 0.3rem; border-bottom: 1px solid {UI['bg_secondary']};
        display: flex; gap: 0.3rem; font-size: 9px;
    }}
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
    win_data = all_data.get("WIN") or all_data.get("EWZ")
    if win_data and win_data.get("current_price"):
        st.session_state.win_price = win_data["current_price"]
        st.session_state.win_change = win_data.get("change_pct")
        div_detector.update_win_price(win_data["current_price"])
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
    src_clr = UI['positive'] if mt5_on else "#42A5F5"

    st.markdown(f"""
    <div class="top-bar">
        <span class="top-title">MACRO SCORING WIN</span>
        <span class="top-status">
            <span style="color:{src_clr}">{src_txt}</span>
            {avail}/{total}
            <span style="color:{UI['text_muted']}">|</span>
            {last_r.strftime("%H:%M:%S")}
            <span style="color:{UI['text_muted']}">|</span>
            #{st.session_state.refresh_count}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ---- SCORE PRINCIPAL (CSS only, no Plotly) ----
    # Zone bar indicator position (score -100 to 100 -> 0% to 100%)
    indicator_pct = max(0, min(100, (score + 100) / 200 * 100))
    glow_class = "score-glow" if UI.get("score_glow", True) else ""

    st.markdown(f"""
    <div class="score-panel">
        <div class="score-number {glow_class}" style="color:{score_color}">{score:+.1f}</div>
        <div class="score-signal-label" style="color:{score_color}">{signal.get('label', 'N/A')}</div>
        <div class="score-confidence">{signal.get('confidence', '')} | Raw: {score_result.get('raw_score', 0):.4f} | W: {score_result.get('total_weight_used', 0):.3f}</div>
        <div class="zone-bar">
            <div class="zone-indicator" style="left:{indicator_pct}%"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- METRIC STRIP ----
    delta_color = UI['positive'] if delta_val > 0 else UI['negative'] if delta_val < 0 else UI['neutral']
    mom_color = UI['positive'] if momentum_val > 0 else UI['negative'] if momentum_val < 0 else UI['neutral']
    win_ch = st.session_state.get("win_change")
    win_str = f"{win_ch:+.2f}%" if win_ch is not None else "N/A"
    win_color = UI['positive'] if (win_ch or 0) > 0 else UI['negative'] if (win_ch or 0) < 0 else UI['neutral']

    if confluence.get("score_delta_aligned"):
        conf_html = f'<span style="color:{UI["positive"]}">CONFLUI</span>'
    elif confluence.get("reversal_detected"):
        conf_html = f'<span style="color:{UI["warning"]}">REVERT</span>'
    else:
        conf_html = f'<span style="color:{UI["text_muted"]}">---</span>'

    st.markdown(f"""
    <div class="metric-strip">
        <div class="metric-item">
            <div class="metric-val" style="color:{delta_color}">{delta_val:+.1f}</div>
            <div class="metric-lbl">Delta</div>
        </div>
        <div class="metric-item">
            <div class="metric-val" style="color:{mom_color}">{momentum_val:+.1f}</div>
            <div class="metric-lbl">Momentum</div>
        </div>
        <div class="metric-item">
            <div class="metric-val" style="color:{win_color}">{win_str}</div>
            <div class="metric-lbl">WIN/Proxy</div>
        </div>
        <div class="metric-item">
            <div class="metric-val">{conf_html}</div>
            <div class="metric-lbl">Confluencia</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- SIGNAL BANNER ----
    etype = entry.get("type", "NEUTRO")
    elabel = entry.get("label", "SEM SINAL")
    econf = entry.get("confidence", "")
    eaction = entry.get("action", "")

    if "COMPRA_FORTE" in etype:
        sbg, sborder, scolor = "#0a2e0a", UI['positive'], UI['positive']
    elif "COMPRA" in etype:
        sbg, sborder, scolor = "#0a1f0a", "#66BB6A", "#66BB6A"
    elif "VENDA_FORTE" in etype:
        sbg, sborder, scolor = "#2e0a0a", UI['negative'], UI['negative']
    elif "VENDA" in etype:
        sbg, sborder, scolor = "#1f0a0a", "#EF5350", "#EF5350"
    elif "REVERSAO" in etype:
        sbg, sborder, scolor = "#2e2a0a", UI['warning'], UI['warning']
    else:
        sbg, sborder, scolor = UI['bg_secondary'], UI['border_color'], UI['neutral']

    st.markdown(f"""
    <div class="signal-banner" style="background:{sbg}; border-color:{sborder}30;">
        <div class="signal-type" style="color:{scolor}">{elabel} <span style="font-size:8px;color:{sborder}88">{econf}</span></div>
        <div class="signal-action">{eaction}</div>
    </div>
    """, unsafe_allow_html=True)

    # ---- DIVERGENCE ALERT ----
    if divergence and divergence.get("type") not in ("INDEFINIDO",):
        div_label = divergence.get("label", "")
        div_color = divergence.get("color", UI['neutral'])
        div_desc = divergence.get("description", "")
        div_icon = divergence.get("icon", "")
        div_bg = f"{UI['warning']}08" if "DIVERGENCIA" in divergence.get("type", "") else f"{UI['positive']}08"

        st.markdown(f"""
        <div class="div-alert" style="background:{div_bg}; border-left-color:{div_color};">
            <span class="div-label" style="color:{div_color}">{div_icon} {div_label}</span>
            <span class="div-desc">{div_desc[:90]}</span>
        </div>
        """, unsafe_allow_html=True)

    # ---- CATEGORIAS ----
    category_scores = score_result.get("category_scores", {})
    st.markdown('<div class="section-header">CATEGORIAS</div>', unsafe_allow_html=True)

    for cat_name, cat_data in category_scores.items():
        cat_score = cat_data.get("normalized", 0)
        cat_color = get_score_color(cat_score)
        cat_icon = ""
        for cname, cinfo in CATEGORIES.items():
            if cname == cat_name:
                cat_icon = cinfo.get("icon", "")
                break

        bar_pct = max(0, min(100, (cat_score + 100) / 200 * 100))

        st.markdown(f"""
        <div class="cat-row">
            <span class="cat-icon">{cat_icon}</span>
            <span class="cat-name">{cat_name}</span>
            <div class="cat-bar-wrap">
                <div class="cat-bar-fill" style="width:{bar_pct}%;background:{cat_color};"></div>
            </div>
            <span class="cat-score" style="color:{cat_color}">{cat_score:+.0f}</span>
        </div>
        """, unsafe_allow_html=True)

    # ---- ATIVOS ----
    asset_signals = score_result.get("asset_signals", {})
    st.markdown('<div class="section-header">ATIVOS</div>', unsafe_allow_html=True)

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

        change_str = format_change(change) if change is not None else "N/A"
        ch_cls = "pos" if (change or 0) > 0 else "neg" if (change or 0) < 0 else "neu"
        co_cls = "pos" if contribution > 0.001 else "neg" if contribution < -0.001 else "neu"
        dir_icon = "&#9650;" if direction > 0 else "&#9660;"
        dir_cls = "pos" if direction > 0 else "neg"
        src_cls = "src-m" if "mt5" in source else "src-y"
        src_txt = "M" if "mt5" in source else "Y"
        price_str = format_price(price) if price else "---"

        asset_rows += f"""
        <tr>
            <td class="ast-name"><span class="{src_cls}">{src_txt}</span> {asset_name}</td>
            <td class="ast-price">{price_str}</td>
            <td class="ast-change {ch_cls}">{change_str}</td>
            <td class="ast-dir {dir_cls}">{dir_icon}</td>
            <td class="ast-contrib {co_cls}">{contribution:+.3f}</td>
        </tr>"""

    st.markdown(f"""
    <table class="ast-table">
        <thead><tr>
            <th>Ativo</th><th style="text-align:right">Preco</th>
            <th style="text-align:right">Var</th><th style="text-align:center">Dir</th>
            <th style="text-align:right">Contrib</th>
        </tr></thead>
        <tbody>{asset_rows}</tbody>
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
            line=dict(color=UI['accent'], width=1.5, shape='spline'),
            fill='tozeroy', fillcolor=f"rgba(79, 195, 247, 0.06)",
        ))
        fig.add_hline(y=60, line_dash="dash", line_color=f"{UI['positive']}30", line_width=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#66BB6A20", line_width=1)
        fig.add_hline(y=0, line_dash="solid", line_color="#ffffff10", line_width=0.5)
        fig.add_hline(y=-30, line_dash="dot", line_color="#EF535020", line_width=1)
        fig.add_hline(y=-60, line_dash="dash", line_color=f"{UI['negative']}30", line_width=1)

        fig.update_layout(
            height=UI.get("chart_height", 130),
            margin=dict(l=25, r=10, t=5, b=15),
            yaxis=dict(range=[-100, 100], title="",
                       tickfont=dict(size=7, color=UI['text_muted']),
                       gridcolor=UI['bg_tertiary'], zeroline=False),
            xaxis=dict(title="", tickfont=dict(size=6, color=UI['text_muted']),
                       gridcolor=UI['bg_secondary']),
            template="plotly_dark",
            paper_bgcolor=UI['bg_primary'],
            plot_bgcolor=UI['bg_primary'],
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---- CONTROLS ----
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

    # Missing
    missing = score_result.get("missing_assets", [])
    if missing:
        st.markdown(f'<div style="color:{UI["negative"]};font-size:8px;text-align:center;padding:0.05rem;">Sem dados: {", ".join(missing[:6])}{"..." if len(missing) > 6 else ""}</div>', unsafe_allow_html=True)

    # Auto refresh
    refresh_seconds = st.session_state.interval
    st.markdown(f"""
    <div class="ctrl-bar">
        <span class="ctrl-info">Auto-refresh {refresh_seconds}s</span>
        <span class="ctrl-info">v2.1</span>
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
