"""
Utilitarios diversos para o sistema.
Inclui funcoes de formatacao, verificacao de horario,
e deteccao dinamica de contratos WIN/WDO.
"""

import re
from datetime import datetime
from typing import Optional

# Codigos de mes para contratos futuros da B3
# Usado pela BM&F para nomear contratos: F=Jan, G=Fev, H=Mar, etc.
MONTH_CODES = {
    1: "F", 2: "G", 3: "H", 4: "J",
    5: "K", 6: "M", 7: "N", 8: "Q",
    9: "U", 10: "V", 11: "X", 12: "Z",
}


def format_change(value: float, decimals: int = 2) -> str:
    """Formata variacao com sinal e cores."""
    if value is None:
        return "N/A"
    if value > 0:
        return f"+{value:.{decimals}f}%"
    elif value < 0:
        return f"{value:.{decimals}f}%"
    return f"{value:.{decimals}f}%"


def format_price(value: float, decimals: int = 2) -> str:
    """Formata preco."""
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def get_change_color(value: float) -> str:
    """Retorna cor baseada na variacao."""
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
    bar = "\u2588" * normalized + "\u2591" * (width - normalized)
    return f"[{bar}]"


def is_trading_hours() -> bool:
    """Verifica se esta em horario de trading B3."""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    current_time = hour * 60 + minute
    
    # B3: 10:00 - 17:30 (compreendendo 9:00-10:00 como leilao)
    trading_start = 10 * 60  # 10:00
    trading_end = 17 * 60 + 30  # 17:30
    
    weekday = now.weekday()
    
    return weekday < 5 and trading_start <= current_time <= trading_end


def sanitize_filename(name: str) -> str:
    """Remove caracteres invalidos de nome de arquivo."""
    return re.sub(r'[^\w\-_.]', '_', name)


def get_active_win_contract(date: datetime = None, roll_days_before: int = 3) -> str:
    """
    Retorna o codigo do contrato WIN ativo baseado na data.

    A logica considera o contrato do mes mais proximo que ainda nao
    venceu. Contratos de indice na B3 vencem na terceira sexta-feira
    do mes de vencimento. Roll days antes do vencimento, o contrato
    seguinte passa a ser o ativo.

    Exemplos:
        - Maio 2025 → WINK25
        - Janeiro 2025 → WINF25
        - Dezembro 2025 → WINZ25

    Args:
        date: Data de referencia (default: agora).
        roll_days_before: Dias antes do vencimento para trocar de contrato.

    Returns:
        Codigo do contrato ativo (ex: "WINK25").
    """
    return _get_active_futures_contract(
        prefix="WIN",
        date=date,
        roll_days_before=roll_days_before,
    )


def get_active_wdo_contract(date: datetime = None, roll_days_before: int = 3) -> str:
    """
    Retorna o codigo do contrato WDO ativo baseado na data.

    Mesma logica do WIN, mas com prefixo WDO (mini dolar).

    Exemplos:
        - Maio 2025 → WDOK25
        - Janeiro 2025 → WDOF25

    Args:
        date: Data de referencia (default: agora).
        roll_days_before: Dias antes do vencimento para trocar de contrato.

    Returns:
        Codigo do contrato ativo (ex: "WDOK25").
    """
    return _get_active_futures_contract(
        prefix="WDO",
        date=date,
        roll_days_before=roll_days_before,
    )


def _get_active_futures_contract(prefix: str, date: datetime = None,
                                  roll_days_before: int = 3) -> str:
    """
    Calcula o codigo do contrato futuro ativo para um dado prefixo.

    Logica de vencimento B3:
    - O contrato vence na terceira sexta-feira do mes.
    - roll_days_before dias antes do vencimento, o contrato seguinte
      torna-se o contrato ativo (para evitar problemas de liquidez).

    Se a data atual esta apos o roll date do mes atual, usa o contrato
    do mes seguinte. Caso contrario, usa o contrato do mes atual.

    Args:
        prefix: Prefixo do contrato ("WIN" ou "WDO").
        date: Data de referencia (default: agora).
        roll_days_before: Dias antes do vencimento para roll.

    Returns:
        Codigo do contrato (ex: "WINK25").
    """
    date = date or datetime.now()
    year = date.year
    month = date.month

    # Calcula a terceira sexta-feira do mes atual
    third_friday = _get_third_friday(year, month)

    # Roll date: alguns dias antes do vencimento
    from datetime import timedelta
    roll_date = third_friday - timedelta(days=roll_days_before)

    # Se ja passamos do roll date, usar o proximo mes
    if date.date() >= roll_date.date():
        # Proximo mes
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1

    # Obtem o codigo do mes
    month_code = MONTH_CODES.get(month, "Z")

    # Ano com 2 digitos
    year_code = str(year)[-2:]

    # Monta o codigo do contrato
    contract = f"{prefix}{month_code}{year_code}"

    return contract


def _get_third_friday(year: int, month: int) -> datetime:
    """
    Calcula a data da terceira sexta-feira de um dado mes/ano.

    Metodo:
    1. Encontra o dia da semana do dia 1 do mes
    2. Calcula quantos dias ate a primeira sexta-feira
    3. Adiciona 14 dias (2 semanas) para chegar na terceira

    Args:
        year: Ano.
        month: Mes (1-12).

    Returns:
        DateTime da terceira sexta-feira do mes.
    """
    from datetime import timedelta

    # Dia 1 do mes
    first_day = datetime(year, month, 1)

    # Dia da semana do dia 1 (0=segunda, 4=sexta)
    weekday = first_day.weekday()

    # Dias ate a primeira sexta-feira
    if weekday <= 4:  # Segunda a sexta
        days_to_friday = 4 - weekday
    else:  # Sabado ou domingo
        days_to_friday = 11 - weekday  # Proxima sexta

    first_friday = first_day + timedelta(days=days_to_friday)

    # Terceira sexta-feira = primeira + 14 dias
    third_friday = first_friday + timedelta(days=14)

    return third_friday
