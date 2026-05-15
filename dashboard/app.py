"""
Dashboard Profissional - Macro Scoring WIN v5.0
=================================================
Layout ultra-compacto: blocos lado a lado, sem scroll.
Modulos v5.0: ScoreSmoother, PriceReversal, RegimeDetector,
SignalManager, PerformanceTracker, AlertSystem, Dynamic Contracts.

Para rodar: streamlit run dashboard/app.py
"""

import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go

from config import (
    MT5_CONFIG, DUAL_SOURCE_ASSETS, YF_SYMBOLS, MACRO_WEIGHTS,
    SIGNAL_CONFIG, CATEGORIES, DASHBOARD_CONFIG, LOG_CONFIG,
    WIN_TRACKING, DIVERGENCE_CONFIG, UI_CONFIG,
    SECTOR_GROUPS, MULTI_TIMEFRAME_CONFIG, KEY_LEVELS_CONFIG,
    SCORE_SMOOTHER_CONFIG, PRICE_REVERSAL_CONFIG, ALERT_CONFIG,
    SIGNAL_FILTER_CONFIG, PERFORMANCE_CONFIG, REGIME_CONFIG,
    WIN_CONTRACT_CONFIG, MT5_SYMBOLS,
)
from data_sources.data_manager import DataManager
from data_sources.sector_data import SectorDataManager
from scoring.macro_score import MacroScorer
from scoring.delta import DeltaAnalyzer
from scoring.divergence import DivergenceDetector
from scoring.key_levels import KeyLevelsCalculator
from scoring.score_smoother import ScoreSmoother
from scoring.price_reversal import PriceReversalDetector
from scoring.regime_detector import RegimeDetector
from scoring.signal_manager import SignalManager
from scoring.performance_tracker import PerformanceTracker
from utils.alert_system import AlertSystem
from utils.helpers import (
    format_change, format_price, get_change_color, get_score_color,
    get_active_win_contract, get_active_wdo_contract,
)
from utils.macro_logger import MacroLogger
from dashboard.analysis_tab import render_analysis_tab

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UI = UI_CONFIG

st.set_page_config(page_title="Macro WIN", page_icon="W", layout="centered",
                   initial_sidebar_state="collapsed")

# ============ CSS ULTRA-COMPACT ============
st.markdown(f"""
<style>
    .stApp {{background:{UI['bg_primary']};color:{UI['text_primary']};}}
    .block-container {{
        padding-top:0;padding-bottom:0;padding-left:5px;padding-right:5px;
        max-width:{UI['panel_width']}px;font-family:{UI['font_family_ui']};
    }}
    section[data-testid="stSidebar"]{{display:none}}
    #MainMenu,footer,header{{visibility:hidden}}

    /* ALERT NOTIFICATION */
    .alert-bar{{display:flex;align-items:center;gap:4px;padding:2px 6px;border-radius:2px;border:1px solid;margin:1px 0;font-size:7px;font-family:{UI['font_family_data']};animation:alertPulse 1.5s ease-in-out}}
    @keyframes alertPulse {{0%{{opacity:0.5}}100%{{opacity:1}}}}
    .alert-icon{{font-size:9px}}
    .alert-msg{{color:{UI['text_secondary']};font-size:6px;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .alert-type{{font-weight:800;letter-spacing:0.5px}}

    /* STATUS BAR */
    .sbar{{display:flex;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']};font-family:{UI['font_family_data']};font-size:8px}}
    .sc{{padding:2px 5px;border-right:1px solid {UI['border_color']};display:flex;align-items:center;gap:2px;white-space:nowrap}}
    .sc:last-child{{border-right:none}}
    .sl{{color:{UI['text_muted']};font-size:6px;text-transform:uppercase}}
    .sv{{font-weight:700;font-size:8px}}

    /* SCORE ROW: direction | score+zone | conf */
    .srow{{display:flex;align-items:center;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']};padding:2px 4px;gap:4px}}
    .sdir{{font-size:14px;font-weight:900;font-family:{UI['font_family_data']};letter-spacing:1px;min-width:55px;text-align:center;padding:1px;border-radius:2px}}
    .smid{{flex:1;text-align:center}}
    .snum{{font-size:32px;font-weight:900;font-family:{UI['font_family_data']};line-height:1;letter-spacing:-1px}}
    .sema{{font-size:14px;font-weight:700;font-family:{UI['font_family_data']};line-height:1}}
    .slbl{{font-size:6px;color:{UI['text_muted']};letter-spacing:0.5px}}
    .sglow{{text-shadow:0 0 15px currentColor,0 0 30px currentColor}}
    .strend{{font-size:6px;color:{UI['text_secondary']};letter-spacing:1px}}
    .zbar{{width:100%;height:2px;margin-top:1px;background:linear-gradient(to right,{UI['negative']} 0%,{UI['negative']} 15%,#FF7043 20%,{UI['warning']} 35%,{UI['warning']} 65%,#66BB6A 80%,{UI['positive']} 85%,{UI['positive']} 100%);position:relative;border-radius:1px}}
    .zind{{position:absolute;top:-3px;width:2px;height:8px;background:#fff;border-radius:1px}}
    .srt{{text-align:right;min-width:70px}}
    .sconf{{font-size:6px;color:{UI['text_muted']}}}

    /* METRIC STRIP */
    .mstrip{{display:flex;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']}}}
    .mc{{flex:1;text-align:center;padding:1px 0;border-right:1px solid {UI['border_color']}}}
    .mc:last-child{{border-right:none}}
    .mv{{font-size:11px;font-weight:800;font-family:{UI['font_family_data']};line-height:1}}
    .ml{{font-size:6px;color:{UI['text_muted']};text-transform:uppercase;letter-spacing:.5px}}

    /* SIGNAL BANNER */
    .sigb{{text-align:center;padding:2px;border-radius:2px;border:1px solid;margin:1px 0}}
    .sigt{{font-size:11px;font-weight:800;letter-spacing:1px;font-family:{UI['font_family_data']}}}
    .siga{{font-size:7px;color:{UI['text_secondary']}}}

    /* RECOVERY / REGIME / REVERSAL BANNER */
    .recb{{display:flex;align-items:center;gap:4px;padding:2px 4px;border-left:3px solid;font-size:7px;margin:1px 0;background:{UI['bg_secondary']}}}
    .recl{{font-weight:800;font-family:{UI['font_family_data']};font-size:8px}}
    .recd{{color:{UI['text_secondary']};font-size:6px;flex:1}}

    /* SECTOR GRID - 4 colunas! */
    .sgrid{{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:1px;padding:1px}}
    .sblk{{background:{UI['bg_sector']};border:1px solid {UI['border_color']};border-radius:1px;padding:2px 3px}}
    .shdr{{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid {UI['border_color']}40;padding-bottom:1px;margin-bottom:1px}}
    .snm{{font-size:6px;font-weight:700;font-family:{UI['font_family_data']};letter-spacing:.5px}}
    .ssc{{font-size:9px;font-weight:900;font-family:{UI['font_family_data']}}}
    .sar{{display:flex;align-items:center;gap:2px;padding:0;font-size:7px;font-family:{UI['font_family_data']}}}
    .san{{min-width:32px;color:{UI['text_secondary']};font-size:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .sv5{{font-weight:600;min-width:30px;text-align:right;font-size:6px}}
    .svd{{font-weight:700;min-width:34px;text-align:right;font-size:7px}}

    /* TWO-COL: levels + filters */
    .twocol{{display:grid;grid-template-columns:1fr 1fr;gap:1px;padding:1px}}
    .sech{{font-size:6px;font-weight:700;color:{UI['text_muted']};padding:1px 3px;letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid {UI['border_color']};font-family:{UI['font_family_data']};display:flex;justify-content:space-between}}
    .secr{{font-size:6px;color:{UI['text_secondary']}}}

    /* LEVEL ROWS */
    .lrow{{display:flex;align-items:center;gap:3px;padding:0;font-family:{UI['font_family_data']};border-bottom:1px solid {UI['border_color']}15}}
    .ldot{{width:4px;height:4px;border-radius:50%;min-width:4px}}
    .lnm{{min-width:28px;font-size:7px;font-weight:700;text-align:center}}
    .lpr{{font-size:8px;font-weight:700;min-width:52px;text-align:right}}
    .ldi{{font-size:6px;color:{UI['text_muted']};flex:1;text-align:right}}
    .lcur{{width:100%;height:1px;background:{UI['level_current']};margin:0;position:relative}}
    .lcul{{position:absolute;right:0;top:-7px;font-size:6px;font-weight:900;color:{UI['level_current']};font-family:{UI['font_family_data']}}}

    /* FILTER ROWS */
    .frow{{display:flex;align-items:center;gap:2px;padding:0;font-size:7px;border-bottom:1px solid {UI['bg_secondary']}1}}
    .fico{{font-size:7px;min-width:10px;text-align:center}}
    .ftxt{{color:{UI['text_secondary']};font-size:6px}}
    .fval{{font-weight:700;font-family:{UI['font_family_data']};font-size:7px;margin-left:auto}}

    /* FEELING BAR */
    .fbar{{display:flex;align-items:center;gap:3px;padding:1px 4px;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']};font-size:7px}}
    .fbl{{color:{UI['text_muted']};font-size:6px;text-transform:uppercase;letter-spacing:.5px}}
    .fbv{{font-weight:900;font-size:9px;font-family:{UI['font_family_data']}}}
    .fbd{{color:{UI['text_secondary']};font-size:6px;font-family:{UI['font_family_data']}}}

    /* LOG TABLE */
    .ltbl{{width:100%;border-collapse:collapse}}
    .ltbl th{{text-align:left;padding:0 2px;color:{UI['text_muted']};font-size:5px;text-transform:uppercase;letter-spacing:.3px;border-bottom:1px solid {UI['border_color']};font-family:{UI['font_family_data']}}}
    .ltbl td{{padding:0 2px;border-bottom:1px solid {UI['bg_secondary']};font-family:{UI['font_family_data']};font-size:7px}}

    .pos{{color:{UI['positive']}}}.neg{{color:{UI['negative']}}}.neu{{color:{UI['neutral']}}}.wrn{{color:{UI['warning']}}}
    .src-m{{font-size:5px;background:#1b5e2022;color:#4CAF50;padding:0 1px;border-radius:1px}}
    .src-y{{font-size:5px;background:#0d47a122;color:#42A5F5;padding:0 1px;border-radius:1px}}

    /* Controls */
    .stButton>button{{background:{UI['bg_tertiary']};color:{UI['text_secondary']};border:1px solid {UI['border_light']};font-size:8px;font-weight:600;border-radius:2px;padding:1px 4px;font-family:{UI['font_family_ui']}}}
    .stSelectbox div[data-baseweb="select"]{{background:{UI['bg_tertiary']};border:1px solid {UI['border_light']};border-radius:2px;min-height:1.1rem;font-size:8px}}
    .stTabs [data-baseweb="tab-list"]{{gap:0;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']}}}
    .stTabs [data-baseweb="tab"]{{height:1.2rem;font-size:7px;font-weight:700;letter-spacing:1px;color:{UI['text_muted']};padding:0 .4rem;font-family:{UI['font_family_data']}}}
    .stTabs [aria-selected="true"]{{color:{UI['accent']}!important;border-bottom:2px solid {UI['accent']}!important;background:{UI['bg_primary']}}}
    .stTabs [data-baseweb="tab-panel"]{{padding:0}}
</style>
""", unsafe_allow_html=True)


# ============ HELPER: Resolve AUTO contract ============
def resolve_win_contract():
    """Resolve WIN contract when mt5_symbol is AUTO."""
    try:
        if WIN_TRACKING.get("mt5_symbol") == "AUTO" and WIN_CONTRACT_CONFIG.get("enabled", True):
            roll = WIN_CONTRACT_CONFIG.get("roll_days_before", 3)
            return get_active_win_contract(roll_days_before=roll)
    except Exception:
        pass
    return None

def resolve_wdo_contract():
    """Resolve WDO contract when MT5_SYMBOLS WIN is AUTO."""
    try:
        if MT5_SYMBOLS.get("WDO") == "AUTO" and WIN_CONTRACT_CONFIG.get("enabled", True):
            roll = WIN_CONTRACT_CONFIG.get("roll_days_before", 3)
            return get_active_wdo_contract(roll_days_before=roll)
    except Exception:
        pass
    return None


# ============ INIT ============
def init_session_state():
    if "data_manager" not in st.session_state:
        # Resolve AUTO contracts for WIN_TRACKING
        wt = dict(WIN_TRACKING)
        if wt.get("mt5_symbol") == "AUTO":
            resolved = resolve_win_contract()
            if resolved:
                wt["mt5_symbol"] = resolved
                logger.info(f"WIN contract resolved: {resolved}")

        dm = DataManager(mt5_config=MT5_CONFIG, dual_source=DUAL_SOURCE_ASSETS,
                         yf_only=YF_SYMBOLS, win_tracking=wt)
        st.session_state.data_manager = dm
        st.session_state.scorer = MacroScorer(MACRO_WEIGHTS, SIGNAL_CONFIG)
        st.session_state.delta_analyzer = DeltaAnalyzer(SIGNAL_CONFIG)
        st.session_state.divergence_detector = DivergenceDetector(DIVERGENCE_CONFIG)
        st.session_state.key_levels = KeyLevelsCalculator(KEY_LEVELS_CONFIG)
        st.session_state.sector_manager = SectorDataManager(SECTOR_GROUPS, MULTI_TIMEFRAME_CONFIG)
        st.session_state.macro_logger = MacroLogger(LOG_CONFIG)

        # v5.0 modules
        st.session_state.score_smoother = ScoreSmoother(SCORE_SMOOTHER_CONFIG)
        st.session_state.price_reversal = PriceReversalDetector(PRICE_REVERSAL_CONFIG)
        st.session_state.regime_detector = RegimeDetector(REGIME_CONFIG)
        st.session_state.signal_manager = SignalManager(SIGNAL_FILTER_CONFIG)
        st.session_state.performance_tracker = PerformanceTracker(PERFORMANCE_CONFIG)
        st.session_state.alert_system = AlertSystem(ALERT_CONFIG)

        # State
        st.session_state.score_history = []
        st.session_state.signal_log = []
        st.session_state.last_data = {}
        st.session_state.mt5_status = None
        st.session_state.refresh_count = 0
        st.session_state.interval = 30
        st.session_state.win_price = None
        st.session_state.win_change = None
        st.session_state.sectors_data = {}

        # v5.0 results cache
        st.session_state.smoothed_result = {}
        st.session_state.reversal_result = {}
        st.session_state.regime_result = {}
        st.session_state.filtered_signal = {}
        st.session_state.perf_stats = {}
        st.session_state.alert_result = {}
        st.session_state.alert_html = ""
        st.session_state.active_win_contract = resolve_win_contract() or "---"
        st.session_state.active_wdo_contract = resolve_wdo_contract() or "---"

init_session_state()


def refresh_data():
    dm = st.session_state.data_manager
    all_data = dm.get_all_data()
    st.session_state.last_data = all_data

    scorer = st.session_state.scorer
    score_result = scorer.calculate_score(all_data)
    st.session_state.score_result = score_result

    score = score_result["score"]
    category_scores = score_result.get("category_scores", {})

    delta_analyzer = st.session_state.delta_analyzer
    delta_analyzer.update(score)
    delta_result = delta_analyzer.get_entry_signal(score_result)
    st.session_state.delta_result = delta_result
    delta_val = delta_result.get("delta", 0)

    div_detector = st.session_state.divergence_detector
    div_detector.update_score(score)
    win_data = all_data.get("WIN") or all_data.get("EWZ")
    win_price = None
    win_change_pct = None
    if win_data and win_data.get("current_price"):
        win_price = win_data["current_price"]
        win_change_pct = win_data.get("change_pct")
        st.session_state.win_price = win_price
        st.session_state.win_change = win_change_pct
        div_detector.update_win_price(win_data["current_price"])
    st.session_state.divergence_result = div_detector.check_divergence()

    kl = st.session_state.key_levels
    if st.session_state.win_price:
        kl.update_win_data(current_price=st.session_state.win_price)
    ewz_data = all_data.get("EWZ", {})
    ibov_data = all_data.get("IBOV", {})
    if ewz_data:
        kl.calculate_from_ewz(ewz_data, ibov_data)
    st.session_state.levels_result = kl.get_full_analysis(score)

    # ==== v5.0: Score Smoother ====
    st.session_state.score_smoother.add_score(score)
    smoothed = st.session_state.score_smoother.get_both()
    st.session_state.smoothed_result = smoothed

    # ==== v5.0: Price Reversal Detector ====
    pr = st.session_state.price_reversal
    if win_price is not None and win_change_pct is not None:
        pr.update_win_price(win_price, win_change_pct)
    pr.update_score(score, delta_val)
    reversal_result = pr.check_price_reversal()
    st.session_state.reversal_result = reversal_result

    # ==== v5.0: Regime Detector ====
    st.session_state.regime_detector.update(score, delta_val)
    regime_result = st.session_state.regime_detector.detect_regime()
    st.session_state.regime_result = regime_result

    # ==== v5.0: Signal Manager (Confluence Filter) ====
    entry_type = delta_result.get("entry_signal", {}).get("type", "NEUTRO")
    divergence_result = st.session_state.divergence_result
    recovery = delta_result.get("intraday_recovery")
    filtered_signal = st.session_state.signal_manager.process_signal(
        signal_type=entry_type,
        score=score,
        delta=delta_val,
        sector_data=category_scores,
        divergence=divergence_result,
        recovery=recovery,
    )
    st.session_state.filtered_signal = filtered_signal

    # ==== v5.0: Performance Tracker ====
    if entry_type != "NEUTRO" and st.session_state.win_price:
        st.session_state.performance_tracker.register_signal(
            signal_type=entry_type,
            score=score,
            delta=delta_val,
            win_price=st.session_state.win_price,
            timestamp=datetime.now(),
            levels_result=st.session_state.levels_result,
        )
    if st.session_state.win_price:
        st.session_state.performance_tracker.check_outcomes(st.session_state.win_price)
    st.session_state.perf_stats = st.session_state.performance_tracker.get_statistics()

    # ==== v5.0: Alert System ====
    prev_signal = st.session_state.alert_system._last_signal_type
    signal_change = (prev_signal is not None and prev_signal != entry_type)
    alert_result = st.session_state.alert_system.check_and_alert(
        signal_change=signal_change,
        signal_type=entry_type,
        score=score,
        divergence=divergence_result,
        recovery=recovery,
        reversal=reversal_result,
    )
    st.session_state.alert_result = alert_result
    if alert_result.get("alert_fired"):
        st.session_state.alert_html = st.session_state.alert_system.get_alert_html(
            alert_result.get("alert_type", ""),
            alert_result.get("message", ""),
        )
    else:
        st.session_state.alert_html = ""

    now = datetime.now()
    st.session_state.score_history.append({
        "timestamp": now, "score": score,
        "signal_type": score_result["signal"]["type"],
        "delta": delta_val,
        "momentum": delta_result.get("momentum", 0),
    })
    if len(st.session_state.score_history) > 500:
        st.session_state.score_history = st.session_state.score_history[-500:]

    entry = delta_result.get("entry_signal", {})
    if entry.get("type", "NEUTRO") != "NEUTRO":
        st.session_state.signal_log.append({
            "time": now.strftime("%H:%M:%S"), "direction": entry.get("label", ""),
            "score": score, "delta": delta_val,
            "confidence": entry.get("confidence", ""),
            "filtered": filtered_signal.get("final_action", entry.get("type", "")),
        })
        if len(st.session_state.signal_log) > 50:
            st.session_state.signal_log = st.session_state.signal_log[-50:]

    st.session_state.refresh_count += 1
    st.session_state.last_refresh = now

    if st.session_state.refresh_count % 2 == 0 or not st.session_state.sectors_data:
        try:
            st.session_state.sectors_data = st.session_state.sector_manager.get_all_sectors()
        except Exception as e:
            logger.warning(f"Erro setores: {e}")

    mlog = st.session_state.macro_logger
    mlog.log_full_cycle(score_result, delta_result, all_data)
    div_r = st.session_state.divergence_result
    if div_r and div_r.get("type") not in ("INDEFINIDO", "NEUTRO"):
        mlog._log_session_event("DIVERGENCE", {"type": div_r["type"], "label": div_r["label"], "severity": div_r["severity"]})

    # Log v5.0 events
    if reversal_result and reversal_result.get("detected"):
        mlog._log_session_event("PRICE_REVERSAL", {
            "type": reversal_result["type"], "strength": reversal_result.get("strength", ""),
            "direction": reversal_result.get("direction", ""),
        })
    if regime_result and regime_result.get("regime") not in ("INDEFINIDO",):
        mlog._log_session_event("REGIME", {
            "regime": regime_result["regime"], "label": regime_result.get("label", ""),
        })

    return score_result


def vc(val):
    """Color class for value"""
    if val is None: return "neu"
    return "pos" if val > 0 else "neg" if val < 0 else "neu"

def vs(val):
    """Format variation string"""
    if val is None: return "---"
    return f"{val:+.2f}%"


# ============ LAYOUT ============
tab_mesa, tab_analysis = st.tabs(["MESA", "ANALISE"])

with tab_mesa:
    if not st.session_state.get("score_result"):
        with st.spinner("Conectando..."):
            refresh_data()

    sr = st.session_state.get("score_result", {})
    if not sr:
        st.error("Sem dados. Verifique conexao.")
        st.stop()

    score = sr.get("score", 0)
    signal = sr.get("signal", {})
    score_color = get_score_color(score)
    dr = st.session_state.get("delta_result", {})
    delta_val = dr.get("delta", 0)
    mom_val = dr.get("momentum", 0)
    entry = dr.get("entry_signal", {})
    conf = dr.get("confluence", {})
    div = st.session_state.get("divergence_result", {})
    ad = st.session_state.get("last_data", {})
    sd = st.session_state.get("sectors_data", {})
    lr = st.session_state.get("levels_result", {})
    recovery = dr.get("intraday_recovery")
    rev_down = dr.get("intraday_reversal_down")

    # v5.0 results
    smoothed = st.session_state.get("smoothed_result", {})
    reversal_result = st.session_state.get("reversal_result", {})
    regime_result = st.session_state.get("regime_result", {})
    filtered_signal = st.session_state.get("filtered_signal", {})
    perf_stats = st.session_state.get("perf_stats", {})

    # ==== 0. ALERT NOTIFICATION (top) ====
    alert_html = st.session_state.get("alert_html", "")
    if alert_html:
        st.markdown(alert_html, unsafe_allow_html=True)

    # Compact alert bar
    alert_result = st.session_state.get("alert_result", {})
    if alert_result.get("alert_fired"):
        at = alert_result.get("alert_type", "")
        color_map_alert = {
            "PRICE_REVERSAL": UI['warning'],
            "RECOVERY": UI['positive'],
            "SIGNAL_CHANGE": UI['accent'],
            "STRONG_SIGNAL": UI['negative'],
            "DIVERGENCE": UI['warning'],
        }
        acol = color_map_alert.get(at, UI['neutral'])
        amsg = alert_result.get("message", "").split("\n")[0][:80]
        icon_map_alert = {
            "PRICE_REVERSAL": "&#9889;",
            "RECOVERY": "&#8635;",
            "SIGNAL_CHANGE": "&#128276;",
            "STRONG_SIGNAL": "&#128680;",
            "DIVERGENCE": "&#9888;",
        }
        aicon = icon_map_alert.get(at, "&#128227;")
        st.markdown(f"""
        <div class="alert-bar" style="background:{acol}15;border-color:{acol}40">
            <span class="alert-icon" style="color:{acol}">{aicon}</span>
            <span class="alert-type" style="color:{acol}">{at.replace('_',' ')}</span>
            <span class="alert-msg">{amsg}</span>
        </div>
        """, unsafe_allow_html=True)

    # ==== 1. STATUS BAR ====
    wc = st.session_state.get("win_change")
    wp = st.session_state.win_price
    ws = f"{wp:,.0f}" if wp else "---"
    wcc = f"{wc:+.2f}%" if wc is not None else "---"
    dxy = ad.get("DXY", {})
    vix = ad.get("VIX", {})
    ewz = ad.get("EWZ", {})
    lr_time = st.session_state.get("last_refresh", datetime.now())
    mt5on = st.session_state.get("mt5_status", {}).get("success", False) if st.session_state.get("mt5_status") else False
    srctag = '<span class="src-m">M</span>' if mt5on else '<span class="src-y">Y</span>'

    # Contract info
    win_contract = st.session_state.get("active_win_contract", "---")
    wdo_contract = st.session_state.get("active_wdo_contract", "---")
    contract_html = f'<span class="sl">CT</span><span class="sv" style="color:{UI["text_secondary"]}">{win_contract}</span>'

    st.markdown(f"""
    <div class="sbar">
        <div class="sc" style="background:#1a2535"><span class="sl">LIVE</span></div>
        <div class="sc"><span class="sv" style="color:{UI['warning']}">{lr_time.strftime("%H:%M:%S")}</span></div>
        <div class="sc"><span class="sl">WIN</span><span class="sv">{ws}</span><span class="sv {vc(wc)}">{wcc}</span></div>
        <div class="sc"><span class="sl">DXY</span><span class="sv {vc(dxy.get('change_pct'))}">{dxy.get('change_pct',0):+.2f}%</span></div>
        <div class="sc"><span class="sl">VIX</span><span class="sv" style="color:{UI['warning']}">{vix.get('current_price',0):.1f}</span></div>
        <div class="sc"><span class="sl">EWZ</span><span class="sv {vc(ewz.get('change_pct'))}">{ewz.get('change_pct',0):+.2f}%</span></div>
        <div class="sc">{srctag}<span class="sv" style="color:{UI['text_muted']}">{sr.get('assets_available',0)}/{sr.get('assets_total',0)}</span></div>
        <div class="sc">{contract_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # ==== 2. SCORE ROW (raw + EMA) ====
    dtxt = "COMPRA" if score > 0 else "VENDA" if score < 0 else "NEUTRO"
    dbg = f"{UI['positive']}22" if score > 0 else f"{UI['negative']}22" if score < 0 else f"{UI['neutral']}22"
    dcol = UI['positive'] if score > 0 else UI['negative'] if score < 0 else UI['neutral']
    trend = "MELHORANDO" if delta_val > 5 else "PIORANDO" if delta_val < -5 else "ESTAVEL"
    if conf.get("score_delta_aligned"): trend += " | CONF"
    elif conf.get("reversal_detected"): trend += " | REV"
    if conf.get("recovery_detected"): trend += " | RECUPERACAO"
    ipct = max(0, min(100, (score + 100) / 200 * 100))
    glow = "sglow" if UI.get("score_glow", True) else ""

    # EMA smoothed score
    ema_val = smoothed.get("ema_value")
    ema_delta = smoothed.get("ema_delta")
    ema_color = get_score_color(ema_val) if ema_val is not None else score_color
    ema_str = f"{ema_val:+.1f}" if ema_val is not None else "---"
    ema_delta_str = f"({ema_delta:+.1f})" if ema_delta is not None else ""

    st.markdown(f"""
    <div class="srow">
        <div class="sdir" style="color:{dcol};background:{dbg}">{dtxt}</div>
        <div class="smid">
            <div class="snum {glow}" style="color:{score_color}">{score:+.1f}</div>
            <div style="display:flex;align-items:baseline;justify-content:center;gap:3px">
                <span class="slbl">EMA</span>
                <span class="sema" style="color:{ema_color}">{ema_str}</span>
                <span class="slbl">{ema_delta_str}</span>
            </div>
            <div class="strend">{trend}</div>
            <div class="zbar"><div class="zind" style="left:{ipct}%"></div></div>
        </div>
        <div class="srt">
            <div class="sconf">conf:{signal.get('confidence','---')}</div>
            <div class="sconf">raw:{sr.get('raw_score',0):.3f}</div>
            <div class="sconf">n:{st.session_state.refresh_count}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ==== 3. METRICS ====
    sh = st.session_state.score_history
    ac = 0
    if len(sh) >= 3:
        d1 = sh[-1]["score"] - sh[-2]["score"]
        d2 = sh[-2]["score"] - sh[-3]["score"]
        ac = d1 - d2
    zl = "FORTE" if abs(score) > 60 else "MOD" if abs(score) > 30 else "NEU"

    st.markdown(f"""
    <div class="mstrip">
        <div class="mc"><div class="mv {vc(delta_val)}">{delta_val:+.1f}</div><div class="ml">Delta</div></div>
        <div class="mc"><div class="mv {vc(mom_val)}">{mom_val:+.1f}</div><div class="ml">Mom</div></div>
        <div class="mc"><div class="mv {vc(ac) if abs(ac)>2 else 'neu'}">{ac:+.1f}</div><div class="ml">Acel</div></div>
        <div class="mc"><div class="mv" style="color:{score_color}">{zl}</div><div class="ml">Zona</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ==== 4. SIGNAL BANNER ====
    et = entry.get("type", "NEUTRO")
    el = entry.get("label", "SEM SINAL")
    ec = entry.get("confidence", "")
    ea = entry.get("action", "")

    if "COMPRA_FORTE" in et: sbg,sb,sc2 = "#0a2e0a",UI['positive'],UI['positive']
    elif "COMPRA" in et and "RECUPERACAO" not in et: sbg,sb,sc2 = "#0a1f0a","#66BB6A","#66BB6A"
    elif "RECUPERACAO_FORTE" in et: sbg,sb,sc2 = "#0a2e1a",UI['positive'],UI['positive']
    elif "RECUPERACAO" in et: sbg,sb,sc2 = "#1a2e0a","#66BB6A","#66BB6A"
    elif "VENDA_FORTE" in et: sbg,sb,sc2 = "#2e0a0a",UI['negative'],UI['negative']
    elif "VENDA" in et and "REVERSAO" not in et: sbg,sb,sc2 = "#1f0a0a","#EF5350","#EF5350"
    elif "REVERSAO_BAIXA_INTRADAY" in et: sbg,sb,sc2 = "#2e1a0a",UI['negative'],UI['negative']
    elif "REVERSAO" in et: sbg,sb,sc2 = "#2e2a0a",UI['warning'],UI['warning']
    else: sbg,sb,sc2 = UI['bg_secondary'],UI['border_color'],UI['neutral']

    # Show filtered signal action if different from original
    fs_action = filtered_signal.get("final_action", "")
    fs_was_cooldown = filtered_signal.get("was_cooldown", False)
    fs_downgraded = filtered_signal.get("downgraded", False)
    filter_note = ""
    if fs_was_cooldown:
        filter_note = ' <span style="font-size:6px;color:#FF9800">COOLDOWN</span>'
    elif fs_downgraded:
        filter_note = f' <span style="font-size:6px;color:#FF9800">&rarr; {fs_action}</span>'

    st.markdown(f"""
    <div class="sigb" style="background:{sbg};border-color:{sb}30">
        <div class="sigt" style="color:{sc2}">{el} <span style="font-size:6px;color:{sb}88">{ec}</span>{filter_note}</div>
        <div class="siga">{ea}</div>
    </div>
    """, unsafe_allow_html=True)

    # ==== 4b. RECOVERY BANNER ====
    if recovery and recovery.get("detected"):
        rc = recovery["color"]
        st.markdown(f"""
        <div class="recb" style="border-left-color:{rc};background:{rc}08">
            <span class="recl" style="color:{rc}">RECUPERACAO {recovery['strength']}</span>
            <span class="recd">{recovery['description'][:90]}</span>
        </div>
        """, unsafe_allow_html=True)
    elif rev_down and rev_down.get("detected"):
        rc2 = rev_down["color"]
        st.markdown(f"""
        <div class="recb" style="border-left-color:{rc2};background:{rc2}08">
            <span class="recl" style="color:{rc2}">REVERSAO BAIXA {rev_down['strength']}</span>
            <span class="recd">{rev_down['description'][:90]}</span>
        </div>
        """, unsafe_allow_html=True)

    # ==== 4c. REGIME BANNER ====
    if regime_result:
        regime_type = regime_result.get("regime", "INDEFINIDO")
        regime_label = regime_result.get("label", "")
        regime_color = regime_result.get("color", UI['neutral'])
        regime_conf = regime_result.get("confidence", "")

        if regime_type != "INDEFINIDO":
            # Get trading recommendation
            regime_rec = st.session_state.regime_detector.get_trading_recommendation()
            regime_approach = regime_rec.get("approach", "") if regime_rec else ""
            regime_risk = regime_rec.get("risk_level", "") if regime_rec else ""

            st.markdown(f"""
            <div class="recb" style="border-left-color:{regime_color};background:{regime_color}08">
                <span class="recl" style="color:{regime_color}">REGIME: {regime_label}</span>
                <span class="recd">{regime_approach} | risk:{regime_risk} | conf:{regime_conf}</span>
            </div>
            """, unsafe_allow_html=True)

    # ==== 4d. PRICE REVERSAL BANNER ====
    if reversal_result and reversal_result.get("detected"):
        rv_type = reversal_result.get("type", "")
        rv_label = reversal_result.get("label", "")
        rv_color = reversal_result.get("color", UI['neutral'])
        rv_strength = reversal_result.get("strength", "")
        rv_dir = reversal_result.get("direction", "")
        rv_momenta = reversal_result.get("momenta", {})

        # Build momentum display
        mom_strs = []
        for period, val in rv_momenta.items():
            if val is not None:
                mom_strs.append(f"{period}p:{val:+.2f}%")
        mom_display = " ".join(mom_strs[:3])

        # Key label: "DIVERG PRECO ALTA" or "DIVERG PRECO BAIXA"
        if "ALTA" in rv_type:
            rv_short = "DIVERG PRECO ALTA"
        elif "BAIXA" in rv_type:
            rv_short = "DIVERG PRECO BAIXA"
        elif "REVERSAO" in rv_type and "ALTA" in rv_type:
            rv_short = "REV PRECO ALTA"
        elif "REVERSAO" in rv_type and "BAIXA" in rv_type:
            rv_short = "REV PRECO BAIXA"
        else:
            rv_short = rv_label

        st.markdown(f"""
        <div class="recb" style="border-left-color:{rv_color};background:{rv_color}12">
            <span class="recl" style="color:{rv_color}">{rv_short} {rv_strength}</span>
            <span class="recd">{mom_display}</span>
        </div>
        """, unsafe_allow_html=True)

    # ==== 5. SECTOR GRID (4 colunas!) ====
    st.markdown('<div class="sech">SETORES <span class="secr">5m / 15m / dia</span></div>', unsafe_allow_html=True)

    if sd:
        shtml = '<div class="sgrid">'
        for sn, sdata in sd.items():
            sc3 = sdata["color"]
            ss = sdata.get("sector_score", 0)
            ssc2 = UI['positive'] if ss > 0 else UI['negative'] if ss < 0 else UI['neutral']

            ahtml = ""
            for an, adata in sdata["assets"].items():
                dn = adata.get("display_name", an)
                cd = adata.get("change_pct")
                c5 = adata.get("change_5m")
                c15 = adata.get("change_15m")
                ahtml += f"""<div class="sar">
                    <span class="san">{dn}</span>
                    <span class="sv5 {vc(c5)}">{vs(c5) if c5 is not None else '---'}</span>
                    <span class="sv5 {vc(c15)}">{vs(c15) if c15 is not None else '---'}</span>
                    <span class="svd {vc(cd)}">{vs(cd) if cd is not None else '---'}</span>
                </div>"""

            shtml += f"""<div class="sblk" style="border-left:2px solid {sc3}30">
                <div class="shdr"><span class="snm" style="color:{sc3}">{sdata['icon']} {sn}</span><span class="ssc" style="color:{ssc2}">{ss:+.0f}</span></div>
                {ahtml}
            </div>"""
        shtml += '</div>'
        st.markdown(shtml, unsafe_allow_html=True)

        # Feeling
        feeling = st.session_state.sector_manager.get_market_feeling(sd)
        fc = UI['positive'] if feeling['direction'] > 10 else UI['negative'] if feeling['direction'] < -10 else UI['neutral']
        st.markdown(f"""
        <div class="fbar">
            <span class="fbl">FEELING</span>
            <span class="fbv" style="color:{fc}">{feeling['feeling']}</span>
            <span class="fbd">({feeling['direction']:+.0f})</span>
            <span class="fbd" style="flex:1;text-align:right">altas:{feeling['bullish_sectors']} baixas:{feeling['bearish_sectors']}/{feeling['total_sectors']}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="padding:2px;color:{UI["text_muted"]};font-size:7px;text-align:center">Carregando setores...</div>', unsafe_allow_html=True)

    # ==== 6. DIVERGENCIA (inline) ====
    dt = div.get("type", "INDEFINIDO") if div else "INDEFINIDO"
    if dt not in ("INDEFINIDO", "NEUTRO"):
        dc = div.get("color", UI['neutral'])
        dl = div.get("label", "")
        dd = div.get("description", "")[:70]
        st.markdown(f"""<div class="recb" style="border-left-color:{dc};background:{dc}08">
            <span class="recl" style="color:{dc}">{div.get('icon','')} {dl}</span><span class="recd">{dd}</span>
        </div>""", unsafe_allow_html=True)

    # ==== 7 & 8. LEVELS + FILTERS (2 colunas) ====
    st.markdown('<div class="sech">REGIOES INDICE <span class="secr">S/R</span></div>', unsafe_allow_html=True)

    left_html = ""
    right_html = ""

    # LEFT: Key Levels
    if lr and lr.get("available"):
        lvs = lr.get("levels", {})
        cp = lr.get("current_price")
        lt = {"R3":("res",UI['level_resistance']),"R2":("res",UI['level_resistance']),"R1":("res",UI['level_resistance']),
              "PIVOT":("pvt",UI['level_pivot']),"S1":("sup",UI['level_support']),"S2":("sup",UI['level_support']),"S3":("sup",UI['level_support'])}
        for ln in ["R3","R2","R1","PIVOT","S1","S2","S3"]:
            if ln not in lvs: continue
            lv = lvs[ln]
            lty, lc = lt.get(ln, ("neu", UI['neutral']))
            ds = ""
            if cp:
                d = lv - cp
                dp = (d/cp)*100
                ds = f"{d:+,.0f} ({dp:+.1f}%)"
            left_html += f"""<div class="lrow"><div class="ldot" style="background:{lc}"></div>
                <span class="lnm" style="color:{lc}">{ln}</span>
                <span class="lpr" style="color:{lc}">{lv:,.0f}</span>
                <span class="ldi">{ds}</span></div>"""
            if ln == "R1" and cp:
                left_html += f"""<div class="lcur"><span class="lcul">WIN {cp:,.0f}</span></div>"""
    else:
        msg = lr.get("message", "Aguardando dados") if lr else "Aguardando"
        left_html = f'<div style="padding:2px;color:{UI["text_muted"]};font-size:6px;text-align:center">{msg}</div>'

    # RIGHT: Filters with Confluence
    # Score zona
    sz = abs(score) < 4
    szc = "wrn" if sz else "pos"
    szi = "&#9888;" if sz else "&#10003;"

    # Estabilidade
    ct = "Ok"
    ctc = "pos"
    if len(sh) >= 4:
        rs = [h["score"] for h in sh[-4:]]
        sd2 = all(s > 0 for s in rs) or all(s < 0 for s in rs)
        if sd2: ct = "Confirmado"; ctc = "pos"
        else: ct = "Instavel"; ctc = "wrn"

    # Acel
    at = "estavel"; atc = "neu"
    if ac > 5: at = "acel alta"; atc = "pos"
    elif ac < -5: at = "acel baixa"; atc = "neg"

    # Dolar
    ud = "subindo" if (ad.get("DXY",{}).get("change_pct") or 0) > 0 else "caindo" if (ad.get("DXY",{}).get("change_pct") or 0) < 0 else "plano"
    uc2 = "neg" if ud == "subindo" and score > 0 else "pos" if ud == "caindo" and score > 0 else "neu"

    # Cesta
    vch = ad.get("VALE_ADR",{}).get("change_pct") or 0
    pch = ad.get("PETR_ADR",{}).get("change_pct") or 0
    cb = "positivas" if (vch+pch) > 0.5 else "negativas" if (vch+pch) < -0.5 else "neutras"
    cc2 = vc(1 if cb == "positivas" else -1 if cb == "negativas" else 0)

    # Divergencia
    dok = dt not in ("DIVERGENCIA_ALTA", "DIVERGENCIA_BAIXA")
    dvt = "Ok" if dok else "DIVERG"
    dvc = "pos" if dok else "wrn"

    # Recovery
    rvt = "Sim" if recovery and recovery.get("detected") else "---"
    rvc = "pos" if recovery and recovery.get("detected") else "neu"

    filters = [
        (szi, "Score zona", f"{score:+.1f}", szc),
        ("&#10003;", "Estab", ct, ctc),
        ("&#9670;", "Acel", at, atc),
        ("&#9670;", "Diverg", dvt, dvc),
        ("$", f"USD {ud}", f"{ad.get('DXY',{}).get('change_pct',0):+.2f}%", uc2),
        ("&#9679;", "V+P", cb, cc2),
        ("&#8634;", "Recup", rvt, rvc),
    ]

    # v5.0: Confluence filter results from SignalManager
    filter_details = filtered_signal.get("filter_details", {})
    confluence_count = filtered_signal.get("confluence_count", 0)
    min_confluence = SIGNAL_FILTER_CONFIG.get("min_confluence_filters", 3)

    # Add confluence filter indicators
    conf_filters = [
        ("score_zone", "ScZone"),
        ("delta_direction", "Delta"),
        ("momentum_confirm", "MomCfm"),
        ("not_in_divergence", "NoDiv"),
        ("recovery_confirmed", "Recup"),
    ]
    for fkey, flabel in conf_filters:
        fd = filter_details.get(fkey, {})
        f_passed = fd.get("passed", False) if fd else False
        fi = "&#10003;" if f_passed else "&#10007;"
        fc2 = "pos" if f_passed else "wrn"
        filters.append((fi, flabel, f"{confluence_count}/{min_confluence}" if fkey == conf_filters[0][0] else "", fc2))

    for fi, ft, fv, fc2 in filters:
        right_html += f"""<div class="frow"><span class="fico {fc2}">{fi}</span><span class="ftxt">{ft}</span><span class="fval {fc2}">{fv}</span></div>"""

    st.markdown(f"""
    <div class="twocol">
        <div style="background:{UI['bg_secondary']};padding:2px 3px">{left_html}</div>
        <div style="background:{UI['bg_secondary']};padding:2px 3px">
            <div class="sech" style="margin-bottom:1px">FILTROS <span class="secr">conf {confluence_count}/{min_confluence}</span></div>
            {right_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ==== 9. SIGNAL LOG (compacto) ====
    slog = st.session_state.signal_log
    st.markdown(f'<div class="sech">LOG ({len(slog)}) <span class="secr">sinais recentes</span></div>', unsafe_allow_html=True)
    if slog:
        lr2 = ""
        for s in slog[-4:][::-1]:
            dc2 = "pos" if "COMPRA" in s["direction"] else "neg" if "VENDA" in s["direction"] else "wrn"
            if "RECUPERACAO" in s["direction"]: dc2 = "pos"
            filtered_tag = ""
            fs2 = s.get("filtered", "")
            if fs2 and fs2 != s.get("direction", ""):
                filtered_tag = f' <span style="font-size:5px;color:#FF9800">&rarr;{fs2}</span>'
            lr2 += f"""<tr><td>{s['time']}</td><td class="{dc2}">{s['direction']}{filtered_tag}</td><td>{s['score']:+.0f}</td><td>{s['delta']:+.0f}</td><td>{s['confidence']}</td></tr>"""
        st.markdown(f"""<table class="ltbl"><thead><tr><th>Hora</th><th>Dir</th><th>Sc</th><th>Dlt</th><th>Conf</th></tr></thead><tbody>{lr2}</tbody></table>""", unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="padding:1px;color:{UI["text_muted"]};font-size:6px;text-align:center">Nenhum sinal</div>', unsafe_allow_html=True)

    # ==== 9b. PERFORMANCE STATS (v5.0 compact strip) ====
    if perf_stats and perf_stats.get("total_signals", 0) > 0:
        wr = perf_stats.get("win_rate", 0)
        payoff = perf_stats.get("payoff_ratio", 0)
        pending = perf_stats.get("pending_count", 0)
        total = perf_stats.get("total_signals", 0)
        wins = perf_stats.get("total_wins", 0)
        losses = perf_stats.get("total_losses", 0)
        wr_color = UI['positive'] if wr >= 50 else UI['warning'] if wr >= 30 else UI['negative']
        payoff_color = UI['positive'] if payoff >= 1.5 else UI['warning'] if payoff >= 1.0 else UI['negative']
        pending_color = UI['warning'] if pending > 5 else UI['text_muted']

        st.markdown(f"""
        <div class="mstrip" style="border-top:1px solid {UI['border_color']}">
            <div class="mc"><div class="mv" style="color:{wr_color}">{wr:.0f}%</div><div class="ml">WinRate</div></div>
            <div class="mc"><div class="mv" style="color:{payoff_color}">{payoff:.1f}x</div><div class="ml">Payoff</div></div>
            <div class="mc"><div class="mv" style="color:{pending_color}">{pending}</div><div class="ml">Pending</div></div>
            <div class="mc"><div class="mv" style="color:{UI['text_muted']}">{wins}W/{losses}L</div><div class="ml">Total {total}</div></div>
        </div>
        """, unsafe_allow_html=True)

    # ==== 10. CHART (mini) ====
    if len(sh) >= 2:
        st.markdown('<div class="sech">SCORE</div>', unsafe_allow_html=True)
        ts = [h["timestamp"] for h in sh]
        ss = [h["score"] for h in sh]
        ds2 = [h.get("delta", 0) for h in sh]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ts, y=ss, mode='lines', line=dict(color=UI['accent'], width=1.5, shape='spline'),
                                  fill='tozeroy', fillcolor=f"rgba(79,195,247,0.05)"))
        # Add EMA line if available
        smoother = st.session_state.get("score_smoother")
        if smoother and smoother._history:
            ema_history = smoother.get_history(last_n=len(sh))
            if ema_history:
                ema_ts = [e["timestamp"] for e in ema_history]
                ema_vals = [e["ema"] for e in ema_history]
                fig.add_trace(go.Scatter(x=ema_ts, y=ema_vals, mode='lines',
                                          line=dict(color='#FF9800', width=1, dash='dot'),
                                          name='EMA'))
        if any(d != 0 for d in ds2):
            dc3 = [UI['positive'] if d >= 0 else UI['negative'] for d in ds2]
            fig.add_trace(go.Bar(x=ts, y=ds2, marker_color=dc3, marker_line_width=0, opacity=0.3, yaxis='y2'))
        for y, c in [(60, f"{UI['positive']}25"),(-60,f"{UI['negative']}25")]:
            fig.add_hline(y=y, line_dash="dash", line_color=c, line_width=1)
        fig.add_hline(y=0, line_color="#ffffff08", line_width=0.5)
        fig.update_layout(height=70, margin=dict(l=20,r=5,t=1,b=8),
                          yaxis=dict(range=[-100,100],tickfont=dict(size=5,color=UI['text_muted']),gridcolor=UI['bg_tertiary'],zeroline=False),
                          yaxis2=dict(range=[-30,30],overlaying='y',side='right',tickfont=dict(size=4,color=UI['text_muted']),showgrid=False),
                          xaxis=dict(tickfont=dict(size=4,color=UI['text_muted']),gridcolor=UI['bg_secondary']),
                          template="plotly_dark",paper_bgcolor=UI['bg_primary'],plot_bgcolor=UI['bg_primary'],showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ==== CONTROLS ====
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("Atualizar", use_container_width=True):
            with st.spinner("..."): refresh_data()
    with c2:
        if st.button("MT5", use_container_width=True):
            dm = st.session_state.data_manager
            s2, m2 = dm.connect_mt5()
            st.session_state.mt5_status = {"success": s2, "message": m2}
    with c3:
        interval = st.selectbox("Sec", [15, 30, 60], index=1, label_visibility="collapsed")
        st.session_state.interval = interval

    rs2 = st.session_state.interval
    contract_label = st.session_state.get("active_win_contract", "---")
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;padding:1px 3px;background:{UI['bg_secondary']};border-top:1px solid {UI['border_color']};font-size:6px;color:{UI['text_muted']};font-family:{UI['font_family_data']}">
        <span>auto {rs2}s | #{st.session_state.refresh_count} | {contract_label}</span>
        <span>v5.0</span>
    </div>
    <script>setTimeout(function(){{window.location.reload();}},{rs2*1000});</script>
    """, unsafe_allow_html=True)


with tab_analysis:
    render_analysis_tab()
