"""
Configuracao do Sistema de Macro Scoring para Mini Indice (WIN)
================================================================
Todos os ativos, pesos, thresholds e parametros configuraveis.
v7.0 - Reestruturacao completa dos pesos para DAY TRADE:
       - B3 diretos (DOL, DI, bancões, VALE3, PETR4, setoriais) com peso MAIOR
       - Internacionais/ADRs com peso MENOR (contexto, nao gatilho)
       - Sistema de gatilhos de entrada com confluencia
       - Logging completo para auditoria diaria
       - Script de validacao empirica de correlacoes
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
# DETECCAO DINAMICA DE CONTRATO WIN/WDO
# ============================================================
WIN_CONTRACT_CONFIG = {
    "enabled": True,
    "month_codes": {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
                    7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"},
    "base_prefix": "WIN",
    "wdo_prefix": "WDO",
    "roll_days_before": 3,
}

# ============================================================
# MAPEAMENTO DE ATIVOS - MT5
# ============================================================
MT5_SYMBOLS = {
    "WIN": "AUTO",
    "WDO": "AUTO",
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
    "DI1_FUTURES": "IMAB11.SA",  # DI1=F delisted from YF, using IMA-B as proxy
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
            "DI1_FUTURES": {"yf": "IMAB11.SA", "display": "IMA-B"},
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
    "mt5_symbol": "AUTO",
    "yf_symbol": "EWZ",
    "yf_direct": "^BVSP",
    "enabled": True,
    "min_periods_for_trend": 5,
}

# ============================================================
# PESOS DO SCORING MACRO (v7.0 - DAY TRADE INTRADAY)
# Total = 1.00
# ============================================================
# FILOSOFIA v7.0:
#   TIER 1 - B3 DIRETOS (55%): Ativos que movem o WIN no MESMO segundo
#     DOL/WDO: Inversamente correlacionado, move ponto a ponto
#     DI/Curva de Juros: Define custo de carry, fluxo de renda fixa
#     Bancões: 40% do IBOV, movem o indice junto
#     VALE3/PETR4: Pesos pesados do IBOV
#     Setoriais (IFNC/IMAT/ICON): Sinal setorial em tempo real
#
#   TIER 2 - CONTEXTO GLOBAL (30%): Cenário macro que define o tom
#     EWZ: Fluxo estrangeiro real-time
#     ES/S&P: Contexto US, pre-market e overnight
#     VIX: Medo global
#     DXY: Forca do dolar
#     Indices globais: DAX, EuroStoxx
#
#   TIER 3 - COMPLEMENTAR (15%): Confirmação secundária
#     ADRs, commodities, crypto, juros US
# ============================================================
MACRO_WEIGHTS = {
    # ---- TIER 1: B3 DIRETOS (55%) - Movem o WIN em tempo real ----
    "WDO":         {"weight": 0.12, "direction": -1, "corr": -0.85, "category": "Dolar/B3",
                    "tier": 1, "intraday_impact": "CRITICO", "note": "Mini dolar - move WIN ponto a ponto"},
    "DI1_FUTURES": {"weight": 0.08, "direction": +1, "corr": 0.70, "category": "Juros/DI",
                    "tier": 1, "intraday_impact": "CRITICO", "note": "Curva de juros - define carry e fluxo RF"},
    "ITUB4":       {"weight": 0.06, "direction": +1, "corr": 0.82, "category": "Bancos",
                    "tier": 1, "intraday_impact": "ALTO", "note": "Itau - maior banco, peso IBOV"},
    "BBDC4":       {"weight": 0.05, "direction": +1, "corr": 0.80, "category": "Bancos",
                    "tier": 1, "intraday_impact": "ALTO", "note": "Bradesco - sensibilidade juros"},
    "BBAS3":       {"weight": 0.04, "direction": +1, "corr": 0.78, "category": "Bancos",
                    "tier": 1, "intraday_impact": "ALTO", "note": "Banco do Brasil - banco publico"},
    "VALE3":       {"weight": 0.06, "direction": +1, "corr": 0.75, "category": "Mineracao",
                    "tier": 1, "intraday_impact": "ALTO", "note": "Vale B3 - peso pesado IBOV, commodity"},
    "PETR4":       {"weight": 0.05, "direction": +1, "corr": 0.72, "category": "Energia",
                    "tier": 1, "intraday_impact": "ALTO", "note": "Petrobras B3 - preco + politica"},
    "IFNC":        {"weight": 0.03, "direction": +1, "corr": 0.70, "category": "Setorial BR",
                    "tier": 1, "intraday_impact": "MEDIO", "note": "Financeiro - sinal setor bancario"},
    "IMAT":        {"weight": 0.03, "direction": +1, "corr": 0.65, "category": "Setorial BR",
                    "tier": 1, "intraday_impact": "MEDIO", "note": "Material - sinal commodity BR"},
    "ICON":        {"weight": 0.03, "direction": +1, "corr": 0.65, "category": "Setorial BR",
                    "tier": 1, "intraday_impact": "MEDIO", "note": "Consumo - solar demanda interna"},

    # ---- TIER 2: CONTEXTO GLOBAL (30%) - Define o tom do dia ----
    "EWZ":         {"weight": 0.06, "direction": +1, "corr": 0.96, "category": "Fluxo Estrangeiro",
                    "tier": 2, "intraday_impact": "ALTO", "note": "ETF Brasil - fluxo gringo real-time"},
    "ES_FUTURES":  {"weight": 0.05, "direction": +1, "corr": 0.57, "category": "Indices Globais",
                    "tier": 2, "intraday_impact": "ALTO", "note": "S&P futures - contexto US intraday"},
    "VIX":         {"weight": 0.05, "direction": -1, "corr": -0.63, "category": "Volatilidade",
                    "tier": 2, "intraday_impact": "MEDIO", "note": "Medo global - risco on/off"},
    "DXY":         {"weight": 0.05, "direction": -1, "corr": -0.57, "category": "Moedas",
                    "tier": 2, "intraday_impact": "MEDIO", "note": "Dolar index - forca USD"},
    "IMAB11":      {"weight": 0.04, "direction": +1, "corr": 0.56, "category": "Juros/DI",
                    "tier": 2, "intraday_impact": "MEDIO", "note": "IMA-B proxy DI - curva BR"},
    "SP500":       {"weight": 0.03, "direction": +1, "corr": 0.45, "category": "Indices Globais",
                    "tier": 2, "intraday_impact": "MEDIO", "note": "S&P cash - confirma abertura"},
    "EUROSTOXX50": {"weight": 0.02, "direction": +1, "corr": 0.53, "category": "Indices Globais",
                    "tier": 2, "intraday_impact": "BAIXO", "note": "Europa - contexto pre-market"},

    # ---- TIER 3: COMPLEMENTAR (15%) - Confirmacao secundaria ----
    "DAX":         {"weight": 0.02, "direction": +1, "corr": 0.49, "category": "Indices Globais",
                    "tier": 3, "intraday_impact": "BAIXO", "note": "Alemanha - contexto Europa"},
    "US10Y":       {"weight": 0.02, "direction": -1, "corr": -0.48, "category": "Juros/DI",
                    "tier": 3, "intraday_impact": "BAIXO", "note": "Tesouro 10y - custo capital global"},
    "VALE_ADR":    {"weight": 0.02, "direction": +1, "corr": 0.75, "category": "ADRs/Overnight",
                    "tier": 3, "intraday_impact": "BAIXO", "note": "Vale ADR - gap overnight"},
    "COPPER":      {"weight": 0.02, "direction": +1, "corr": 0.44, "category": "Commodities",
                    "tier": 3, "intraday_impact": "BAIXO", "note": "Cobre - pulso China/commodity"},
    "WTI":         {"weight": 0.02, "direction": -1, "corr": -0.50, "category": "Commodities",
                    "tier": 3, "intraday_impact": "BAIXO", "note": "Petroleo - impacto PETR"},
    "PETR_ADR":    {"weight": 0.01, "direction": +1, "corr": 0.22, "category": "ADRs/Overnight",
                    "tier": 3, "intraday_impact": "BAIXO", "note": "Petrobras ADR - gap"},
    "BRENT":       {"weight": 0.01, "direction": -1, "corr": -0.30, "category": "Commodities",
                    "tier": 3, "intraday_impact": "BAIXO", "note": "Brent - referencia Europa"},
    "IRON_ORE":    {"weight": 0.01, "direction": +1, "corr": 0.20, "category": "Commodities",
                    "tier": 3, "intraday_impact": "BAIXO", "note": "Ferro - pulso Vale"},
    "BITCOIN":     {"weight": 0.01, "direction": +1, "corr": 0.41, "category": "Risk Appetite",
                    "tier": 3, "intraday_impact": "BAIXO", "note": "BTC - risco global"},
    "NIKKEI":      {"weight": 0.01, "direction": +1, "corr": 0.35, "category": "Indices Globais",
                    "tier": 3, "intraday_impact": "BAIXO", "note": "Japao - sessao asia"},
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
# CATEGORIAS PARA O DASHBOARD (v7.0 - DAY TRADE)
# ============================================================
CATEGORIES = {
    "Dolar/B3": {
        "icon": "DOL",
        "color": "#00BCD4",
        "assets": ["WDO", "DXY", "USDBRL"]
    },
    "Bancos": {
        "icon": "BNK",
        "color": "#2196F3",
        "assets": ["ITUB4", "BBDC4", "BBAS3", "IFNC"]
    },
    "Mineracao": {
        "icon": "MIN",
        "color": "#FF9800",
        "assets": ["VALE3", "VALE_ADR", "IRON_ORE"]
    },
    "Energia": {
        "icon": "ENR",
        "color": "#4CAF50",
        "assets": ["PETR4", "PETR_ADR", "WTI", "BRENT"]
    },
    "Setorial BR": {
        "icon": "SET",
        "color": "#8BC34A",
        "assets": ["IFNC", "IMAT", "ICON"]
    },
    "Juros/DI": {
        "icon": "TX",
        "color": "#9C27B0",
        "assets": ["DI1_FUTURES", "IMAB11", "US10Y"]
    },
    "Fluxo Estrangeiro": {
        "icon": "FLX",
        "color": "#E91E63",
        "assets": ["EWZ", "ES_FUTURES", "SP500"]
    },
    "Volatilidade": {
        "icon": "VIX",
        "color": "#FF5722",
        "assets": ["VIX"]
    },
    "Moedas": {
        "icon": "FX",
        "color": "#00BCD4",
        "assets": ["DXY", "WDO", "USDBRL"]
    },
    "Indices Globais": {
        "icon": "GLO",
        "color": "#2196F3",
        "assets": ["ES_FUTURES", "SP500", "EUROSTOXX50", "DAX", "NIKKEI"]
    },
    "Commodities": {
        "icon": "COM",
        "color": "#FF9800",
        "assets": ["IRON_ORE", "BRENT", "WTI", "COPPER"]
    },
    "ADRs": {
        "icon": "ADR",
        "color": "#00BCD4",
        "assets": ["VALE_ADR", "PETR_ADR"]
    },
    "Risk": {
        "icon": "RSK",
        "color": "#E91E63",
        "assets": ["BITCOIN"]
    },
}

# ============================================================
# CONFIGURACAO DO SCORE SMOOTHER (EMA/SMA)
# ============================================================
SCORE_SMOOTHER_CONFIG = {
    "enabled": True,
    "ema_period": 5,
    "sma_period": 10,
    "use_ema": True,
    "max_history": 500,
}

# ============================================================
# CONFIGURACAO DE PRICE REVERSAL (Divergencia Preco vs Score)
# ============================================================
PRICE_REVERSAL_CONFIG = {
    "enabled": True,
    "momentum_periods": [3, 5, 10],
    "score_threshold_bearish": -25,
    "score_threshold_bullish": 25,
    "min_positive_periods": 2,
    "strong_momentum_threshold": 0.5,
    "moderate_momentum_threshold": 0.2,
    "max_history": 500,
}

# ============================================================
# CONFIGURACAO DE ALERTAS (Som + Webhook + Telegram)
# ============================================================
ALERT_CONFIG = {
    "enabled": True,
    "cooldown_seconds": 120,
    "sound_enabled": True,
    "webhook_enabled": False,
    "webhook_url": "",
    "telegram_enabled": False,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "alert_on_signal_change": True,
    "alert_on_strong_signal": True,
    "alert_on_divergence": True,
    "alert_on_recovery": True,
    "alert_on_reversal": True,
    "strong_signal_threshold": 50,
}

# ============================================================
# CONFIGURACAO DO SIGNAL FILTER (Cooldown + Confluencia)
# ============================================================
SIGNAL_FILTER_CONFIG = {
    "enabled": True,
    "cooldown_same_type_seconds": 300,
    "cooldown_same_direction_seconds": 120,
    "min_confluence_filters": 3,
    "filters": {
        "score_zone": True,
        "delta_direction": True,
        "momentum_confirm": True,
        "not_in_divergence": True,
        "recovery_confirmed": True,
    },
}

# ============================================================
# CONFIGURACAO DE PERFORMANCE TRACKER
# ============================================================
PERFORMANCE_CONFIG = {
    "enabled": True,
    "max_pending_signals": 50,
    "max_signal_lifetime_seconds": 1800,
    "default_sl_points": 200,
    "default_tp_points": 400,
    "track_all_signals": True,
}

# ============================================================
# CONFIGURACAO DO REGIME DETECTOR
# ============================================================
REGIME_CONFIG = {
    "enabled": True,
    "lookback_periods": 20,
    "trend_threshold": 20,
    "lateral_range": 15,
    "volatility_threshold": 15,
    "transition_delta_threshold": 10,
    "min_periods": 5,
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
    "performance_log_file": "performance_log.csv",
    "system_log_file": "system_log.jsonl",
    "retention_days": 90,
    "log_every_n_reads": 1,
    "enable_score_log": True,
    "enable_asset_log": True,
    "enable_signal_log": True,
    "enable_session_log": True,
    "log_score_ema": True,
    "log_regime": True,
    "log_price_reversal": True,
    "log_sector_snapshot": True,
    "log_win_price": True,
    "enable_performance_log": True,
    "enable_system_log": True,
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

# ============================================================
# CONFIGURACAO DO CONTEXT CLASSIFIER (v6.0)
# ============================================================
CONTEXT_CLASSIFIER_CONFIG = {
    "enabled": True,
    "min_periods": 5,
}

# ============================================================
# CONFIGURACAO DO STRUCTURAL CONTEXT - VWAP/IB/VA (v6.0)
# ============================================================
STRUCTURAL_CONTEXT_CONFIG = {
    "enabled": True,
    "vwap_period": "session",
    "ib_start_hour": 9,
    "ib_end_hour": 10,
    "va_lookback_days": 5,
}

# ============================================================
# CONFIGURACAO DO DYNAMIC WEIGHTS (v6.0)
# ============================================================
DYNAMIC_WEIGHTS_CONFIG = {
    "enabled": True,
    "lookback_periods": 78,
    "recalc_interval_seconds": 900,
    "max_weight_change_pct": 20,
    "min_correlation_threshold": 0.3,
}

# ============================================================
# CONFIGURACAO DO COMPRESSION DETECTOR (v6.0)
# ============================================================
COMPRESSION_DETECTOR_CONFIG = {
    "enabled": True,
    "atr_lookback": 20,
    "atr_percentile_low": 20,
    "score_variance_window": 15,
    "sector_convergence_threshold": 0.7,
}

# ============================================================
# CONFIGURACAO DO CONFIDENCE SCORE (v6.0)
# ============================================================
CONFIDENCE_SCORE_CONFIG = {
    "enabled": True,
    "min_data_quality": 0.6,
}

# ============================================================
# CONFIGURACAO DO CALENDAR EVENTS (v6.0)
# ============================================================
CALENDAR_EVENTS_CONFIG = {
    "enabled": True,
    "events": [],
}

# ============================================================
# GATILHOS DE ENTRADA - SISTEMA DE TRIGGERS (v7.0)
# ============================================================
# Define condicoes especificas para pontos de entrada
# Cada gatilho requer confluencia de multiplos fatores
ENTRY_TRIGGERS_CONFIG = {
    "enabled": True,

    # Gatilho 1: SCORE + DELTA (viés + aceleração)
    "score_delta_trigger": {
        "enabled": True,
        # Compra: score > 35 E delta > 10 (acelerando alta)
        "long_score_min": 35,
        "long_delta_min": 10,
        # Venda: score < -35 E delta < -10 (acelerando baixa)
        "short_score_max": -35,
        "short_delta_max": -10,
        "description": "Score forte + Delta acelerando = entrada agressiva",
    },

    # Gatilho 2: DOL vs BANCOS (divergência interna B3)
    "dolar_bank_trigger": {
        "enabled": True,
        # DOL caindo + Bancos subindo = COMPRA forte (risco Brasil ON)
        "long_wdo_max_change": -0.3,    # WDO caindo = dolar caindo
        "long_banks_min_change": 0.2,    # Bancos subindo
        # DOL subindo + Bancos caindo = VENDA forte (risco Brasil OFF)
        "short_wdo_min_change": 0.3,     # WDO subindo = dolar subindo
        "short_banks_max_change": -0.2,   # Bancos caindo
        "bank_assets": ["ITUB4", "BBDC4", "BBAS3", "IFNC"],
        "description": "DOL vs Bancos - conflito interno B3 = gatilho forte",
    },

    # Gatilho 3: SCORE REVERSAL + COMPRESSION (saída de compressão)
    "compression_break_trigger": {
        "enabled": True,
        # Score saindo de zona neutra após compressão = breakout
        "compression_periods_min": 5,     # Pelo menos 5 periodos comprimido
        "compression_score_range": 15,    # Score variando menos de 15 pts
        "breakout_delta_min": 8,          # Delta do breakout > 8
        "description": "Saida de compressao + delta forte = breakout",
    },

    # Gatilho 4: TIER1 CONFLUENCIA (B3 diretos alinhados)
    "tier1_alignment_trigger": {
        "enabled": True,
        # Pelo menos N ativos Tier1 na mesma direção
        "min_aligned_assets": 6,          # 6 de 10 Tier1 alinhados
        "tier1_assets": ["WDO", "DI1_FUTURES", "ITUB4", "BBDC4", "BBAS3",
                         "VALE3", "PETR4", "IFNC", "IMAT", "ICON"],
        "aligned_change_threshold": 0.15, # Variação mínima para contar como alinhado
        "description": "B3 diretos alinhados = movimento coordenado",
    },

    # Gatilho 5: REGIME + DIVERGENCIA (anti-entrada)
    "regime_filter_trigger": {
        "enabled": True,
        # NÃO entrar se regime lateral + sem direção clara
        "block_on_lateral": True,         # Bloqueia em regime lateral
        "block_on_divergence": True,      # Bloqueia se divergência ativa
        "block_on_low_confidence": True,  # Bloqueia se confiança < 50%
        "min_confidence_pct": 50,
        "description": "Filtro anti-entrada: lateral, divergencia, baixa confianca",
    },
}

# ============================================================
# LOG TURBINADO - AUDITORIA DIARIA (v7.0)
# ============================================================
# Logs completos para revisão diária e evolução do sistema
ENHANCED_LOG_CONFIG = {
    "enabled": True,

    # Log de gatilhos disparados
    "trigger_log_file": "trigger_log.csv",
    "enable_trigger_log": True,

    # Log de Tier1 detalhado (B3 diretos a cada ciclo)
    "tier1_log_file": "tier1_log.csv",
    "enable_tier1_log": True,

    # Log de confluência (quantos ativos alinhados por direção)
    "confluence_log_file": "confluence_log.csv",
    "enable_confluence_log": True,

    # Log de auditoria diária (resumo do dia)
    "daily_audit_file": "daily_audit.jsonl",
    "enable_daily_audit": True,

    # Log de ajuste de pesos (quando DynamicWeights recalcula)
    "weight_adjustment_log": "weight_adjustments.csv",
    "enable_weight_adjustment_log": True,

    # Snapshot completo a cada N ciclos (para replay)
    "snapshot_log_file": "snapshot_log.jsonl",
    "enable_snapshot_log": True,
    "snapshot_every_n_cycles": 10,  # Snapshot completo a cada 10 ciclos

    # Log de resultado de operações (entrada -> saida)
    "trade_result_log": "trade_results.csv",
    "enable_trade_result_log": True,

    # Métricas de evolução do sistema
    "evolution_metrics_file": "evolution_metrics.csv",
    "enable_evolution_metrics": True,
}

# ============================================================
# VALIDACAO EMPIRICA - CORRELAÇÃO INTRADAY (v7.0)
# ============================================================
# Script para testar correlação real de cada ativo com WIN intraday
CORRELATION_VALIDATOR_CONFIG = {
    "enabled": True,
    "lookback_days": 60,          # 60 dias de dados
    "interval": "5m",             # Candles de 5 min para intraday
    "min_observations": 500,      # Mínimo de observações
    "correlation_method": "pearson",
    "lag_seconds": [0, 30, 60],   # Testar lag de 0s, 30s, 60s
    "output_file": "correlation_report.json",
    "recalc_days": 7,             # Recalcular correlações a cada 7 dias
}
