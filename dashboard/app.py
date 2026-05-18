"""
Dashboard Profissional - Macro Scoring WIN v12.0
=================================================
COMPLETE REWRITE - Robust, never crashes.

Rules:
- NEVER st.stop() - causes blank screens
- ALL variables initialized with safe defaults before use
- Every function call wrapped in try/except
- Dashboard shows SOMETHING even when data fetching fails
- Auto-refresh via time-based st.rerun()
- All state in st.session_state with safe defaults

Para rodar: streamlit run dashboard/app.py
"""

import sys, os, time, traceback, logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ============ PATH RESOLUTION ============
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_APP_DIR)
for _p in [_PROJECT_ROOT, os.getcwd(), _APP_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
_walk_dir = _APP_DIR
for _ in range(3):
    if os.path.isfile(os.path.join(_walk_dir, 'config.py')):
        if _walk_dir not in sys.path:
            sys.path.insert(0, _walk_dir)
        break
    _walk_dir = os.path.dirname(_walk_dir)

import streamlit as st

# ============ SAFE IMPORTS ============
_import_errors = []

def _safe_import(module_path, names, fallback_values=None):
    result = {}
    fb = fallback_values or {}
    try:
        mod = __import__(module_path, fromlist=names)
        for name in names:
            val = getattr(mod, name, fb.get(name))
            if val is not None:
                result[name] = val
    except Exception as e:
        _import_errors.append(f"{module_path}: {e}")
        logger.error(f"Import error from {module_path}: {e}")
        for name in names:
            val = fb.get(name)
            if val is not None:
                result[name] = val
    return result

# Config
_cfg = _safe_import('config', [
    'MT5_CONFIG', 'DUAL_SOURCE_ASSETS', 'YF_SYMBOLS', 'MACRO_WEIGHTS',
    'SIGNAL_CONFIG', 'CATEGORIES', 'DASHBOARD_CONFIG', 'LOG_CONFIG',
    'WIN_TRACKING', 'DIVERGENCE_CONFIG', 'UI_CONFIG',
    'SECTOR_GROUPS', 'MULTI_TIMEFRAME_CONFIG', 'KEY_LEVELS_CONFIG',
    'SCORE_SMOOTHER_CONFIG', 'PRICE_REVERSAL_CONFIG', 'ALERT_CONFIG',
    'SIGNAL_FILTER_CONFIG', 'PERFORMANCE_CONFIG', 'REGIME_CONFIG',
    'WIN_CONTRACT_CONFIG', 'MT5_SYMBOLS',
    'CONTEXT_CLASSIFIER_CONFIG', 'STRUCTURAL_CONTEXT_CONFIG',
    'DYNAMIC_WEIGHTS_CONFIG', 'COMPRESSION_DETECTOR_CONFIG',
    'CONFIDENCE_SCORE_CONFIG', 'CALENDAR_EVENTS_CONFIG',
    'ENTRY_TRIGGERS_CONFIG', 'ENHANCED_LOG_CONFIG', 'CORRELATION_VALIDATOR_CONFIG',
])

# Fallback direct import
if not _cfg or all(v is None for v in _cfg.values()):
    try:
        import importlib
        _config_mod = importlib.import_module('config')
        for _name in _cfg:
            val = getattr(_config_mod, _name, None)
            if val is not None:
                _cfg[_name] = val
    except Exception as e2:
        logger.error(f"Fallback config import failed: {e2}")

# Unpack config with safe defaults
_UI_DEFAULTS = {
    "panel_width": 580, "panel_padding": 6,
    "font_family_data": "'Consolas', monospace",
    "font_family_ui": "'Segoe UI', sans-serif",
    "score_font_size": 36, "score_glow": True,
    "bg_primary": "#080c12", "bg_secondary": "#0d1420",
    "bg_tertiary": "#111a28", "bg_sector": "#0a1018",
    "border_color": "#1a2535", "border_light": "#243040",
    "text_primary": "#d0d8e0", "text_secondary": "#6b7d8e",
    "text_muted": "#3a4a5a", "accent": "#4fc3f7",
    "positive": "#00E676", "negative": "#FF1744",
    "warning": "#FFD600", "neutral": "#78909C",
    "level_resistance": "#FF5252", "level_support": "#69F0AE",
    "level_pivot": "#FFD740", "level_current": "#FFFFFF",
}

def _cfg_get(key, default=None):
    val = _cfg.get(key)
    return val if val is not None else default

MT5_CONFIG = _cfg_get('MT5_CONFIG', {})
DUAL_SOURCE_ASSETS = _cfg_get('DUAL_SOURCE_ASSETS', {})
YF_SYMBOLS = _cfg_get('YF_SYMBOLS', {})
MACRO_WEIGHTS = _cfg_get('MACRO_WEIGHTS', {})
SIGNAL_CONFIG = _cfg_get('SIGNAL_CONFIG', {})
CATEGORIES = _cfg_get('CATEGORIES', {})
DASHBOARD_CONFIG = _cfg_get('DASHBOARD_CONFIG', {})
LOG_CONFIG = _cfg_get('LOG_CONFIG', {})
WIN_TRACKING = _cfg_get('WIN_TRACKING', {})
DIVERGENCE_CONFIG = _cfg_get('DIVERGENCE_CONFIG', {})
UI_CONFIG = _cfg_get('UI_CONFIG', _UI_DEFAULTS)
KEY_LEVELS_CONFIG = _cfg_get('KEY_LEVELS_CONFIG', {})
SCORE_SMOOTHER_CONFIG = _cfg_get('SCORE_SMOOTHER_CONFIG', {})
PRICE_REVERSAL_CONFIG = _cfg_get('PRICE_REVERSAL_CONFIG', {})
ALERT_CONFIG = _cfg_get('ALERT_CONFIG', {})
SIGNAL_FILTER_CONFIG = _cfg_get('SIGNAL_FILTER_CONFIG', {})
PERFORMANCE_CONFIG = _cfg_get('PERFORMANCE_CONFIG', {})
REGIME_CONFIG = _cfg_get('REGIME_CONFIG', {})
WIN_CONTRACT_CONFIG = _cfg_get('WIN_CONTRACT_CONFIG', {})
MT5_SYMBOLS = _cfg_get('MT5_SYMBOLS', {})
CONTEXT_CLASSIFIER_CONFIG = _cfg_get('CONTEXT_CLASSIFIER_CONFIG', {})
STRUCTURAL_CONTEXT_CONFIG = _cfg_get('STRUCTURAL_CONTEXT_CONFIG', {})
DYNAMIC_WEIGHTS_CONFIG = _cfg_get('DYNAMIC_WEIGHTS_CONFIG', {})
COMPRESSION_DETECTOR_CONFIG = _cfg_get('COMPRESSION_DETECTOR_CONFIG', {})
CONFIDENCE_SCORE_CONFIG = _cfg_get('CONFIDENCE_SCORE_CONFIG', {})
CALENDAR_EVENTS_CONFIG = _cfg_get('CALENDAR_EVENTS_CONFIG', {})
SECTOR_GROUPS = _cfg_get('SECTOR_GROUPS', {})
MULTI_TIMEFRAME_CONFIG = _cfg_get('MULTI_TIMEFRAME_CONFIG', {})
ENTRY_TRIGGERS_CONFIG = _cfg_get('ENTRY_TRIGGERS_CONFIG', {})
ENHANCED_LOG_CONFIG = _cfg_get('ENHANCED_LOG_CONFIG', {})
CORRELATION_VALIDATOR_CONFIG = _cfg_get('CORRELATION_VALIDATOR_CONFIG', {})

UI = UI_CONFIG if isinstance(UI_CONFIG, dict) else _UI_DEFAULTS

# Data sources
_dm = _safe_import('data_sources.data_manager', ['DataManager']); DataManager = _dm.get('DataManager')
_sd = _safe_import('data_sources.sector_data', ['SectorDataManager']); SectorDataManager = _sd.get('SectorDataManager')

# Scoring modules
_ms = _safe_import('scoring.macro_score', ['MacroScorer']); MacroScorer = _ms.get('MacroScorer')
_da = _safe_import('scoring.delta', ['DeltaAnalyzer']); DeltaAnalyzer = _da.get('DeltaAnalyzer')
_dd = _safe_import('scoring.divergence', ['DivergenceDetector']); DivergenceDetector = _dd.get('DivergenceDetector')
_kl = _safe_import('scoring.key_levels', ['KeyLevelsCalculator']); KeyLevelsCalculator = _kl.get('KeyLevelsCalculator')
_ss = _safe_import('scoring.score_smoother', ['ScoreSmoother']); ScoreSmoother = _ss.get('ScoreSmoother')
_pr = _safe_import('scoring.price_reversal', ['PriceReversalDetector']); PriceReversalDetector = _pr.get('PriceReversalDetector')
_rd = _safe_import('scoring.regime_detector', ['RegimeDetector']); RegimeDetector = _rd.get('RegimeDetector')
_sm = _safe_import('scoring.signal_manager', ['SignalManager']); SignalManager = _sm.get('SignalManager')
_pt = _safe_import('scoring.performance_tracker', ['PerformanceTracker']); PerformanceTracker = _pt.get('PerformanceTracker')
_cc = _safe_import('scoring.context_classifier', ['ContextClassifier']); ContextClassifier = _cc.get('ContextClassifier')
_sc = _safe_import('scoring.structural_context', ['StructuralContext']); StructuralContext = _sc.get('StructuralContext')
_dw = _safe_import('scoring.dynamic_weights', ['DynamicWeights']); DynamicWeights = _dw.get('DynamicWeights')
_cd = _safe_import('scoring.compression_detector', ['CompressionDetector']); CompressionDetector = _cd.get('CompressionDetector')
_cs = _safe_import('scoring.confidence_score', ['ConfidenceScore']); ConfidenceScore = _cs.get('ConfidenceScore')
_et = _safe_import('scoring.entry_triggers', ['EntryTriggers']); EntryTriggers = _et.get('EntryTriggers')

# Utils
_al = _safe_import('utils.alert_system', ['AlertSystem']); AlertSystem = _al.get('AlertSystem')
_ce = _safe_import('utils.calendar_events', ['CalendarEvents']); CalendarEvents = _ce.get('CalendarEvents')
_hl = _safe_import('utils.helpers', [
    'format_change', 'format_price', 'get_change_color', 'get_score_color',
    'get_active_win_contract', 'get_active_wdo_contract',
])
format_change = _hl.get('format_change', lambda v, d=2: f"{v:+.{d}f}%" if v is not None else "---")
format_price = _hl.get('format_price', lambda v, d=2: f"{v:,.{d}f}" if v is not None else "---")
get_change_color = _hl.get('get_change_color', lambda v: "#9E9E9E")
get_score_color = _hl.get('get_score_color', lambda s: "#FFC107")
get_active_win_contract = _hl.get('get_active_win_contract', lambda **kw: "WINK25")
get_active_wdo_contract = _hl.get('get_active_wdo_contract', lambda **kw: "WDOK25")
_ml = _safe_import('utils.macro_logger', ['MacroLogger']); MacroLogger = _ml.get('MacroLogger')
_at = _safe_import('dashboard.analysis_tab', ['render_analysis_tab']); render_analysis_tab = _at.get('render_analysis_tab')

CRITICAL_FAILURES = []
if DataManager is None: CRITICAL_FAILURES.append("DataManager")
if MacroScorer is None: CRITICAL_FAILURES.append("MacroScorer")

# ============ PAGE CONFIG ============
st.set_page_config(page_title="Macro WIN v12.0", page_icon="W", layout="centered",
                   initial_sidebar_state="collapsed")

# ============ SAFE FORMAT HELPERS ============
def sf(val, fmt="+.1f", default="---"):
    if val is None: return default
    try: return f"{val:{fmt}}"
    except (TypeError, ValueError): return default

def sfd(d, key, fmt="+.1f", default="---"):
    if not isinstance(d, dict): return default
    return sf(d.get(key), fmt, default)

def vc(val):
    if val is None: return "neu"
    try: return "pos" if val > 0 else "neg" if val < 0 else "neu"
    except (TypeError, ValueError): return "neu"

def vs(val):
    if val is None: return "---"
    try: return f"{val:+.2f}%"
    except (TypeError, ValueError): return "---"


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

    .err-bar{{background:#FF174418;border:1px solid #FF174440;border-radius:3px;padding:4px 8px;margin:2px 0;font-size:8px;color:#FF8A80;font-family:{UI['font_family_data']}}}
    .alert-bar{{display:flex;align-items:center;gap:4px;padding:2px 6px;border-radius:2px;border:1px solid;margin:1px 0;font-size:7px;font-family:{UI['font_family_data']};animation:alertPulse 1.5s ease-in-out}}
    @keyframes alertPulse {{0%{{opacity:0.5}}100%{{opacity:1}}}}
    .alert-icon{{font-size:9px}}
    .alert-msg{{color:{UI['text_secondary']};font-size:6px;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .alert-type{{font-weight:800;letter-spacing:0.5px}}

    .sbar{{display:flex;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']};font-family:{UI['font_family_data']};font-size:8px}}
    .sc{{padding:2px 5px;border-right:1px solid {UI['border_color']};display:flex;align-items:center;gap:2px;white-space:nowrap}}
    .sc:last-child{{border-right:none}}
    .sl{{color:{UI['text_muted']};font-size:6px;text-transform:uppercase}}
    .sv{{font-weight:700;font-size:8px}}

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

    .mstrip{{display:flex;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']}}}
    .mc{{flex:1;text-align:center;padding:1px 0;border-right:1px solid {UI['border_color']}}}
    .mc:last-child{{border-right:none}}
    .mv{{font-size:11px;font-weight:800;font-family:{UI['font_family_data']};line-height:1}}
    .ml{{font-size:6px;color:{UI['text_muted']};text-transform:uppercase;letter-spacing:.5px}}

    .sigb{{text-align:center;padding:2px;border-radius:2px;border:1px solid;margin:1px 0}}
    .sigt{{font-size:11px;font-weight:800;letter-spacing:1px;font-family:{UI['font_family_data']}}}
    .siga{{font-size:7px;color:{UI['text_secondary']}}}

    .ctxb{{display:flex;align-items:center;gap:4px;padding:2px 4px;border-left:3px solid;font-size:7px;margin:1px 0;background:{UI['bg_secondary']}}}
    .ctxl{{font-weight:800;font-family:{UI['font_family_data']};font-size:8px}}
    .ctxd{{color:{UI['text_secondary']};font-size:6px;flex:1}}

    .recb{{display:flex;align-items:center;gap:4px;padding:2px 4px;border-left:3px solid;font-size:7px;margin:1px 0;background:{UI['bg_secondary']}}}
    .recl{{font-weight:800;font-family:{UI['font_family_data']};font-size:8px}}
    .recd{{color:{UI['text_secondary']};font-size:6px;flex:1}}

    .sgrid{{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:1px;padding:1px}}
    .sblk{{background:{UI['bg_sector']};border:1px solid {UI['border_color']};border-radius:1px;padding:2px 3px}}
    .shdr{{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid {UI['border_color']}40;padding-bottom:1px;margin-bottom:1px}}
    .snm{{font-size:6px;font-weight:700;font-family:{UI['font_family_data']};letter-spacing:.5px}}
    .ssc{{font-size:9px;font-weight:900;font-family:{UI['font_family_data']}}}
    .sar{{display:flex;align-items:center;gap:2px;padding:0;font-size:7px;font-family:{UI['font_family_data']}}}
    .san{{min-width:32px;color:{UI['text_secondary']};font-size:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .sv5{{font-weight:600;min-width:30px;text-align:right;font-size:6px}}
    .svd{{font-weight:700;min-width:34px;text-align:right;font-size:7px}}

    .twocol{{display:grid;grid-template-columns:1fr 1fr;gap:1px;padding:1px}}
    .sech{{font-size:6px;font-weight:700;color:{UI['text_muted']};padding:1px 3px;letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid {UI['border_color']};font-family:{UI['font_family_data']};display:flex;justify-content:space-between}}
    .secr{{font-size:6px;color:{UI['text_secondary']}}}

    .lrow{{display:flex;align-items:center;gap:3px;padding:0;font-family:{UI['font_family_data']};border-bottom:1px solid {UI['border_color']}15}}
    .ldot{{width:4px;height:4px;border-radius:50%;min-width:4px}}
    .lnm{{min-width:28px;font-size:7px;font-weight:700;text-align:center}}
    .lpr{{font-size:8px;font-weight:700;min-width:52px;text-align:right}}
    .ldi{{font-size:6px;color:{UI['text_muted']};flex:1;text-align:right}}
    .lcur{{width:100%;height:1px;background:{UI['level_current']};margin:0;position:relative}}
    .lcul{{position:absolute;right:0;top:-7px;font-size:6px;font-weight:900;color:{UI['level_current']};font-family:{UI['font_family_data']}}}

    .frow{{display:flex;align-items:center;gap:2px;padding:0;font-size:7px;border-bottom:1px solid {UI['bg_secondary']}1}}
    .fico{{font-size:7px;min-width:10px;text-align:center}}
    .ftxt{{color:{UI['text_secondary']};font-size:6px}}
    .fval{{font-weight:700;font-family:{UI['font_family_data']};font-size:7px;margin-left:auto}}

    .fbar{{display:flex;align-items:center;gap:3px;padding:1px 4px;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']};font-size:7px}}
    .fbl{{color:{UI['text_muted']};font-size:6px;text-transform:uppercase;letter-spacing:.5px}}
    .fbv{{font-weight:900;font-size:9px;font-family:{UI['font_family_data']}}}
    .fbd{{color:{UI['text_secondary']};font-size:6px;font-family:{UI['font_family_data']}}}

    .struct-row{{display:flex;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']};font-family:{UI['font_family_data']};font-size:7px}}
    .struct-item{{padding:1px 4px;border-right:1px solid {UI['border_color']};display:flex;align-items:center;gap:2px}}
    .struct-item:last-child{{border-right:none}}
    .struct-lbl{{color:{UI['text_muted']};font-size:6px}}
    .struct-val{{font-weight:700;font-size:7px}}

    .ltbl{{width:100%;font-size:6px;font-family:{UI['font_family_data']};border-collapse:collapse}}
    .ltbl th{{text-align:left;padding:1px 2px;color:{UI['text_muted']};border-bottom:1px solid {UI['border_color']}}}
    .ltbl td{{padding:1px 2px;border-bottom:1px solid {UI['border_color']}30}}

    .pos{{color:{UI['positive']}}}.neg{{color:{UI['negative']}}}.neu{{color:{UI['neutral']}}}.wrn{{color:{UI['warning']}}}
    .src-m{{font-size:5px;background:#1b5e2022;color:#4CAF50;padding:0 1px;border-radius:1px}}
    .src-y{{font-size:5px;background:#0d47a122;color:#42A5F5;padding:0 1px;border-radius:1px}}

    .stButton>button{{background:{UI['bg_tertiary']};color:{UI['text_secondary']};border:1px solid {UI['border_light']};font-size:8px;font-weight:600;border-radius:2px;padding:1px 4px;font-family:{UI['font_family_ui']}}}
    .stSelectbox div[data-baseweb="select"]{{background:{UI['bg_tertiary']};border:1px solid {UI['border_light']};border-radius:2px;min-height:1.1rem;font-size:8px}}
    .stTabs [data-baseweb="tab-list"]{{gap:0;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']}}}
    .stTabs [data-baseweb="tab"]{{height:1.2rem;font-size:7px;font-weight:700;letter-spacing:1px;color:{UI['text_muted']};padding:0 .4rem;font-family:{UI['font_family_data']}}}
    .stTabs [aria-selected="true"]{{color:{UI['accent']}!important;border-bottom:2px solid {UI['accent']}!important;background:{UI['bg_primary']}}}
    .stTabs [data-baseweb="tab-panel"]{{padding:0}}

    .err-display{{background:#FF174418;border:1px solid #FF174440;border-radius:3px;padding:8px;margin:4px 0;font-family:{UI['font_family_data']};font-size:9px;color:#FF8A80}}
    .err-display .err-title{{font-weight:800;font-size:10px;color:#FF5252;margin-bottom:4px}}
    .err-display .err-trace{{font-size:7px;color:#FF8A80;white-space:pre-wrap;word-break:break-all}}

    .dicurve{{display:flex;align-items:flex-end;gap:2px;padding:3px 4px;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']};height:38px}}
    .dibar{{display:flex;flex-direction:column;align-items:center;flex:1;gap:0}}
    .dibar-fill{{width:100%;border-radius:1px 1px 0 0;min-height:2px;transition:height 0.3s}}
    .dibar-label{{font-size:5px;color:{UI['text_muted']};font-family:{UI['font_family_data']};letter-spacing:.5px}}
    .dibar-val{{font-size:6px;font-weight:700;font-family:{UI['font_family_data']};margin-top:1px}}
    .di-spread{{display:flex;flex-direction:column;align-items:center;justify-content:center;min-width:50px;gap:1px}}
    .di-spread-label{{font-size:5px;color:{UI['text_muted']};text-transform:uppercase;letter-spacing:.5px}}
    .di-spread-val{{font-size:9px;font-weight:900;font-family:{UI['font_family_data']}}}
    .di-spread-shape{{font-size:5px;font-weight:700;letter-spacing:.5px}}

    .trig-grid{{display:grid;grid-template-columns:1fr 1fr;gap:1px;padding:1px}}
    .trig-item{{display:flex;align-items:center;gap:3px;padding:2px 3px;background:{UI['bg_sector']};border:1px solid {UI['border_color']};border-radius:1px;font-size:6px;font-family:{UI['font_family_data']}}}
    .trig-dot{{width:5px;height:5px;border-radius:50%;min-width:5px}}
    .trig-name{{color:{UI['text_secondary']};flex:1;font-size:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .trig-strength{{font-weight:800;font-size:7px;min-width:12px;text-align:right}}
    .trig-dir{{font-size:5px;font-weight:700;min-width:20px;text-align:right}}
    .trig-score-bar{{display:flex;align-items:center;gap:4px;padding:3px 4px;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']}}}
    .trig-pips{{display:flex;gap:1px}}
    .trig-pip{{width:6px;height:6px;border-radius:1px;background:{UI['border_color']}}}
    .trig-pip.on{{background:{UI['positive']}}}
    .trig-pip.blocked{{background:{UI['negative']}}}

    .mktphase{{display:flex;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']};font-family:{UI['font_family_data']};font-size:7px}}
    .phase-item{{flex:1;text-align:center;padding:2px 0;border-right:1px solid {UI['border_color']};opacity:0.3}}
    .phase-item.active{{opacity:1.0;font-weight:800}}
    .phase-item:last-child{{border-right:none}}
    .phase-label{{font-size:5px;color:{UI['text_muted']};text-transform:uppercase;letter-spacing:.5px}}
    .phase-time{{font-size:7px;font-weight:700}}

    .flowbar{{display:flex;align-items:center;gap:4px;padding:2px 4px;background:{UI['bg_secondary']};border-bottom:1px solid {UI['border_color']};font-size:7px}}
    .flow-icon{{font-size:9px}}
    .flow-label{{color:{UI['text_muted']};font-size:5px;text-transform:uppercase;letter-spacing:.5px}}
    .flow-val{{font-weight:900;font-family:{UI['font_family_data']};font-size:8px}}
    .flow-bar{{flex:1;height:4px;background:{UI['border_color']};border-radius:2px;position:relative;overflow:hidden}}
    .flow-fill{{position:absolute;top:0;height:100%;border-radius:2px;transition:width 0.3s}}

    .sparkline{{display:flex;align-items:flex-end;gap:0;height:16px;min-width:80px}}
    .spark-bar{{width:3px;min-height:1px;border-radius:0.5px}}
</style>
""", unsafe_allow_html=True)

# Show import errors
if _import_errors:
    err_html = "<br>".join(_import_errors[:5])
    st.markdown(f'<div class="err-bar">IMPORT WARNINGS: {err_html}</div>', unsafe_allow_html=True)


# ============ CONTRACT RESOLUTION ============
@st.cache_data(ttl=3600)
def _cached_resolve_win_contract(roll_days):
    try: return get_active_win_contract(roll_days_before=roll_days)
    except: return None

@st.cache_data(ttl=3600)
def _cached_resolve_wdo_contract(roll_days):
    try: return get_active_wdo_contract(roll_days_before=roll_days)
    except: return None

def resolve_win_contract():
    try:
        if WIN_TRACKING.get("mt5_symbol") == "AUTO" and WIN_CONTRACT_CONFIG.get("enabled", True):
            return _cached_resolve_win_contract(WIN_CONTRACT_CONFIG.get("roll_days_before", 3))
    except: pass
    return None

def resolve_wdo_contract():
    try:
        if MT5_SYMBOLS.get("WDO") == "AUTO" and WIN_CONTRACT_CONFIG.get("enabled", True):
            return _cached_resolve_wdo_contract(WIN_CONTRACT_CONFIG.get("roll_days_before", 3))
    except: pass
    return None


# ============ SESSION STATE INIT ============
_SESSION_DEFAULTS = {
    "data_manager": None,
    "scorer": None, "delta_analyzer": None, "divergence_detector": None,
    "key_levels": None, "sector_manager": None, "macro_logger": None,
    "score_smoother": None, "price_reversal": None, "regime_detector": None,
    "signal_manager": None, "performance_tracker": None, "alert_system": None,
    "context_classifier": None, "structural_context": None,
    "dynamic_weights": None, "compression_detector": None,
    "confidence_score": None, "calendar_events": None,
    "entry_triggers": None,
    "score_history": [], "signal_log": [], "last_data": {},
    "mt5_status": None, "refresh_count": 0, "interval": 30,
    "win_price": None, "win_change": None, "sectors_data": {},
    "score_result": {}, "delta_result": {}, "divergence_result": {},
    "levels_result": {}, "smoothed_result": {}, "reversal_result": {},
    "regime_result": {}, "filtered_signal": {}, "perf_stats": {},
    "alert_result": {}, "alert_html": "",
    "context_result": {}, "structural_result": {},
    "dynamic_weights_result": {}, "compression_result": {},
    "confidence_result": {}, "trigger_result": {}, "calendar_result": {},
    "active_win_contract": "---", "active_wdo_contract": "---",
    "last_refresh_time": 0,
}

def _ss(key, default=None):
    """Safe session_state get with default."""
    return st.session_state.get(key, default if default is not None else _SESSION_DEFAULTS.get(key))

def init_session_state():
    """Initialize ALL session state keys with safe defaults."""
    needs_init = any(k not in st.session_state for k in _SESSION_DEFAULTS)
    if not needs_init and st.session_state.get("data_manager") is None and DataManager is not None:
        needs_init = True
    if not needs_init:
        return

    for key, val in _SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val

    if DataManager is None:
        logger.error("DataManager not available - dashboard will show limited data")
        return

    try:
        wt = dict(WIN_TRACKING) if isinstance(WIN_TRACKING, dict) and WIN_TRACKING else {}
        if wt.get("mt5_symbol") == "AUTO":
            resolved = resolve_win_contract()
            if resolved:
                wt["mt5_symbol"] = resolved

        st.session_state.data_manager = DataManager(
            mt5_config=MT5_CONFIG, dual_source=DUAL_SOURCE_ASSETS,
            yf_only=YF_SYMBOLS, win_tracking=wt
        )
        st.session_state.scorer = MacroScorer(MACRO_WEIGHTS, SIGNAL_CONFIG) if MacroScorer else None
        st.session_state.delta_analyzer = DeltaAnalyzer(SIGNAL_CONFIG) if DeltaAnalyzer else None
        st.session_state.divergence_detector = DivergenceDetector(DIVERGENCE_CONFIG) if DivergenceDetector else None
        st.session_state.key_levels = KeyLevelsCalculator(KEY_LEVELS_CONFIG) if KeyLevelsCalculator else None
        st.session_state.sector_manager = SectorDataManager(SECTOR_GROUPS, MULTI_TIMEFRAME_CONFIG) if SectorDataManager and SECTOR_GROUPS else None
        st.session_state.macro_logger = MacroLogger(LOG_CONFIG) if MacroLogger else None
        st.session_state.score_smoother = ScoreSmoother(SCORE_SMOOTHER_CONFIG) if ScoreSmoother else None
        st.session_state.price_reversal = PriceReversalDetector(PRICE_REVERSAL_CONFIG) if PriceReversalDetector else None
        st.session_state.regime_detector = RegimeDetector(REGIME_CONFIG) if RegimeDetector else None
        st.session_state.signal_manager = SignalManager(SIGNAL_FILTER_CONFIG) if SignalManager else None
        st.session_state.performance_tracker = PerformanceTracker(PERFORMANCE_CONFIG) if PerformanceTracker else None
        st.session_state.alert_system = AlertSystem(ALERT_CONFIG) if AlertSystem else None
        st.session_state.context_classifier = ContextClassifier(CONTEXT_CLASSIFIER_CONFIG) if ContextClassifier else None
        st.session_state.structural_context = StructuralContext(STRUCTURAL_CONTEXT_CONFIG) if StructuralContext else None
        st.session_state.dynamic_weights = DynamicWeights(MACRO_WEIGHTS, DYNAMIC_WEIGHTS_CONFIG) if DynamicWeights else None
        st.session_state.compression_detector = CompressionDetector(COMPRESSION_DETECTOR_CONFIG) if CompressionDetector else None
        st.session_state.confidence_score = ConfidenceScore(CONFIDENCE_SCORE_CONFIG) if ConfidenceScore else None
        st.session_state.calendar_events = CalendarEvents(CALENDAR_EVENTS_CONFIG) if CalendarEvents else None
        st.session_state.entry_triggers = EntryTriggers(ENTRY_TRIGGERS_CONFIG) if EntryTriggers else None
        st.session_state.active_win_contract = resolve_win_contract() or "---"
        st.session_state.active_wdo_contract = resolve_wdo_contract() or "---"
    except Exception as e:
        logger.error(f"Init error: {e}\n{traceback.format_exc()}")

init_session_state()


# ============ REFRESH DATA ============
_EMPTY_SCORE = {
    "score": 0,
    "signal": {"type": "NEUTRO", "label": "AGUARDANDO", "confidence": "---", "action": "Sem dados", "color": "#78909C"},
    "category_scores": {}, "assets_available": 0, "assets_total": 23,
    "raw_score": 0, "total_weight_used": 0, "asset_signals": {},
    "missing_assets": [], "timestamp": datetime.now(),
}

_EMPTY_DELTA = {
    "delta": 0, "momentum": 0,
    "entry_signal": {"type": "NEUTRO", "label": "SEM SINAL", "confidence": "---", "action": "", "suggested_side": "FLAT"},
    "confluence": {"score_delta_aligned": False, "reversal_detected": False, "recovery_detected": False},
    "intraday_recovery": None, "intraday_reversal_down": None,
}

def refresh_data():
    """Refresh all data. NEVER crashes."""
    dm = _ss("data_manager")
    all_data = {}
    if dm is None:
        try:
            wt = dict(WIN_TRACKING) if isinstance(WIN_TRACKING, dict) and WIN_TRACKING else {}
            dm = DataManager(mt5_config=MT5_CONFIG, dual_source=DUAL_SOURCE_ASSETS,
                             yf_only=YF_SYMBOLS, win_tracking=wt)
            st.session_state.data_manager = dm
        except Exception as e:
            logger.error(f"DataManager reinit failed: {e}")
    try:
        if dm is not None: all_data = dm.get_all_data() or {}
    except Exception as e:
        logger.error(f"Data fetch error: {e}")
        all_data = {}
    st.session_state.last_data = all_data

    # Calendar
    try:
        cal = _ss("calendar_events")
        if cal:
            st.session_state.calendar_result = cal.get_event_summary() or {}
            dw = _ss("dynamic_weights")
            if dw: dw.set_calendar_multipliers(cal.get_weight_multipliers())
    except Exception as e: logger.warning(f"Calendar error: {e}")

    # Dynamic weights
    try:
        dw = _ss("dynamic_weights")
        if dw:
            for an, ad in all_data.items():
                if isinstance(ad, dict) and ad.get("change_pct") is not None: dw.update(an, ad["change_pct"])
            wd = all_data.get("WIN") or all_data.get("EWZ")
            if wd and wd.get("change_pct") is not None: dw.update_win(wd["change_pct"])
            st.session_state.dynamic_weights_result = dw.maybe_recalculate() or {}
    except Exception as e: logger.warning(f"DynamicWeights error: {e}")

    # Scoring
    scorer = _ss("scorer")
    score_result = _EMPTY_SCORE.copy()
    if scorer is None:
        st.session_state.score_result = score_result
        return score_result
    try:
        score_result = scorer.calculate_score(all_data) or _EMPTY_SCORE
        st.session_state.score_result = score_result
    except Exception as e:
        logger.error(f"Scoring error: {e}")
        score_result = _EMPTY_SCORE.copy()
        score_result["signal"] = {"type": "NEUTRO", "label": "ERRO", "confidence": "---", "action": f"Erro: {e}", "color": "#FF1744"}
        st.session_state.score_result = score_result
        return score_result

    score = score_result.get("score", 0) or 0
    category_scores = score_result.get("category_scores", {})

    # Delta
    delta_val = 0
    try:
        da = _ss("delta_analyzer")
        if da:
            da.update(score)
            dr = da.get_entry_signal(score_result) or _EMPTY_DELTA
            st.session_state.delta_result = dr
            delta_val = dr.get("delta", 0) or 0
    except Exception as e:
        logger.warning(f"Delta error: {e}")
        st.session_state.delta_result = _EMPTY_DELTA.copy()

    # WIN price + Divergence
    win_price = None
    win_change_pct = None
    try:
        wd = all_data.get("WIN") or all_data.get("EWZ")
        if wd and wd.get("current_price"):
            win_price = wd["current_price"]
            win_change_pct = wd.get("change_pct")
            st.session_state["win_price"] = win_price
            st.session_state["win_change"] = win_change_pct
    except: pass

    try:
        dd = _ss("divergence_detector")
        if dd:
            dd.update_score(score)
            if win_price: dd.update_win_price(win_price)
            st.session_state.divergence_result = dd.check_divergence() or {}
    except Exception as e: logger.warning(f"Divergence error: {e}")

    # Key Levels
    try:
        kl = _ss("key_levels")
        if kl:
            if st.session_state.get("win_price"): kl.update_win_data(current_price=st.session_state.get("win_price"))
            if all_data.get("EWZ"): kl.calculate_from_ewz(all_data.get("EWZ", {}), all_data.get("IBOV", {}))
            st.session_state.levels_result = kl.get_full_analysis(score) or {}
    except Exception as e: logger.warning(f"KeyLevels error: {e}")

    # Score Smoother
    try:
        ss = _ss("score_smoother")
        if ss:
            ss.add_score(score)
            st.session_state.smoothed_result = ss.get_both() or {}
    except Exception as e: logger.warning(f"Smoother error: {e}")

    # Price Reversal
    reversal_result = {}
    try:
        pr = _ss("price_reversal")
        if pr:
            if win_price is not None and win_change_pct is not None: pr.update_win_data(win_price, win_change_pct)
            pr.update_score(score, delta_val)
            reversal_result = pr.check_price_reversal() or {}
            st.session_state.reversal_result = reversal_result
    except Exception as e: logger.warning(f"PriceReversal error: {e}")

    # Regime
    regime_result = {}
    try:
        rd = _ss("regime_detector")
        if rd:
            rd.update(score, delta_val)
            regime_result = rd.detect_regime() or {}
            st.session_state.regime_result = regime_result
    except Exception as e: logger.warning(f"Regime error: {e}")

    # Signal Manager
    filtered_signal = {}
    try:
        sm = _ss("signal_manager")
        dr = _ss("delta_result", {})
        entry_type = dr.get("entry_signal", {}).get("type", "NEUTRO") if dr else "NEUTRO"
        if sm:
            filtered_signal = sm.process_signal(
                signal_type=entry_type, score=score, delta=delta_val,
                sector_data=category_scores, divergence=_ss("divergence_result", {}),
                recovery=dr.get("intraday_recovery") if dr else None,
            ) or {}
            st.session_state.filtered_signal = filtered_signal
    except Exception as e: logger.warning(f"SignalManager error: {e}")

    # Performance Tracker
    try:
        pt = _ss("performance_tracker")
        dr = _ss("delta_result", {})
        entry_type = dr.get("entry_signal", {}).get("type", "NEUTRO") if dr else "NEUTRO"
        if pt:
            if entry_type != "NEUTRO" and st.session_state.get("win_price"):
                pt.register_signal(signal_type=entry_type, score=score, delta=delta_val,
                    win_price=st.session_state.get("win_price"), timestamp=datetime.now(),
                    levels_result=st.session_state.get("levels_result", {}))
            if st.session_state.get("win_price"): pt.check_outcomes(st.session_state.get("win_price"))
            st.session_state.perf_stats = pt.get_statistics() or {}
    except Exception as e: logger.warning(f"PerfTracker error: {e}")

    # Compression
    compression_result = {}
    try:
        cd = _ss("compression_detector")
        if cd:
            cd.update_score(score)
            hist = _ss("score_history", [])
            if len(hist) >= 2:
                cd.update_atr(max(abs(score - hist[-1].get("score", score)), 0.1))
            compression_result = cd.detect(category_scores) or {}
            st.session_state.compression_result = compression_result
    except Exception as e: logger.warning(f"Compression error: {e}")

    # Confidence
    confidence_result = {}
    try:
        cs = _ss("confidence_score")
        if cs:
            cs.update(score)
            confidence_result = cs.calculate(
                assets_available=score_result.get("assets_available", 0),
                assets_total=score_result.get("assets_total", 23),
                regime_result=regime_result, divergence_result=_ss("divergence_result", {}),
                category_scores=category_scores) or {}
            st.session_state.confidence_result = confidence_result
    except Exception as e: logger.warning(f"Confidence error: {e}")

    # Context Classifier
    try:
        ctx = _ss("context_classifier")
        if ctx:
            st.session_state.context_result = ctx.classify(
                score=score, delta=delta_val, regime_result=regime_result,
                divergence_result=_ss("divergence_result", {}), reversal_result=reversal_result,
                filtered_signal=filtered_signal, compression_result=compression_result,
                confidence_result=confidence_result, category_scores=category_scores) or {}
    except Exception as e: logger.warning(f"ContextClassifier error: {e}")

    # Structural Context
    try:
        sc_mod = _ss("structural_context")
        if sc_mod and win_price is not None:
            wd = all_data.get("WIN") or all_data.get("EWZ") or {}
            sc_mod.update_candle(high=wd.get("current_price", win_price)*1.001,
                low=wd.get("current_price", win_price)*0.999, close=win_price,
                volume=wd.get("volume", 1.0) or 1.0)
            st.session_state.structural_result = sc_mod.get_analysis() or {}
    except Exception as e: logger.warning(f"StructuralContext error: {e}")

    # Alert System
    try:
        al = _ss("alert_system")
        dr = _ss("delta_result", {})
        entry_type = dr.get("entry_signal", {}).get("type", "NEUTRO") if dr else "NEUTRO"
        if al:
            prev = getattr(al, '_last_signal_type', None)
            alert_result = al.check_and_alert(
                signal_change=(prev is not None and prev != entry_type),
                signal_type=entry_type, score=score,
                divergence=_ss("divergence_result", {}),
                recovery=dr.get("intraday_recovery") if dr else None,
                reversal=reversal_result) or {}
            st.session_state.alert_result = alert_result
            st.session_state.alert_html = al.get_alert_html(alert_result.get("alert_type",""), alert_result.get("message","")) if alert_result.get("alert_fired") else ""
    except Exception as e: logger.warning(f"AlertSystem error: {e}")

    # Entry Triggers
    try:
        et = _ss("entry_triggers")
        if et:
            st.session_state.trigger_result = et.evaluate(
                score=score, delta=delta_val, all_data=all_data,
                compression_result=compression_result, regime_result=regime_result,
                divergence_result=_ss("divergence_result", {}),
                confidence_result=confidence_result, category_scores=category_scores) or {}
    except Exception as e: logger.warning(f"EntryTriggers error: {e}")

    # History
    try:
        now = datetime.now()
        dr = _ss("delta_result", {})
        st.session_state.score_history.append({
            "timestamp": now, "score": score,
            "signal_type": score_result.get("signal", {}).get("type", "NEUTRO"),
            "delta": delta_val, "momentum": dr.get("momentum", 0) if dr else 0})
        if len(st.session_state.score_history) > 500:
            st.session_state.score_history = st.session_state.score_history[-500:]
    except: pass

    # Signal Log
    try:
        dr = _ss("delta_result", {})
        entry = dr.get("entry_signal", {}) if dr else {}
        if entry.get("type", "NEUTRO") != "NEUTRO":
            now = datetime.now()
            st.session_state.signal_log.append({
                "time": now.strftime("%H:%M:%S"), "direction": entry.get("label", ""),
                "score": score, "delta": delta_val,
                "confidence": entry.get("confidence", ""),
                "filtered": filtered_signal.get("final_action", entry.get("type", ""))})
            if len(st.session_state.signal_log) > 50:
                st.session_state.signal_log = st.session_state.signal_log[-50:]
    except: pass

    st.session_state["refresh_count"] = st.session_state.get("refresh_count", 0) + 1
    st.session_state.last_refresh = datetime.now()

    # Sectors (every 2nd)
    try:
        if st.session_state.refresh_count % 2 == 0 or not st.session_state.get("sectors_data"):
            sm2 = _ss("sector_manager")
            if sm2: st.session_state.sectors_data = sm2.get_all_sectors() or {}
    except: pass

    # Logging
    try:
        mlog = _ss("macro_logger")
        if mlog:
            mlog.log_full_cycle(score_result, _ss("delta_result", {}), all_data)
            div_r = _ss("divergence_result", {})
            if div_r and div_r.get("type") not in ("INDEFINIDO", "NEUTRO"):
                mlog._log_session_event("DIVERGENCE", {"type": div_r["type"], "label": div_r.get("label", "")})
            if reversal_result and reversal_result.get("detected"):
                mlog._log_session_event("PRICE_REVERSAL", {"type": reversal_result["type"]})
            if regime_result and regime_result.get("regime") not in ("INDEFINIDO",):
                mlog._log_session_event("REGIME", {"regime": regime_result["regime"]})
            cr = _ss("context_result", {})
            if cr and cr.get("context_type") != "LATERAL_INDEFINIDO":
                mlog._log_session_event("CONTEXT", {"type": cr["context_type"], "risk": cr.get("risk", "")})
            if confidence_result and confidence_result.get("confidence_score", 0) < 30:
                mlog._log_session_event("LOW_CONFIDENCE", {"score": confidence_result["confidence_score"]})
    except: pass

    return score_result


# ============ LAYOUT RENDER HELPERS ============
def _render_error(section_name, error_msg):
    st.markdown(f'<div class="err-bar">{section_name}: {str(error_msg)[:60]}</div>', unsafe_allow_html=True)

def render_alert_bar():
    try:
        ar = _ss("alert_result", {})
        if ar and ar.get("alert_fired"):
            at = ar.get("alert_type", "")
            cm = {"PRICE_REVERSAL": UI['warning'], "RECOVERY": UI['positive'],
                  "SIGNAL_CHANGE": UI['accent'], "STRONG_SIGNAL": UI['negative'], "DIVERGENCE": UI['warning']}
            acol = cm.get(at, UI['neutral'])
            amsg = ar.get("message", "").split("\n")[0][:80]
            st.markdown(f'<div class="alert-bar" style="background:{acol}15;border-color:{acol}40"><span class="alert-type" style="color:{acol}">{at.replace("_"," ")}</span><span class="alert-msg">{amsg}</span></div>', unsafe_allow_html=True)
    except Exception as e: _render_error("Alert", e)

def render_status_bar():
    try:
        sr = _ss("score_result", {}); ad = _ss("last_data", {})
        wc = _ss("win_change"); wp = _ss("win_price")
        ws = sf(wp, ",.0f", "---"); wcc = (sf(wc, "+.2f", "---") + "%") if wc is not None else "---"
        dxy = ad.get("DXY", {}) or {}; vix = ad.get("VIX", {}) or {}; ewz = ad.get("EWZ", {}) or {}
        lr_time = _ss("last_refresh", datetime.now())
        mt5on = False
        try:
            ms = _ss("mt5_status")
            if ms: mt5on = ms.get("success", False)
        except: pass
        srctag = '<span class="src-m">M</span>' if mt5on else '<span class="src-y">Y</span>'
        wc2 = _ss("active_win_contract", "---")
        cr = _ss("calendar_result", {}); cal_icon = ""
        if cr and cr.get("has_events"): cal_icon = '<span class="sv" style="color:#FF9800">EV</span>'
        time_str = lr_time.strftime("%H:%M:%S") if hasattr(lr_time, 'strftime') else '---'
        st.markdown(f'<div class="sbar"><div class="sc" style="background:#1a2535"><span class="sl">LIVE</span></div><div class="sc"><span class="sv" style="color:{UI["warning"]}">{time_str}</span></div><div class="sc"><span class="sl">WIN</span><span class="sv">{ws}</span><span class="sv {vc(wc)}">{wcc}</span></div><div class="sc"><span class="sl">DXY</span><span class="sv {vc(dxy.get("change_pct"))}">{sfd(dxy, "change_pct", "+.2f", "---")}%</span></div><div class="sc"><span class="sl">VIX</span><span class="sv" style="color:{UI["warning"]}">{sfd(vix, "current_price", ".1f", "---")}</span></div><div class="sc"><span class="sl">EWZ</span><span class="sv {vc(ewz.get("change_pct"))}">{sfd(ewz, "change_pct", "+.2f", "---")}%</span></div><div class="sc">{srctag}<span class="sv" style="color:{UI["text_muted"]}">{sr.get("assets_available",0)}/{sr.get("assets_total",0)}</span></div><div class="sc"><span class="sl">CT</span><span class="sv" style="color:{UI["text_secondary"]}">{wc2}</span></div><div class="sc">{cal_icon}</div></div>', unsafe_allow_html=True)
    except Exception as e: _render_error("Status", e)

def render_market_phase():
    try:
        now_brt = datetime.now(); time_val = now_brt.hour + now_brt.minute / 60.0
        phases = [("PRE","09:00",9.0,10.0,"#FF9800"),("ABERT","10:00",10.0,10.5,"#4CAF50"),("CORE","10:30",10.5,16.0,"#2196F3"),("CLOSING","16:00",16.0,17.5,"#FF5722")]
        ph = ""
        for pn, pt, ps, pe, pc in phases:
            ia = ps <= time_val < pe; ac = "active" if ia else ""; cs = f"color:{pc}" if ia else ""
            ph += f'<div class="phase-item {ac}" style="{cs}"><div class="phase-label">{pn}</div><div class="phase-time" style="{cs}">{pt}</div></div>'
        st.markdown(f'<div class="mktphase">{ph}</div>', unsafe_allow_html=True)
    except Exception as e: _render_error("Phase", e)

def render_flow_direction():
    try:
        ad = _ss("last_data", {})
        ewz = ad.get("EWZ", {}) or {}; dxy = ad.get("DXY", {}) or {}
        vale_adr = ad.get("VALE_ADR", {}) or {}; vale3 = ad.get("VALE3", {}) or {}
        ec = ewz.get('change_pct'); dc = dxy.get('change_pct')
        vac = vale_adr.get('change_pct'); v3c = vale3.get('change_pct')
        fs = 0; fp = 0
        if ec is not None: fs += (1 if ec > 0 else -1); fp += 1
        if dc is not None: fs += (-1 if dc > 0 else 1); fp += 1
        if vac is not None and v3c is not None:
            gap = vac - v3c; fs += (1 if gap > 0.3 else -1 if gap < -0.3 else 0); fp += 1
        fd = "IN" if fs > 0 else "OUT" if fs < 0 else "NEUTRO"
        fc = UI['positive'] if fs > 0 else UI['negative'] if fs < 0 else UI['neutral']
        fpct = min(100, max(0, 50 + (fs / max(fp, 1)) * 50))
        ffill = fpct if fs >= 0 else 100 - fpct; fl = "0" if fs >= 0 else f"{fpct:.0f}%"
        st.markdown(f'<div class="flowbar"><span class="flow-label">FLOW</span><span class="flow-val" style="color:{fc}">{fd}</span><div class="flow-bar"><div class="flow-fill" style="background:{fc};width:{ffill:.0f}%;left:{fl}"></div></div><span class="flow-label">EWZ {sfd(ewz, "change_pct", "+.1f", "---")}</span></div>', unsafe_allow_html=True)
    except Exception as e: _render_error("Flow", e)

def render_score_row():
    try:
        sr = _ss("score_result", {}); score = sr.get("score", 0) or 0
        signal = sr.get("signal", {}) or {}; score_color = get_score_color(score)
        dr = _ss("delta_result", {}); delta_val = (dr.get("delta", 0) if dr else 0) or 0
        mom_val = (dr.get("momentum", 0) if dr else 0) or 0
        entry = dr.get("entry_signal", {}) if dr else {}; conf = dr.get("confluence", {}) if dr else {}
        smoothed = _ss("smoothed_result", {}); cr = _ss("confidence_result", {})
        dtxt = "COMPRA" if score > 0 else "VENDA" if score < 0 else "NEUTRO"
        dbg = f"{UI['positive']}22" if score > 0 else f"{UI['negative']}22" if score < 0 else f"{UI['neutral']}22"
        dcol = UI['positive'] if score > 0 else UI['negative'] if score < 0 else UI['neutral']
        trend = "MELHORANDO" if delta_val > 5 else "PIORANDO" if delta_val < -5 else "ESTAVEL"
        if conf and conf.get("score_delta_aligned"): trend += " | CONF"
        ipct = max(0, min(100, (score + 100) / 200 * 100))
        glow = "sglow" if UI.get("score_glow", True) else ""
        ema_val = smoothed.get("ema_value") if smoothed else None
        ema_delta = smoothed.get("ema_delta") if smoothed else None
        ema_color = get_score_color(ema_val) if ema_val is not None else score_color
        ema_str = sf(ema_val, "+.1f", "---")
        ema_delta_str = f"({sf(ema_delta, '+.1f', '')})" if ema_delta is not None else ""
        conf_score = (cr.get("confidence_score", 0) if cr else 0) or 0
        conf_color = cr.get("color", UI['neutral']) if cr else UI['neutral']
        st.markdown(f'<div class="srow"><div class="sdir" style="color:{dcol};background:{dbg}">{dtxt}</div><div class="smid"><div class="snum {glow}" style="color:{score_color}">{sf(score, "+.1f", "0.0")}</div><div style="display:flex;align-items:baseline;justify-content:center;gap:3px"><span class="slbl">EMA</span><span class="sema" style="color:{ema_color}">{ema_str}</span><span class="slbl">{ema_delta_str}</span></div><div class="strend">{trend}</div><div class="zbar"><div class="zind" style="left:{ipct}%"></div></div></div><div class="srt"><div class="sconf">conf:{signal.get("confidence","---")}</div><div class="sconf" style="color:{conf_color}">trust:{sf(conf_score, ".0f", "---")}</div><div class="sconf">n:{_ss("refresh_count", 0)}</div></div></div>', unsafe_allow_html=True)
    except Exception as e: _render_error("Score", e)

def render_metrics_strip():
    try:
        sr = _ss("score_result", {}); score = sr.get("score", 0) or 0; sc = get_score_color(score)
        dr = _ss("delta_result", {}); dv = (dr.get("delta", 0) if dr else 0) or 0; mv = (dr.get("momentum", 0) if dr else 0) or 0
        compr = _ss("compression_result", {}); conf_r = _ss("confidence_result", {})
        sh = _ss("score_history", []); ac = 0
        if len(sh) >= 3: ac = (sh[-1]["score"] - sh[-2]["score"]) - (sh[-2]["score"] - sh[-3]["score"])
        zl = "FORTE" if abs(score) > 60 else "MOD" if abs(score) > 30 else "NEU"
        cs = (compr.get("compression_score", 0) if compr else 0) or 0
        cfsc = (conf_r.get("confidence_score", 0) if conf_r else 0) or 0; cfc = conf_r.get("color", UI['neutral']) if conf_r else UI['neutral']
        st.markdown(f'<div class="mstrip"><div class="mc"><div class="mv {vc(dv)}">{sf(dv, "+.1f", "---")}</div><div class="ml">Delta</div></div><div class="mc"><div class="mv {vc(mv)}">{sf(mv, "+.1f", "---")}</div><div class="ml">Mom</div></div><div class="mc"><div class="mv {vc(ac) if abs(ac)>2 else "neu"}">{sf(ac, "+.1f", "---")}</div><div class="ml">Acel</div></div><div class="mc"><div class="mv" style="color:{sc}">{zl}</div><div class="ml">Zona</div></div><div class="mc"><div class="mv" style="color:{cfc}">{sf(cfsc, ".0f", "---")}</div><div class="ml">Trust</div></div><div class="mc"><div class="mv" style="color:{compr.get("color", UI["neutral"]) if compr else UI["neutral"]}">{sf(cs, ".0f", "---")}</div><div class="ml">Comp</div></div></div>', unsafe_allow_html=True)
    except Exception as e: _render_error("Metrics", e)

def render_signal_banner():
    try:
        dr = _ss("delta_result", {}); entry = dr.get("entry_signal", {}) if dr else {}
        fs = _ss("filtered_signal", {}); et = entry.get("type", "NEUTRO") if entry else "NEUTRO"
        el = entry.get("label", "SEM SINAL") if entry else "SEM SINAL"
        ec = entry.get("confidence", "") if entry else ""; ea = entry.get("action", "") if entry else ""
        if "COMPRA_FORTE" in et: sbg,sb,sc2 = "#0a2e0a",UI['positive'],UI['positive']
        elif "COMPRA" in et and "RECUPERACAO" not in et: sbg,sb,sc2 = "#0a1f0a","#66BB6A","#66BB6A"
        elif "RECUPERACAO_FORTE" in et: sbg,sb,sc2 = "#0a2e1a",UI['positive'],UI['positive']
        elif "RECUPERACAO" in et: sbg,sb,sc2 = "#1a2e0a","#66BB6A","#66BB6A"
        elif "VENDA_FORTE" in et: sbg,sb,sc2 = "#2e0a0a",UI['negative'],UI['negative']
        elif "VENDA" in et and "REVERSAO" not in et: sbg,sb,sc2 = "#1f0a0a","#EF5350","#EF5350"
        elif "REVERSAO_BAIXA_INTRADAY" in et: sbg,sb,sc2 = "#2e1a0a",UI['negative'],UI['negative']
        elif "REVERSAO" in et: sbg,sb,sc2 = "#2e2a0a",UI['warning'],UI['warning']
        else: sbg,sb,sc2 = UI['bg_secondary'],UI['border_color'],UI['neutral']
        fn = ""
        if fs:
            if fs.get("was_cooldown"): fn = ' <span style="font-size:6px;color:#FF9800">COOLDOWN</span>'
            elif fs.get("downgraded"): fn = f' <span style="font-size:6px;color:#FF9800">&rarr; {fs.get("final_action", "")}</span>'
        st.markdown(f'<div class="sigb" style="background:{sbg};border-color:{sb}30"><div class="sigt" style="color:{sc2}">{el} <span style="font-size:6px;color:{sb}88">{ec}</span>{fn}</div><div class="siga">{ea}</div></div>', unsafe_allow_html=True)
    except Exception as e: _render_error("Signal", e)

    # Context
    try:
        cr = _ss("context_result", {})
        if cr:
            cl = cr.get("label", ""); cc = cr.get("color", UI['neutral']); crk = cr.get("risk", ""); cre = cr.get("reason", "")[:80]
            st.markdown(f'<div class="ctxb" style="border-left-color:{cc};background:{cc}08"><span class="ctxl" style="color:{cc}">CTX: {cl}</span><span class="ctxd">{cre} | risk:{crk}</span></div>', unsafe_allow_html=True)
    except: pass

    # Recovery/Reversal
    try:
        dr = _ss("delta_result", {}); rec = dr.get("intraday_recovery") if dr else None; rvd = dr.get("intraday_reversal_down") if dr else None
        if rec and rec.get("detected"):
            rc = rec.get("color", UI['neutral']) or UI['neutral']
            st.markdown(f'<div class="recb" style="border-left-color:{rc};background:{rc}08"><span class="recl" style="color:{rc}">RECUPERACAO {rec.get("strength","")}</span><span class="recd">{rec.get("description","")[:80]}</span></div>', unsafe_allow_html=True)
        elif rvd and rvd.get("detected"):
            rc2 = rvd.get("color", UI['neutral']) or UI['neutral']
            st.markdown(f'<div class="recb" style="border-left-color:{rc2};background:{rc2}08"><span class="recl" style="color:{rc2}">REVERSAO BAIXA {rvd.get("strength","")}</span><span class="recd">{rvd.get("description","")[:80]}</span></div>', unsafe_allow_html=True)
    except: pass

    # Regime
    try:
        rr = _ss("regime_result", {})
        if rr and rr.get("regime", "INDEFINIDO") != "INDEFINIDO":
            rcol = rr.get("color", UI['neutral']); rlab = rr.get("label", "")
            rd_obj = _ss("regime_detector"); rrec = rd_obj.get_trading_recommendation() if rd_obj and hasattr(rd_obj, 'get_trading_recommendation') else {}
            rapp = rrec.get("approach", "") if rrec else ""; rrisk = rrec.get("risk_level", "") if rrec else ""
            st.markdown(f'<div class="recb" style="border-left-color:{rcol};background:{rcol}08"><span class="recl" style="color:{rcol}">REGIME: {rlab}</span><span class="recd">{rapp} | risk:{rrisk}</span></div>', unsafe_allow_html=True)
    except: pass

    # Reversal
    try:
        rv = _ss("reversal_result", {})
        if rv and rv.get("detected"):
            rvc = rv.get("color", UI['neutral']); rvs = rv.get("strength", ""); rvt = rv.get("type", "")
            rvs_txt = "DIVERG PRECO" + (" ALTA" if "ALTA" in rvt else " BAIXA" if "BAIXA" in rvt else "")
            rv_m = rv.get("momenta", {}); ms = [f"{p}p:{v:+.2f}%" for p, v in rv_m.items() if v is not None] if rv_m else []
            st.markdown(f'<div class="recb" style="border-left-color:{rvc};background:{rvc}12"><span class="recl" style="color:{rvc}">{rvs_txt} {rvs}</span><span class="recd">{" ".join(ms[:3])}</span></div>', unsafe_allow_html=True)
    except: pass

    # Structural
    try:
        sr = _ss("structural_result", {})
        if sr and sr.get("enabled"):
            av = sr.get("above_vwap"); vd = sr.get("vwap_distance_pct"); ib = sr.get("ib_type", "---"); va = sr.get("va_position", "---")
            vps = "---"
            if av is True: vps = f"ACIMA {sf(vd, '+.2f', '')}" if vd is not None else "ACIMA"
            elif av is False: vps = f"ABAIXO {sf(vd, '+.2f', '')}" if vd is not None else "ABAIXO"
            ibc = "#4FC3F7" if ib == "EXPANDIDO" else "#FFD600" if ib == "CONTRAIDO" else UI['text_muted']
            vac = "#00E676" if va == "ACIMA_VA" else "#FF1744" if va == "ABAIXO_VA" else UI['text_muted']
            st.markdown(f'<div class="struct-row"><div class="struct-item"><span class="struct-lbl">VWAP</span><span class="struct-val" style="color:{UI["accent"]}">{vps}</span></div><div class="struct-item"><span class="struct-lbl">IB</span><span class="struct-val" style="color:{ibc}">{ib}</span></div><div class="struct-item"><span class="struct-lbl">VA</span><span class="struct-val" style="color:{vac}">{va}</span></div></div>', unsafe_allow_html=True)
    except: pass

    # Calendar
    try:
        cr = _ss("calendar_result", {})
        if cr and cr.get("has_events"):
            ev = cr.get("events", []); en = ", ".join(set(e.get("name", "") for e in ev if e.get("name")))
            if en: st.markdown(f'<div class="recb" style="border-left-color:#FF9800;background:#FF980008"><span class="recl" style="color:#FF9800">EVENTO: {en}</span><span class="recd">Pesos ajustados automaticamente</span></div>', unsafe_allow_html=True)
    except: pass

    # Trigger Banner
    try:
        tr = _ss("trigger_result", {})
        if tr and tr.get("summary"):
            ts = tr.get("summary", ""); tb = tr.get("blocks", []); tf = tr.get("triggered", False)
            if tb: tbg, tbc, ttc = "#FF174418", "#FF174440", "#FF8A80"
            elif tf: tbg, tbc, ttc = "#00E67618", "#00E67640", "#69F0AE"
            else: tbg, tbc, ttc = UI["bg_secondary"], UI["border_color"], UI["text_secondary"]
            st.markdown(f'<div class="recb" style="border-left-color:{ttc};background:{tbg}"><span class="recl" style="color:{ttc}">GATILHO: {ts}</span></div>', unsafe_allow_html=True)
    except: pass

def render_sector_grid():
    try:
        st.markdown('<div class="sech">SETORES <span class="secr">5m / 15m / dia</span></div>', unsafe_allow_html=True)
        sd = _ss("sectors_data", {})
        if sd:
            shtml = '<div class="sgrid">'
            for sn, sdata in sd.items():
                sc3 = sdata.get("color", UI['neutral']); ss2 = sdata.get("sector_score", 0) or 0
                ssc2 = UI['positive'] if ss2 > 0 else UI['negative'] if ss2 < 0 else UI['neutral']
                ahtml = ""
                for an, adata in sdata.get("assets", {}).items():
                    dn = adata.get("display_name", an); cd = adata.get("change_pct")
                    c5 = adata.get("change_5m"); c15 = adata.get("change_15m")
                    ahtml += f'<div class="sar"><span class="san">{dn}</span><span class="sv5 {vc(c5)}">{vs(c5) if c5 is not None else "---"}</span><span class="sv5 {vc(c15)}">{vs(c15) if c15 is not None else "---"}</span><span class="svd {vc(cd)}">{vs(cd) if cd is not None else "---"}</span></div>'
                shtml += f'<div class="sblk" style="border-left:2px solid {sc3}30"><div class="shdr"><span class="snm" style="color:{sc3}">{sdata.get("icon","")} {sn}</span><span class="ssc" style="color:{ssc2}">{sf(ss2, "+.0f", "---")}</span></div>{ahtml}</div>'
            shtml += '</div>'
            st.markdown(shtml, unsafe_allow_html=True)
            try:
                sm2 = _ss("sector_manager")
                if sm2 and hasattr(sm2, 'get_market_feeling'):
                    feeling = sm2.get_market_feeling(sd); fd = feeling.get('direction', 0) or 0
                    fc = UI['positive'] if fd > 10 else UI['negative'] if fd < -10 else UI['neutral']
                    st.markdown(f'<div class="fbar"><span class="fbl">FEELING</span><span class="fbv" style="color:{fc}">{feeling.get("feeling","---")}</span><span class="fbd">({sf(fd, "+.0f", "---")})</span><span class="fbd" style="flex:1;text-align:right">altas:{feeling.get("bullish_sectors",0)} baixas:{feeling.get("bearish_sectors",0)}/{feeling.get("total_sectors",0)}</span></div>', unsafe_allow_html=True)
            except: pass
        else:
            st.markdown(f'<div style="padding:2px;color:{UI["text_muted"]};font-size:7px;text-align:center">Carregando setores...</div>', unsafe_allow_html=True)
    except Exception as e: _render_error("Sectors", e)

    # DI Curve
    try:
        ad = _ss("last_data", {})
        dic = ad.get("DI_CURTO", {}) or {}; dim = ad.get("DI_MEDIO", {}) or {}; dil = ad.get("DI_LONGO", {}) or {}
        dcc = dic.get("change_pct"); dmc = dim.get("change_pct"); dlc = dil.get("change_pct")
        if dcc is not None or dlc is not None:
            ma = max(abs(dcc or 0), abs(dmc or 0), abs(dlc or 0), 1.0)
            did = [("CURTO", dcc, "#E040FB"), ("MEDIO", dmc, "#AB47BC"), ("LONGO", dlc, "#7B1FA2")]
            sp = (dlc or 0) - (dcc or 0)
            if sp >= 0.3: shape, shc = "STEEP", UI['negative']
            elif sp <= -0.2: shape, shc = "FLAT", UI['warning']
            elif dcc is not None and dlc is not None and dcc > dlc and dcc > 0: shape, shc = "INV", UI['negative']
            else: shape, shc = "NEUTRO", UI['neutral']
            dbhtml = ""
            for lb, chg, col in did:
                if chg is not None: bh = max(4, min(28, abs(chg)/ma*28)); bc2 = col if chg >= 0 else UI['negative']; vs2 = f"{chg:+.2f}%"
                else: bh, bc2, vs2 = 2, UI['text_muted'], "---"
                dbhtml += f'<div class="dibar"><div class="dibar-fill" style="background:{bc2};height:{bh}px"></div><div class="dibar-val" style="color:{bc2}">{vs2}</div><div class="dibar-label">{lb}</div></div>'
            st.markdown(f'<div class="sech">CURVA DI <span class="secr">curto / medio / longo</span></div><div class="dicurve">{dbhtml}<div class="di-spread"><div class="di-spread-label">SPREAD</div><div class="di-spread-val" style="color:{shc}">{sf(sp, "+.2f", "---")}</div><div class="di-spread-shape" style="color:{shc}">{shape}</div></div></div>', unsafe_allow_html=True)
    except Exception as e: _render_error("DI Curve", e)

    # Confluence Triggers
    try:
        tr = _ss("trigger_result", {})
        if tr:
            tf = tr.get("triggered", False); tsc = tr.get("trigger_score", 0) or 0
            tdir = tr.get("direction", "NEUTRO"); tbl = tr.get("blocks", []); tdt = tr.get("details", {})
            ph = ""
            for i in range(7):
                if i < len(tbl): ph += '<div class="trig-pip blocked"></div>'
                elif i < tsc: ph += '<div class="trig-pip on"></div>'
                else: ph += '<div class="trig-pip"></div>'
            tsc2 = UI['positive'] if tsc >= 4 else UI['warning'] if tsc >= 2 else UI['neutral']
            if tbl: tsc2 = UI['negative']
            tnm = {"score_delta": ("Sc+Delta", "ScD"), "dolar_bank": ("DOL+Bancos", "D+B"), "di_curve": ("Curva DI", "DI"),
                   "compression_break": ("Compressao", "Cmp"), "tier1_alignment": ("Tier1 Align", "T1"),
                   "sector_divergence": ("Setor Div", "Set"), "regime_filter": ("Regime", "Rgm")}
            tihtml = ""
            for tk, (fn, sn) in tnm.items():
                td = tdt.get(tk, {})
                if tk == "regime_filter":
                    ia = td.get("blocked", False); dr2 = "BLOCK" if ia else "OK"; ts3 = str(len(td.get("block_reasons", [])))
                    dc2 = UI['negative'] if ia else UI['positive']; drc = UI['negative'] if ia else UI['text_muted']
                else:
                    ia = td.get("triggered", False); dr2 = td.get("direction", "---")[:4]; ts3 = str(td.get("strength", 0))
                    dc2 = UI['positive'] if ia else UI['border_color']; drc = UI['positive'] if dr2 in ("LONG",) else UI['negative'] if dr2 in ("SHOR",) else UI['text_muted']
                tihtml += f'<div class="trig-item"><div class="trig-dot" style="background:{dc2}"></div><span class="trig-name">{sn}</span><span class="trig-dir" style="color:{drc}">{dr2}</span><span class="trig-strength" style="color:{dc2}">{ts3}</span></div>'
            st.markdown(f'<div class="sech">CONFLUENCIA <span class="secr">7 gatilhos</span></div><div class="trig-score-bar"><span style="font-size:6px;color:{UI["text_muted"]};font-family:{UI["font_family_data"]}">GATILHOS</span><div class="trig-pips">{ph}</div><span style="font-size:11px;font-weight:900;color:{tsc2};font-family:{UI["font_family_data"]}">{tsc}/7</span><span style="font-size:6px;color:{UI["text_muted"]};font-family:{UI["font_family_data"]}">{tdir}</span></div><div class="trig-grid">{tihtml}</div>', unsafe_allow_html=True)
    except Exception as e: _render_error("Confluence", e)

    # Sparkline
    try:
        sh = _ss("score_history", [])
        if len(sh) >= 5:
            ss2 = [h["score"] for h in sh[-20:]]; sm2 = max(abs(s) for s in ss2) if ss2 else 1; sm2 = max(sm2, 1)
            sb = ""
            for s in ss2[-20:]:
                hp = max(1, int(abs(s)/sm2*14)); c2 = UI['positive'] if s > 0 else UI['negative'] if s < 0 else UI['neutral']
                sb += f'<div class="spark-bar" style="height:{hp}px;background:{c2}"></div>'
            st.markdown(f'<div style="display:flex;align-items:center;gap:4px;padding:2px 4px;background:{UI["bg_secondary"]};border-bottom:1px solid {UI["border_color"]}"><span style="font-size:5px;color:{UI["text_muted"]};font-family:{UI["font_family_data"]}">HIST</span><div class="sparkline">{sb}</div><span style="font-size:5px;color:{UI["text_muted"]};font-family:{UI["font_family_data"]}">{len(sh)}pts</span></div>', unsafe_allow_html=True)
    except: pass

def render_key_levels_and_filters():
    try:
        sr = _ss("score_result", {}); score = sr.get("score", 0) or 0
        dr = _ss("delta_result", {}); dv = (dr.get("delta", 0) if dr else 0) or 0
        st.markdown('<div class="sech">REGIOES INDICE <span class="secr">S/R</span></div>', unsafe_allow_html=True)
        lh = ""; rh = ""
        lr = _ss("levels_result", {})
        if lr and lr.get("available"):
            lvs = lr.get("levels", {}); cp = lr.get("current_price")
            lt2 = {"R3":("res",UI['level_resistance']),"R2":("res",UI['level_resistance']),"R1":("res",UI['level_resistance']),
                   "PIVOT":("pvt",UI['level_pivot']),"S1":("sup",UI['level_support']),"S2":("sup",UI['level_support']),"S3":("sup",UI['level_support'])}
            for ln in ["R3","R2","R1","PIVOT","S1","S2","S3"]:
                if ln not in lvs: continue
                lv = lvs[ln]; lty, lc = lt2.get(ln, ("neu", UI['neutral'])); ds = ""
                if cp and lv is not None:
                    d = lv - cp; dp = (d/cp)*100; ds = f"{d:+,.0f} ({sf(dp, '+.1f', '---')}%)"
                lh += f'<div class="lrow"><div class="ldot" style="background:{lc}"></div><span class="lnm" style="color:{lc}">{ln}</span><span class="lpr" style="color:{lc}">{sf(lv, ",.0f", "---")}</span><span class="ldi">{ds}</span></div>'
                if ln == "R1" and cp: lh += f'<div class="lcur"><span class="lcul">WIN {sf(cp, ",.0f", "---")}</span></div>'
        else:
            msg = lr.get("message", "Aguardando dados") if lr else "Aguardando"
            lh = f'<div style="padding:2px;color:{UI["text_muted"]};font-size:6px;text-align:center">{msg}</div>'

        sh = _ss("score_history", []); ac = 0
        if len(sh) >= 3: ac = (sh[-1]["score"] - sh[-2]["score"]) - (sh[-2]["score"] - sh[-3]["score"])
        div = _ss("divergence_result", {}); dtd = div.get("type", "INDEFINIDO") if div else "INDEFINIDO"
        rec = dr.get("intraday_recovery") if dr else None; fs = _ss("filtered_signal", {})
        sz = abs(score) < 4; szc = "wrn" if sz else "pos"; szi = "&#9888;" if sz else "&#10003;"
        ct, ctc = "Ok", "pos"
        if len(sh) >= 4:
            rs = [h["score"] for h in sh[-4:]]; sd2 = all(s > 0 for s in rs) or all(s < 0 for s in rs)
            if sd2: ct = "Confirmado"; ctc = "pos"
            else: ct = "Instavel"; ctc = "wrn"
        at2, atc = "estavel", "neu"
        if ac > 5: at2, atc = "acel alta", "pos"
        elif ac < -5: at2, atc = "acel baixa", "neg"
        dok = dtd not in ("DIVERGENCIA_ALTA", "DIVERGENCIA_BAIXA"); dvt = "Ok" if dok else "DIVERG"; dvc = "pos" if dok else "wrn"
        rvt = "Sim" if rec and rec.get("detected") else "---"; rvc = "pos" if rec and rec.get("detected") else "neu"
        filters = [(szi, "Score zona", sf(score, '+.1f', '---'), szc), ("&#10003;", "Estab", ct, ctc),
                   ("&#9670;", "Acel", at2, atc), ("&#9670;", "Diverg", dvt, dvc), ("&#8634;", "Recup", rvt, rvc)]
        fd = fs.get("filter_details", {}) if fs else {}; cc2 = fs.get("confluence_count", 0) if fs else 0
        mc = SIGNAL_FILTER_CONFIG.get("min_confluence_filters", 3) if SIGNAL_FILTER_CONFIG else 3
        cf = [("score_zone","ScZone"),("delta_direction","Delta"),("momentum_confirm","MomCfm"),("not_in_divergence","NoDiv"),("recovery_confirmed","Recup")]
        for fk, fl in cf:
            fdd = fd.get(fk, {}); fp = fdd.get("passed", False) if fdd else False
            fi = "&#10003;" if fp else "&#10007;"; fc3 = "pos" if fp else "wrn"
            filters.append((fi, fl, f"{cc2}/{mc}" if fk == cf[0][0] else "", fc3))
        for fi, ft, fv, fc3 in filters:
            rh += f'<div class="frow"><span class="fico {fc3}">{fi}</span><span class="ftxt">{ft}</span><span class="fval {fc3}">{fv}</span></div>'
        st.markdown(f'<div class="twocol"><div style="padding:1px">{lh}</div><div style="padding:1px">{rh}</div></div>', unsafe_allow_html=True)
    except Exception as e: _render_error("Levels", e)

    # Divergence banner
    try:
        div = _ss("divergence_result", {}); dtd = div.get("type", "INDEFINIDO") if div else "INDEFINIDO"
        if dtd not in ("INDEFINIDO", "NEUTRO"):
            dc = div.get("color", UI['neutral']); dl = div.get("label", ""); dd = div.get("description", "")[:70] if div.get("description") else ""
            st.markdown(f'<div class="recb" style="border-left-color:{dc};background:{dc}08"><span class="recl" style="color:{dc}">{div.get("icon","")} {dl}</span><span class="recd">{dd}</span></div>', unsafe_allow_html=True)
    except: pass

def render_signal_log():
    try:
        slog = _ss("signal_log", [])
        if slog:
            st.markdown('<div class="sech">SINAIS <span class="secr">ultimos</span></div>', unsafe_allow_html=True)
            lhtml = '<table class="ltbl"><tr><th>Hora</th><th>Dir</th><th>Score</th><th>Delta</th><th>Filtrado</th></tr>'
            for s in slog[-5:]:
                lhtml += f'<tr><td>{s.get("time","")}</td><td class="{vc(s.get("score"))}">{s.get("direction","")[:15]}</td><td>{sf(s.get("score"), "+.0f", "---")}</td><td>{sf(s.get("delta"), "+.1f", "---")}</td><td>{s.get("filtered","")[:12]}</td></tr>'
            lhtml += '</table>'
            st.markdown(lhtml, unsafe_allow_html=True)
    except: pass
    try:
        ps = _ss("perf_stats", {})
        if ps and ps.get("total_signals", 0) > 0:
            wr = ps.get("win_rate", 0) or 0; po = ps.get("payoff_ratio", 0) or 0
            tot = ps.get("total_signals", 0) or 0; w = ps.get("total_wins", 0) or 0; lo = ps.get("total_losses", 0) or 0
            wrc = UI['positive'] if wr > 50 else UI['negative']
            st.markdown(f'<div class="fbar"><span class="fbl">PERF</span><span class="fbv" style="color:{wrc}">WR {sf(wr, ".0f", "---")}%</span><span class="fbd">Payoff {sf(po, ".1f", "---")}x</span><span class="fbd" style="flex:1;text-align:right">{w}W/{lo}L/{tot}total</span></div>', unsafe_allow_html=True)
    except: pass


# ============ MAIN LAYOUT ============
tab_mesa, tab_analysis = st.tabs(["MESA", "ANALISE"])

with tab_mesa:
    try:
        if CRITICAL_FAILURES:
            st.error(f"Modulos criticos faltando: {', '.join(CRITICAL_FAILURES)}")
            st.info("O dashboard funcionara com dados limitados.")

        sr = _ss("score_result", {})
        _has = sr.get("assets_available", 0) > 0 or len(_ss("last_data", {})) > 0
        if not sr or not _has:
            sp = st.empty(); sp.info("Conectando ao Yahoo Finance...")
            try: refresh_data(); sp.empty()
            except Exception as e:
                sp.empty(); logger.error(f"Refresh error: {e}")
                st.session_state.score_result = _EMPTY_SCORE.copy()

        sr = _ss("score_result", {}); _ra = sr.get("assets_available", 0) if sr else 0
        _rdc = len(_ss("last_data", {}))
        if not sr or (_ra == 0 and _rdc == 0):
            if not sr: st.session_state.score_result = _EMPTY_SCORE.copy()
            st.markdown("""<div style="background:#FF174418;border:1px solid #FF174440;border-radius:3px;padding:8px;margin:4px 0;font-size:9px;color:#FF8A80;text-align:center">SEM DADOS - Verifique conexao com internet<br><span style="font-size:7px;color:#6b7d8e">Possiveis causas: internet lenta, Yahoo Finance offline, firewall, ou MT5 desconectado</span></div>""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Tentar novamente", key="retry_nodata"):
                    st.session_state.score_result = {}; st.session_state.last_data = {}; st.session_state.data_manager = None; st.rerun()
            with c2:
                if st.button("Conectar MT5 Rico", key="connect_mt5"):
                    dm = _ss("data_manager")
                    if dm:
                        ok, msg = dm.connect_mt5()
                        if ok: st.success(msg)
                        else: st.warning(msg)
                    st.rerun()
            dm = _ss("data_manager")
            if dm:
                try:
                    diag = dm.get_diagnostic()
                    if diag:
                        with st.expander("Diagnostico", expanded=True): st.json(diag)
                except: pass
        elif _ra > 0 and _ra < 15:
            st.markdown(f'<div style="background:#FFD60018;border:1px solid #FFD60040;border-radius:3px;padding:4px 8px;margin:2px 0;font-size:8px;color:#FFD600;text-align:center">DADOS PARCIAIS: {_ra}/23 ativos</div>', unsafe_allow_html=True)

        # Render all sections
        render_alert_bar()
        render_status_bar()
        render_market_phase()
        render_flow_direction()
        render_score_row()
        render_metrics_strip()
        render_signal_banner()
        render_sector_grid()
        render_key_levels_and_filters()
        render_signal_log()

        # Auto-refresh
        interval = _ss("interval", 30)
        st.markdown(f'<div style="text-align:center;padding:2px;font-size:6px;color:{UI["text_muted"]};font-family:{UI["font_family_data"]}">AUTO-REFRESH {interval}s | v12.0 | MT5+YF Robusto</div>', unsafe_allow_html=True)
        _lr = st.session_state.get("last_refresh_time", 0); _nw = time.time()
        if _nw - _lr >= interval:
            st.session_state["last_refresh_time"] = _nw; time.sleep(0.5); st.rerun()

    except Exception as e:
        logger.error(f"Layout error: {e}\n{traceback.format_exc()}")
        st.markdown(f'<div class="err-display"><div class="err-title">ERRO NO DASHBOARD</div><div>Tipo: {type(e).__name__}</div><div>Mensagem: {str(e)}</div><div class="err-trace">{traceback.format_exc()}</div></div>', unsafe_allow_html=True)
        st.error(f"Erro no dashboard: {type(e).__name__}: {e}")
        if st.button("Tentar novamente"): st.rerun()

with tab_analysis:
    try:
        if render_analysis_tab: render_analysis_tab()
        else: st.info("Modulo de analise nao disponivel.")
    except Exception as e:
        st.error(f"Erro na aba de analise: {e}")
        with st.expander("Detalhes"): st.code(traceback.format_exc())
