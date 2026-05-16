"""
Calendar Events - Calendario de Eventos do Mercado
====================================================
Lista de eventos importantes que afetam o mercado brasileiro.
Em dias de evento, ajusta automaticamente os pesos dos ativos
afetados e alerta o trader.

Eventos incluidos:
- COPOM / Decisoes Selic
- NFP (Non-Farm Payrolls EUA)
- FOMC
- Earnings VALE3, PETR3
- IPCA / PIB
- Abertura de mercado

v6.0 - Componente do sistema de macro scoring
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CalendarEvents:
    """
    Calendario de eventos do mercado.

    Verifica eventos do dia e retorna multiplicadores de peso
    para os ativos afetados.
    """

    # Eventos pre-definidos para 2025-2026
    # Formato: (data, nome, ativos_afetados, multiplicador)
    PREDEFINED_EVENTS = [
        # COPOM 2025
        {"date": "2025-03-19", "name": "COPOM", "assets": ["DI1_FUTURES", "IMAB11", "US10Y"], "multiplier": 1.8},
        {"date": "2025-05-07", "name": "COPOM", "assets": ["DI1_FUTURES", "IMAB11", "US10Y"], "multiplier": 1.8},
        {"date": "2025-06-18", "name": "COPOM", "assets": ["DI1_FUTURES", "IMAB11", "US10Y"], "multiplier": 1.8},
        {"date": "2025-07-30", "name": "COPOM", "assets": ["DI1_FUTURES", "IMAB11", "US10Y"], "multiplier": 1.8},
        {"date": "2025-09-17", "name": "COPOM", "assets": ["DI1_FUTURES", "IMAB11", "US10Y"], "multiplier": 1.8},
        {"date": "2025-11-05", "name": "COPOM", "assets": ["DI1_FUTURES", "IMAB11", "US10Y"], "multiplier": 1.8},
        {"date": "2025-12-10", "name": "COPOM", "assets": ["DI1_FUTURES", "IMAB11", "US10Y"], "multiplier": 1.8},
        # NFP (primeira sexta de cada mes)
        {"date": "2025-06-06", "name": "NFP", "assets": ["DXY", "ES_FUTURES", "VIX", "USDBRL"], "multiplier": 1.5},
        {"date": "2025-07-04", "name": "NFP", "assets": ["DXY", "ES_FUTURES", "VIX", "USDBRL"], "multiplier": 1.5},
        {"date": "2025-08-01", "name": "NFP", "assets": ["DXY", "ES_FUTURES", "VIX", "USDBRL"], "multiplier": 1.5},
        {"date": "2025-09-05", "name": "NFP", "assets": ["DXY", "ES_FUTURES", "VIX", "USDBRL"], "multiplier": 1.5},
        {"date": "2025-10-03", "name": "NFP", "assets": ["DXY", "ES_FUTURES", "VIX", "USDBRL"], "multiplier": 1.5},
        {"date": "2025-11-07", "name": "NFP", "assets": ["DXY", "ES_FUTURES", "VIX", "USDBRL"], "multiplier": 1.5},
        {"date": "2025-12-05", "name": "NFP", "assets": ["DXY", "ES_FUTURES", "VIX", "USDBRL"], "multiplier": 1.5},
        # FOMC
        {"date": "2025-06-18", "name": "FOMC", "assets": ["DXY", "US10Y", "ES_FUTURES", "VIX"], "multiplier": 1.6},
        {"date": "2025-07-30", "name": "FOMC", "assets": ["DXY", "US10Y", "ES_FUTURES", "VIX"], "multiplier": 1.6},
        {"date": "2025-09-17", "name": "FOMC", "assets": ["DXY", "US10Y", "ES_FUTURES", "VIX"], "multiplier": 1.6},
        {"date": "2025-12-10", "name": "FOMC", "assets": ["DXY", "US10Y", "ES_FUTURES", "VIX"], "multiplier": 1.6},
    ]

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._custom_events = list(self.config.get("events", []))
        self._all_events = self.PREDEFINED_EVENTS + self._custom_events
        logger.info(f"CalendarEvents inicializado: {len(self._all_events)} eventos carregados")

    def get_today_events(self, target_date: date = None) -> List[Dict]:
        """Retorna eventos do dia."""
        if not self.enabled:
            return []
        target_date = target_date or date.today()
        target_str = target_date.strftime("%Y-%m-%d")
        return [e for e in self._all_events if e.get("date") == target_str]

    def get_weight_multipliers(self, target_date: date = None) -> Dict[str, float]:
        """Retorna multiplicadores de peso para os ativos afetados hoje."""
        events = self.get_today_events(target_date)
        multipliers = {}
        for event in events:
            for asset in event.get("assets", []):
                current = multipliers.get(asset, 1.0)
                multipliers[asset] = max(current, event.get("multiplier", 1.0))
        return multipliers

    def has_events_today(self, target_date: date = None) -> bool:
        return len(self.get_today_events(target_date)) > 0

    def get_event_summary(self, target_date: date = None) -> Dict:
        events = self.get_today_events(target_date)
        multipliers = self.get_weight_multipliers(target_date)
        return {
            "date": (target_date or date.today()).strftime("%Y-%m-%d"),
            "events_count": len(events),
            "events": events,
            "weight_multipliers": multipliers,
            "has_events": len(events) > 0,
        }

    def add_event(self, event_date: str, name: str, assets: list, multiplier: float = 1.5):
        """Adiciona evento customizado."""
        self._all_events.append({
            "date": event_date, "name": name,
            "assets": assets, "multiplier": multiplier,
        })

    def get_status(self) -> Dict:
        return {
            "enabled": self.enabled,
            "total_events": len(self._all_events),
            "today_events": len(self.get_today_events()),
        }
