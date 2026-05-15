"""
Configuração do Sistema de Macro Scoring para Mini Índice (WIN)
================================================================
Todos os ativos, pesos, thresholds e parâmetros configuráveis.
Pesos baseados nas correlações validadas com dados reais (60 dias).
"""

# ============================================================
# CONFIGURAÇÃO DO MT5 (CORRETORA RICO)
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
}

DUAL_SOURCE_ASSETS = {
    "VALE3":  {"mt5": "VALE3", "yf": "VALE3.SA"},
    "PETR4":  {"mt5": "PETR4", "yf": "PETR4.SA"},
    "IFNC":   {"mt5": "IFNC",  "yf": "IFNC.SA"},
    "IMAT":   {"mt5": "IMAT",  "yf": "IMAT.SA"},
    "ICON":   {"mt5": "ICON",  "yf": "ICON.SA"},
    "IMAB11": {"mt5": "IMAB11","yf": "IMAB11.SA"},
    "BOVA11": {"mt5": "BOVA11","yf": "BOVA11.SA"},
}

# ============================================================
# TRACKING DO WIN PARA DIVERGÊNCIA
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
# THRESHOLDS E PARÂMETROS DE SINAL
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
}

# ============================================================
# CATEGORIAS PARA O DASHBOARD
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
# CONFIGURAÇÃO DO DASHBOARD
# ============================================================
DASHBOARD_CONFIG = {
    "width": 600,
    "height": 1000,
    "theme": "dark",
    "compact_mode": True,
    "sidebar_collapsed": True,
}

# ============================================================
# CONFIGURAÇÃO DE INTERFACE (UI) - AJUSTÁVEL
# ============================================================
UI_CONFIG = {
    # ---- PAINEL ----
    "panel_width": 580,                    # Largura máxima do painel (px)
    "panel_padding": 8,                    # Padding lateral (px)

    # ---- FONTES ----
    "font_family_data": "'Consolas', 'JetBrains Mono', 'Courier New', monospace",
    "font_family_ui": "'Segoe UI', 'Inter', 'Helvetica Neue', Arial, sans-serif",

    # Score principal
    "score_font_size": 48,                 # Tamanho do número do score (px)
    "score_label_font_size": 11,           # Label do sinal (px)
    "score_glow": True,                    # Efeito glow no score

    # Metric strip
    "metric_value_font_size": 15,          # Valor das métricas (px)
    "metric_label_font_size": 8,           # Label das métricas (px)

    # Signal banner
    "signal_font_size": 13,                # Texto do sinal (px)
    "signal_action_font_size": 9,          # Texto da ação (px)

    # Categorias
    "category_font_size": 11,              # Nome da categoria (px)
    "category_score_font_size": 12,        # Score da categoria (px)
    "category_bar_height": 5,              # Altura da barra (px)
    "category_bar_width": 140,             # Largura da barra (px)

    # Tabela de ativos
    "asset_table_header_size": 8,          # Header da tabela (px)
    "asset_table_row_size": 10,            # Linha da tabela (px)
    "asset_name_width": 90,               # Largura coluna nome (px)
    "asset_price_width": 75,              # Largura coluna preço (px)
    "asset_change_width": 65,             # Largura coluna variação (px)
    "asset_contrib_width": 60,            # Largura coluna contribuição (px)
    "asset_dir_width": 30,               # Largura coluna direção (px)
    "asset_row_height": 22,              # Altura da linha (px)

    # Divergência
    "divergence_font_size": 10,
    "divergence_desc_size": 8,

    # Header
    "header_title_size": 11,
    "header_status_size": 9,

    # Gráfico histórico
    "chart_height": 130,

    # ---- CORES ----
    "bg_primary": "#080c12",              # Fundo principal
    "bg_secondary": "#0d1420",            # Fundo cards
    "bg_tertiary": "#111a28",             # Fundo hover/alt
    "border_color": "#1a2535",            # Bordas
    "border_light": "#243040",            # Bordas mais claras
    "text_primary": "#d0d8e0",            # Texto principal
    "text_secondary": "#6b7d8e",          # Texto secundário
    "text_muted": "#3a4a5a",              # Texto mudo
    "accent": "#4fc3f7",                  # Cor de destaque
    "positive": "#00E676",                # Positivo
    "negative": "#FF1744",                # Negativo
    "warning": "#FFD600",                 # Alerta
    "neutral": "#78909C",                 # Neutro
}

# ============================================================
# CONFIGURAÇÃO DE DIVERGÊNCIA
# ============================================================
DIVERGENCE_CONFIG = {
    "enabled": True,
    "divergence_periods": 20,
    "divergence_min_periods": 5,
    "divergence_score_threshold": 3,
    "divergence_win_threshold_pct": 0.1,
}

# ============================================================
# CONFIGURAÇÃO DE LOGS
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
# PARÂMETROS DE BACKTEST / VALIDAÇÃO
# ============================================================
BACKTEST_CONFIG = {
    "benchmark": "BOVA11",
    "initial_capital": 100000,
    "position_size": 1,
    "stop_loss_points": 200,
    "take_profit_points": 400,
}
