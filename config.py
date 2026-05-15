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
    "path": r"C:\Program Files\MetaTrader 5\terminal64.exe",  # Ajuste se necessário
    "login": None,       # Seu login da Rico (preencha no .env)
    "password": None,    # Sua senha da Rico (preencha no .env)
    "server": "Rico",    # Servidor da Rico no MT5
    "timeout": 10000,
    "portable": False,
}

# ============================================================
# MAPEAMENTO DE ATIVOS - MT5
# ============================================================
# Tickers no MT5 (formato B3 para a Rico)
# IMPORTANTE: O MT5 precisa estar aberto e logado na Rico
MT5_SYMBOLS = {
    # Índice & Mini Índice
    "WIN": "WINN25",        # Mini Índice (contrato atual - ajuste o vencimento)
    "WDO": "WDON25",        # Mini Dólar (contrato atual - ajuste o vencimento)
    
    # Ações Brasileiras
    "VALE3": "VALE3",
    "PETR4": "PETR4",
    "ITUB4": "ITUB4",
    "BBDC4": "BBDC4",
    "PETR3": "PETR3",
    
    # ETFs Setoriais
    "IFNC": "IFNC",
    "IMAT": "IMAT",
    "ICON": "ICON",
    "BOVA11": "BOVA11",
    "SMALL11": "SMALL11",
    
    # Renda Fixa / Juros
    "IMAB11": "IMAB11",
}

# ============================================================
# MAPEAMENTO DE ATIVOS - YAHOO FINANCE
# ============================================================
# Tickers no Yahoo Finance para ativos macro internacionais
YF_SYMBOLS = {
    # Índices Internacionais
    "SP500": "^GSPC",              # S&P 500
    "ES_FUTURES": "ES=F",          # S&P 500 Futures (E-mini)
    "NASDAQ": "^IXIC",             # Nasdaq Composite
    "DAX": "^GDAXI",               # DAX (Alemanha)
    "EUROSTOXX50": "^STOXX50E",    # Euro Stoxx 50
    "NIKKEI": "^N225",             # Nikkei 225 (Japão)
    
    # Volatilidade
    "VIX": "^VIX",                 # VIX (Volatilidade implícita)
    
    # Moedas
    "DXY": "DX-Y.NYB",            # Dólar Index (DXY)
    "USDBRL": "BRL=X",            # USD/BRL spot
    
    # Commodities
    "IRON_ORE": "SI=F",            # Iron Ore Futures
    "BRENT": "BZ=F",              # Brent Crude Oil
    "WTI": "CL=F",                # WTI Crude Oil
    "COPPER": "HG=F",             # Copper Futures
    "GOLD": "GC=F",               # Gold Futures
    
    # Taxas / Títulos
    "US10Y": "^TNX",              # US 10-Year Treasury Yield
    "US2Y": "^IRX",               # US 2-Year Treasury Yield (proxy)
    
    # Crypto
    "BITCOIN": "BTC-USD",         # Bitcoin
    
    # ADRs Brasileiras
    "VALE_ADR": "VALE",           # VALE ADR (NYSE)
    "PETR_ADR": "PBR",            # Petrobras ADR (NYSE)
    "EWZ": "EWZ",                 # iShares Brazil ETF
}

# Ativos que tentamos primeiro no MT5, depois Yahoo Finance como fallback
# Chave = nome interno, Valor MT5 = símbolo MT5, Valor YF = símbolo YF
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
# PESOS DO SCORING MACRO
# ============================================================
# Baseados nas correlações validadas (estudo com dados reais 60 dias)
# Peso = |correlação| normalizada para somar 100%
# Sinal: +1 = correlação direta, -1 = correlação inversa

MACRO_WEIGHTS = {
    # ---- ALTO IMPACTO (correlação > 0.50) ----
    "EWZ":         {"weight": 0.12, "direction": +1, "corr": 0.96, "category": "Fluxo Estrangeiro"},
    "VALE_ADR":    {"weight": 0.10, "direction": +1, "corr": 0.75, "category": "ADRs/Overnight"},
    "VIX":         {"weight": 0.09, "direction": -1, "corr": -0.63, "category": "Volatilidade"},
    "DXY":         {"weight": 0.08, "direction": -1, "corr": -0.57, "category": "Moedas"},
    "ES_FUTURES":  {"weight": 0.08, "direction": +1, "corr": 0.57, "category": "Índices Globais"},
    "EUROSTOXX50": {"weight": 0.07, "direction": +1, "corr": 0.53, "category": "Índices Globais"},
    "IMAB11":      {"weight": 0.07, "direction": +1, "corr": 0.56, "category": "Juros/Renda Fixa"},
    
    # ---- IMPACTO MÉDIO (correlação 0.30-0.50) ----
    "DAX":         {"weight": 0.05, "direction": +1, "corr": 0.49, "category": "Índices Globais"},
    "US10Y":       {"weight": 0.05, "direction": -1, "corr": -0.48, "category": "Juros/Renda Fixa"},
    "WTI":         {"weight": 0.04, "direction": -1, "corr": -0.50, "category": "Commodities"},
    "SP500":       {"weight": 0.04, "direction": +1, "corr": 0.45, "category": "Índices Globais"},
    "COPPER":      {"weight": 0.04, "direction": +1, "corr": 0.44, "category": "Commodities"},
    "BITCOIN":     {"weight": 0.03, "direction": +1, "corr": 0.41, "category": "Risk Appetite"},
    "NIKKEI":      {"weight": 0.03, "direction": +1, "corr": 0.35, "category": "Índices Globais"},
    "IFNC":        {"weight": 0.03, "direction": +1, "corr": 0.40, "category": "Setorial BR"},
    "WDO":         {"weight": 0.03, "direction": -1, "corr": -0.35, "category": "Moedas"},
    "BRENT":       {"weight": 0.02, "direction": -1, "corr": -0.30, "category": "Commodities"},
    
    # ---- IMPACTO BAIXO MAS RELEVANTE ----
    "IMAT":        {"weight": 0.01, "direction": +1, "corr": 0.25, "category": "Setorial BR"},
    "IRON_ORE":    {"weight": 0.01, "direction": +1, "corr": 0.20, "category": "Commodities"},
    "PETR_ADR":    {"weight": 0.01, "direction": +1, "corr": 0.22, "category": "ADRs/Overnight"},
}

# ============================================================
# THRESHOLDS E PARÂMETROS DE SINAL
# ============================================================
SIGNAL_CONFIG = {
    # Score vai de -100 a +100
    "strong_bullish": 60,     # Score >= 60: Forte tendência de alta
    "moderate_bullish": 30,   # Score >= 30: Moderada tendência de alta
    "neutral_low": -30,       # Score entre -30 e +30: Neutro/Zona de cautela
    "moderate_bearish": -30,  # Score <= -30: Moderada tendência de baixa
    "strong_bearish": -60,    # Score <= -60: Forte tendência de baixa
    
    # Delta (variação do score)
    "delta_acceleration": 15,  # Delta > 15: Aceleração do movimento
    "delta_deceleration": -15, # Delta < -15: Desaceleração/reversão
    
    # Períodos de referência para variação percentual
    "var_periods": {
        "intraday": 0,        # Variação do dia (vs fechamento anterior)
        "short_term": 5,      # 5 pregões
        "medium_term": 21,    # 21 pregões (~1 mês)
    },
    
    # Intervalo de atualização (segundos)
    "refresh_interval": 30,
    
    # Horário de trading
    "trading_start": "09:00",  # Abertura B3
    "trading_end": "17:30",    # Fechamento B3
    "pre_market_start": "09:00",
}

# ============================================================
# CATEGORIAS PARA O DASHBOARD
# ============================================================
CATEGORIES = {
    "Índices Globais": {
        "icon": "🌍",
        "color": "#2196F3",
        "assets": ["ES_FUTURES", "SP500", "EUROSTOXX50", "DAX", "NIKKEI"]
    },
    "Volatilidade": {
        "icon": "⚡",
        "color": "#FF5722",
        "assets": ["VIX"]
    },
    "Moedas": {
        "icon": "💱",
        "color": "#4CAF50",
        "assets": ["DXY", "WDO", "USDBRL"]
    },
    "Commodities": {
        "icon": "⛏️",
        "color": "#FF9800",
        "assets": ["IRON_ORE", "BRENT", "WTI", "COPPER", "GOLD"]
    },
    "Juros/Renda Fixa": {
        "icon": "📊",
        "color": "#9C27B0",
        "assets": ["US10Y", "IMAB11"]
    },
    "ADRs/Overnight": {
        "icon": "🇺🇸",
        "color": "#00BCD4",
        "assets": ["VALE_ADR", "PETR_ADR", "EWZ"]
    },
    "Risk Appetite": {
        "icon": "🎲",
        "color": "#E91E63",
        "assets": ["BITCOIN"]
    },
    "Setorial BR": {
        "icon": "🇧🇷",
        "color": "#8BC34A",
        "assets": ["IFNC", "IMAT", "ICON"]
    },
}

# ============================================================
# PARÂMETROS DE BACKTEST / VALIDAÇÃO
# ============================================================
BACKTEST_CONFIG = {
    "benchmark": "BOVA11",     # Benchmark para comparação
    "initial_capital": 100000, # Capital inicial simulado
    "position_size": 1,        # Número de contratos WIN
    "stop_loss_points": 200,   # Stop loss em pontos
    "take_profit_points": 400, # Take profit em pontos
}
