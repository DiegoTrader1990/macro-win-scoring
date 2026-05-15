"""
Utilitários diversos para o sistema.
"""

import re
from datetime import datetime


def format_change(value: float, decimals: int = 2) -> str:
    """Formata variação com sinal e cores."""
    if value is None:
        return "N/A"
    if value > 0:
        return f"+{value:.{decimals}f}%"
    elif value < 0:
        return f"{value:.{decimals}f}%"
    return f"{value:.{decimals}f}%"


def format_price(value: float, decimals: int = 2) -> str:
    """Formata preço."""
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def get_change_color(value: float) -> str:
    """Retorna cor baseada na variação."""
    if value is None:
        return "#9E9E9E"
    elif value > 0:
        return "#00C853"
    elif value < 0:
        return "#D50000"
    return "#FFC107"


def get_score_color(score: float) -> str:
    """Retorna cor baseada no score."""
    if score >= 60:
        return "#00C853"
    elif score >= 30:
        return "#4CAF50"
    elif score > -30:
        return "#FFC107"
    elif score > -60:
        return "#FF5722"
    else:
        return "#D50000"


def get_score_bar(score: float, width: int = 20) -> str:
    """Retorna barra visual do score."""
    normalized = int((score + 100) / 200 * width)
    normalized = max(0, min(width, normalized))
    bar = "█" * normalized + "░" * (width - normalized)
    return f"[{bar}]"


def is_trading_hours() -> bool:
    """Verifica se está em horário de trading B3."""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    current_time = hour * 60 + minute
    
    # B3: 10:00 - 17:30 (compreendendo 9:00-10:00 como leilão)
    trading_start = 10 * 60  # 10:00
    trading_end = 17 * 60 + 30  # 17:30
    
    weekday = now.weekday()
    
    return weekday < 5 and trading_start <= current_time <= trading_end


def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos de nome de arquivo."""
    return re.sub(r'[^\w\-_.]', '_', name)
