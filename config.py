"""
Configuracao do Sistema de Macro Scoring para Mini Indice (WIN)
================================================================
Todos os ativos, pesos, thresholds e parametros configuraveis.
Pesos baseados nas correlacoes validadas com dados reais (60 dias).
v4.0 - Setores, Multi-Timeframe, Niveis-Chave, Sinais Avancados
"""

# ============================================================
# CONFIGURACAO DO MT5 (CORRETORA RICO)
# ============================================================
MT5_CONFIG = {
    "path": r"C:\Program Files\MetaTrader 5\terminal64.exe",
    "login": None,
    "password": None,
    "server": "Rico",
    "timeout": 10000,
    "portable": False,
}

# ============================================================
# MAPEAMENTO DE ATIVOS - MT5
# ============================================================
MT5_SYMBOLS = {
    "WIN": "WINN25",
    "WDO": "WDON25",
    "VALE3": "VALE3",
    "PETR4": "PETR4",
    "ITUB4": "ITUB4",
    "BBDC4": "BBDC4",
    "BBAS3": "BBAS3",
    "PETR3": "PETR3",
    "IFNC": "IFNC",
    "IMAT": "IMAT",
    "ICON": "ICON",
    "BOVA11": "BOVA11",
    "SMALL11": "SMALL11",
    "IMAB11": "IMAB11",
}

# ============================================================
# MAPEAMENTO DE ATIVOS - YAHOO FINANCE
# ============================================================
YF_SYMBOLS = {
    "SP500": "^GSPC",
    "ES_FUTURES": "ES=F",
    "NASDAQ": "^IXIC",
    "DAX": "^GDAXI",
    "EUROSTOXX50": "^STOXX50E",
    "NIKKEI": "^N225",
    "VIX": "^VIX",
    "DXY": "DX-Y.NYB",
    "USDBRL": "BRL=X",
    "IRON_ORE": "SI=F",
    "BRENT": "BZ=F",
    "WTI": "CL=F",
    "COPPER": "HG=F",
    "GOLD": "GC=F",
    "US10Y": "^TNX",
    "US2Y": "^IRX",
    "BITCOIN": "BTC-USD",
    "VALE_ADR": "VALE",
    "PETR_ADR": "PBR",
    "EWZ": "EWZ",
    "IBOV": "^BVSP",
}

DUAL_SOURCE_ASSETS = {
    "VALE3":  {"mt5": "VALE3", "yf": "VALE3.SA"},
    "PETR4":  {"mt5": "PETR4", "yf": "PETR4.SA"},
    "ITUB4":  {"mt5": "ITUB4", "yf": "ITUB4.SA"},
    "BBDC4":  {"mt5": "BBDC4", "yf": "BBDC4.SA"},
    "BBAS3":  {"mt5": "BBAS3", "yf": "BBAS3.SA"},
    "IFNC":   {"mt5": "IFNC",  "yf": "IFNC.SA"},
    "IMAT":   {"mt5": "IMAT",  "yf": "IMAT.SA"},
    "ICON":   {"mt5": "ICON",  "yf": "ICON.SA"},
    "IMAB11": {"mt5": "IMAB11","yf": "IMAB11.SA"},
    "BOVA11": {"mt5": "BOVA11","yf": "BOVA11.SA"},
}

# ============================================================
# GRUPOS DE SETORES - PAINEL PRINCIPAL
# Cada setor com ativos e tickers YF para buscar variacao
# ============================================================
SECTOR_GROUPS = {
    "BANCOS": {
        "icon": "BNK",
        "color": "#2196F3",
        "description": "Setor financeiro B3",
        "assets": {
            "ITUB4": {"yf": "ITUB4.SA", "display": "Itau"},
            "BBDC4": {"yf": "BBDC4.SA", "display": "Bradesco"},
            "BBAS3": {"yf": "BBAS3.SA", "display": "B Brasil"},
        }
    },
    "MINERACAO": {
        "icon": "MIN",
        "color": "#FF9800",
        "description": "Mineradoras e siderurgicas",
        "assets": {
            "VALE3": {"yf": "VALE3.SA", "display": "Vale"},
            "CSNA3": {"yf": "CSNA3.SA", "display": "CSN"},
            "GGBR4": {"yf": "GGBR4.SA", "display": "Gerdau"},
        }
    },
    "ENERGIA": {
        "icon": "ENR",
        "color": "#4CAF50",
        "description": "Petroleo e energia",
        "assets": {
            "PETR4": {"yf": "PETR4.SA", "display": "Petrobras"},
            "PRIO3": {"yf": "PRIO3.SA", "display": "Prio"},
            "EGIE3": {"yf": "EGIE3.SA", "display": "Engie"},
        }
    },
    "EXTERIOR": {
        "icon": "EXT",
        "color": "#9C27B0",
        "description": "Indices globais e fluxo",
        "assets": {
            "SP500": {"yf": "^GSPC", "display": "S&P500"},
            "DAX": {"yf": "^GDAXI", "display": "DAX"},
            "EWZ": {"yf": "EWZ", "display": "EWZ"},
            "ES_FUTURES": {"yf": "ES=F", "display": "ES Fut"},
        }
    },
    "MOEDAS": {
        "icon": "FX",
        "color": "#00BCD4",
        "description": "Dolar e moedas",
        "assets": {
            "DXY": {"yf": "DX-Y.NYB", "display": "DXY"},
            "USDBRL": {"yf": "BRL=X", "display": "USD/BRL"},
            "WDO": {"yf": "BRL=X", "display": "WDO"},
        }
    },
    "JUROS": {
        "icon": "TX",
        "color": "#E040FB",
        "description": "Taxas e renda fixa",
        "assets": {
            "US10Y": {"yf": "^TNX", "display": "US10Y"},
            "US2Y": {"yf": "^IRX", "display": "US2Y"},
            "IMAB11": {"yf": "IMAB11.SA", "display": "IMA-B"},
        }
    },
    "COMMODITIES": {
        "icon": "COM",
        "color": "#FF5722",
        "description": "Materias-primas",
        "assets": {
            "IRON_ORE": {"yf": "SI=F", "display": "Ferro"},
            "BRENT": {"yf": "BZ=F", "display": "Brent"},
            "COPPER": {"yf": "HG=F", "display": "Cobre"},
        }
    },
    "VOLATILIDADE": {
        "icon": "VIX",
        "color": "#FFD600",
        "description": "Medo e volatilidade",
        "assets": {
            "VIX": {"yf": "^VIX", "display": "VIX"},
        }
    },
}

# ============================================================
# CONFIGURACAO MULTI-TIMEFRAME
# ============================================================
MULTI_TIMEFRAME_CONFIG = {
    "intervals": {
        "5m": {"yf_interval": "5m", "yf_period": "1d", "label": "5m"},
        "15m": {"yf_interval": "15m", "yf_period": "5d", "label": "15m"},
        "dia": {"yf_interval": "1d", "yf_period": "5d", "label": "Dia"},
    },
    "cache_duration": 30,
}

# ============================================================
# CONFIGURACAO DE NIVEIS-CHAVE (S/R) DO WIN
# ============================================================
KEY_LEVELS_CONFIG = {
    "enabled": True,
    "methods": ["pivot_classic", "recent_highs_lows", "score_zones"],
    "pivot_style": "classic",
    "lookback_days": 5,
    "min_touches_for_level": 2,
    "level_proximity_pct": 0.3,
    "win_multiplier": 5,
}

# ============================================================
# TRACKING DO WIN PARA DIVERGENCIA
# ============================================================
WIN_TRACKING = {
    "mt5_symbol": "WINN25",
    "yf_symbol": "EWZ",
    "yf_direct": "^BVSP",
    "enabled": True,
    "min_periods_for_trend": 5,
}

# ============================================================
# PESOS DO SCORING MACRO
# ============================================================
MACRO_WEIGHTS = {
    "EWZ":         {"weight": 0.12, "direction": +1, "corr": 0.96, "category": "Fluxo Estrangeiro"},
    "VALE_ADR":    {"weight": 0.10, "direction": +1, "corr": 0.75, "category": "ADRs/Overnight"},
    "VIX":         {"weight": 0.09, "direction": -1, "corr": -0.63, "category": "Volatilidade"},
    "DXY":         {"weight": 0.08, "direction": -1, "corr": -0.57, "category": "Moedas"},
    "ES_FUTURES":  {"weight": 0.08, "direction": +1, "corr": 0.57, "category": "Indices Globais"},
    "EUROSTOXX50": {"weight": 0.07, "direction": +1, "corr": 0.53, "category": "Indices Globais"},
    "IMAB11":      {"weight": 0.07, "direction": +1, "corr": 0.56, "category": "Juros/Renda Fixa"},
    "DAX":         {"weight": 0.05, "direction": +1, "corr": 0.49, "category": "Indices Globais"},
    "US10Y":       {"weight": 0.05, "direction": -1, "corr": -0.48, "category": "Juros/Renda Fixa"},
    "WTI":         {"weight": 0.04, "direction": -1, "corr": -0.50, "category": "Commodities"},
    "SP500":       {"weight": 0.04, "direction": +1, "corr": 0.45, "category": "Indices Globais"},
    "COPPER":      {"weight": 0.04, "direction": +1, "corr": 0.44, "category": "Commodities"},
    "BITCOIN":     {"weight": 0.03, "direction": +1, "corr": 0.41, "category": "Risk Appetite"},
    "NIKKEI":      {"weight": 0.03, "direction": +1, "corr": 0.35, "category": "Indices Globais"},
    "IFNC":        {"weight": 0.03, "direction": +1, "corr": 0.40, "category": "Setorial BR"},
    "WDO":         {"weight": 0.03, "direction": -1, "corr": -0.35, "category": "Moedas"},
    "BRENT":       {"weight": 0.02, "direction": -1, "corr": -0.30, "category": "Commodities"},
    "IMAT":        {"weight": 0.01, "direction": +1, "corr": 0.25, "category": "Setorial BR"},
    "IRON_ORE":    {"weight": 0.01, "direction": +1, "corr": 0.20, "category": "Commodities"},
    "PETR_ADR":    {"weight": 0.01, "direction": +1, "corr": 0.22, "category": "ADRs/Overnight"},
}

# ============================================================
# THRESHOLDS E PARAMETROS DE SINAL
# ============================================================
SIGNAL_CONFIG = {
    "strong_bullish": 60,
    "moderate_bullish": 30,
    "neutral_low": -30,
    "moderate_bearish": -30,
    "strong_bearish": -60,
    "delta_acceleration": 15,
    "delta_deceleration": -15,
    "var_periods": {
        "intraday": 0,
        "short_term": 5,
        "medium_term": 21,
    },
    "refresh_interval": 30,
    "trading_start": "09:00",
    "trading_end": "17:30",
    "pre_market_start": "09:00",
    "divergence_signal_threshold": 25,
    "strong_move_delta": 15,
    "reversal_confirmation_periods": 3,
}

# ============================================================
# CATEGORIAS PARA O DASHBOARD (scoring)
# ============================================================
CATEGORIES = {
    "Indices Globais": {
        "icon": "GLO",
        "color": "#2196F3",
        "assets": ["ES_FUTURES", "SP500", "EUROSTOXX50", "DAX", "NIKKEI"]
    },
    "Volatilidade": {
        "icon": "VIX",
        "color": "#FF5722",
        "assets": ["VIX"]
    },
    "Moedas": {
        "icon": "FX",
        "color": "#4CAF50",
        "assets": ["DXY", "WDO", "USDBRL"]
    },
    "Commodities": {
        "icon": "COM",
        "color": "#FF9800",
        "assets": ["IRON_ORE", "BRENT", "WTI", "COPPER", "GOLD"]
    },
    "Juros/RF": {
        "icon": "TX",
        "color": "#9C27B0",
        "assets": ["US10Y", "IMAB11"]
    },
    "ADRs": {
        "icon": "ADR",
        "color": "#00BCD4",
        "assets": ["VALE_ADR", "PETR_ADR", "EWZ"]
    },
    "Risk": {
        "icon": "RSK",
        "color": "#E91E63",
        "assets": ["BITCOIN"]
    },
    "Setorial": {
        "icon": "SET",
        "color": "#8BC34A",
        "assets": ["IFNC", "IMAT", "ICON"]
    },
}

# ============================================================
# CONFIGURACAO DO DASHBOARD
# ============================================================
DASHBOARD_CONFIG = {
    "width": 600,
    "height": 1000,
    "theme": "dark",
    "compact_mode": True,
    "sidebar_collapsed": True,
}

# ============================================================
# CONFIGURACAO DE INTERFACE (UI) - AJUSTAVEL
# ============================================================
UI_CONFIG = {
    "panel_width": 580,
    "panel_padding": 6,
    "font_family_data": "'Consolas', 'JetBrains Mono', 'Courier New', monospace",
    "font_family_ui": "'Segoe UI', 'Inter', 'Helvetica Neue', Arial, sans-serif",
    "score_font_size": 36,
    "score_label_font_size": 10,
    "score_glow": True,
    "metric_value_font_size": 13,
    "metric_label_font_size": 7,
    "signal_font_size": 12,
    "signal_action_font_size": 8,
    "sector_title_font_size": 8,
    "sector_asset_font_size": 8,
    "sector_var_font_size": 9,
    "sector_score_font_size": 11,
    "sector_block_padding": 4,
    "level_font_size": 9,
    "level_price_font_size": 10,
    "level_row_height": 16,
    "divergence_font_size": 9,
    "divergence_desc_size": 7,
    "header_title_size": 10,
    "header_status_size": 8,
    "chart_height": 90,
    "bg_primary": "#080c12",
    "bg_secondary": "#0d1420",
    "bg_tertiary": "#111a28",
    "bg_sector": "#0a1018",
    "border_color": "#1a2535",
    "border_light": "#243040",
    "text_primary": "#d0d8e0",
    "text_secondary": "#6b7d8e",
    "text_muted": "#3a4a5a",
    "accent": "#4fc3f7",
    "positive": "#00E676",
    "negative": "#FF1744",
    "warning": "#FFD600",
    "neutral": "#78909C",
    "level_resistance": "#FF5252",
    "level_support": "#69F0AE",
    "level_pivot": "#FFD740",
    "level_current": "#FFFFFF",
}

# ============================================================
# CONFIGURACAO DE DIVERGENCIA
# ============================================================
DIVERGENCE_CONFIG = {
    "enabled": True,
    "divergence_periods": 20,
    "divergence_min_periods": 5,
    "divergence_score_threshold": 3,
    "divergence_win_threshold_pct": 0.1,
}

# ============================================================
# CONFIGURACAO DE LOGS
# ============================================================
LOG_CONFIG = {
    "log_dir": "logs",
    "score_log_file": "score_log.csv",
    "asset_log_file": "asset_log.csv",
    "signal_log_file": "signal_log.csv",
    "session_log_file": "session_log.jsonl",
    "retention_days": 90,
    "log_every_n_reads": 1,
    "enable_score_log": True,
    "enable_asset_log": True,
    "enable_signal_log": True,
    "enable_session_log": True,
}

# ============================================================
# PARAMETROS DE BACKTEST / VALIDACAO
# ============================================================
BACKTEST_CONFIG = {
    "benchmark": "BOVA11",
    "initial_capital": 100000,
    "position_size": 1,
    "stop_loss_points": 200,
    "take_profit_points": 400,
}
