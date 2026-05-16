"""
Structural Context - VWAP + Initial Balance + Value Area
=========================================================
Fornece contexto estrutural do dia: VWAP, Initial Balance,
Value Area do dia anterior e posicao do preco relativo a esses
niveis. Essencial para day trading do WIN.

v6.0 - Componente do sistema de macro scoring
"""

import logging
from datetime import datetime, time
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class StructuralContext:
    """
    Contexto estrutural intraday para o WIN.

    Calcula VWAP, Initial Balance e posicao relativa ao Value Area
    do dia anterior. Usa dados de preco do WIN (MT5 ou proxy).
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.ib_start_hour = self.config.get("ib_start_hour", 9)
        self.ib_end_hour = self.config.get("ib_end_hour", 10)
        self.va_lookback = self.config.get("va_lookback_days", 5)
        self._candles: List[Dict] = []
        self._vwap_value: Optional[float] = None
        self._vwap_upper: Optional[float] = None
        self._vwap_lower: Optional[float] = None
        self._ib_high: Optional[float] = None
        self._ib_low: Optional[float] = None
        self._ib_range: Optional[float] = None
        self._prev_vah: Optional[float] = None
        self._prev_val: Optional[float] = None
        self._current_price: Optional[float] = None
        self._cum_tp_vol = 0.0
        self._cum_vol = 0.0
        self._cum_tp2_vol = 0.0
        self._session_date: Optional[str] = None
        self._max_candles = 2000
        logger.info(f"StructuralContext inicializado: enabled={self.enabled}")

    def update_candle(self, high: float, low: float, close: float,
                      volume: float = 1.0, timestamp: datetime = None) -> None:
        """Adiciona candle intraday para calculo do VWAP."""
        if not self.enabled:
            return
        timestamp = timestamp or datetime.now()
        today_str = timestamp.strftime("%Y-%m-%d")

        # Reset na mudanca de dia
        if self._session_date != today_str:
            self._session_date = today_str
            self._cum_tp_vol = 0.0
            self._cum_vol = 0.0
            self._cum_tp2_vol = 0.0
            self._ib_high = None
            self._ib_low = None

        tp = (high + low + close) / 3.0
        self._cum_tp_vol += tp * volume
        self._cum_vol += volume
        self._cum_tp2_vol += tp * tp * volume
        self._current_price = close

        # VWAP
        if self._cum_vol > 0:
            self._vwap_value = self._cum_tp_vol / self._cum_vol
            variance = (self._cum_tp2_vol / self._cum_vol) - (self._vwap_value ** 2)
            std_dev = max(0, variance) ** 0.5
            self._vwap_upper = self._vwap_value + std_dev
            self._vwap_lower = self._vwap_value - std_dev

        # Initial Balance (9h-10h)
        hour = timestamp.hour
        if self.ib_start_hour <= hour < self.ib_end_hour:
            if self._ib_high is None or high > self._ib_high:
                self._ib_high = high
            if self._ib_low is None or low < self._ib_low:
                self._ib_low = low
            if self._ib_high is not None and self._ib_low is not None:
                self._ib_range = self._ib_high - self._ib_low

        # Store candle
        self._candles.append({
            "timestamp": timestamp, "high": high, "low": low,
            "close": close, "volume": volume,
        })
        if len(self._candles) > self._max_candles:
            self._candles = self._candles[-self._max_candles:]

    def set_prev_value_area(self, vah: float, val: float) -> None:
        """Define o Value Area do dia anterior (calculado externamente)."""
        self._prev_vah = vah
        self._prev_val = val

    def calculate_from_daily_data(self, daily_data: list) -> None:
        """
        Calcula Value Area do dia anterior a partir de dados diarios.
        daily_data: lista de dicts com 'high', 'low', 'close' dos ultimos N dias.
        """
        if not daily_data or len(daily_data) < 2:
            return
        # Usa o penultimo dia como "dia anterior"
        prev = daily_data[-2]
        # Aproximacao: VA = 70% do range do dia anterior centrado no POC
        h = prev.get("high", 0)
        l = prev.get("low", 0)
        c = prev.get("close", 0)
        if h and l:
            poc = (h + l + c) / 3.0
            range_70 = (h - l) * 0.70
            self._prev_vah = poc + range_70 / 2
            self._prev_val = poc - range_70 / 2

    def get_analysis(self) -> Dict:
        """Retorna analise estrutural completa."""
        if not self.enabled:
            return self._empty_result()

        result = {
            "enabled": True,
            "vwap": round(self._vwap_value, 2) if self._vwap_value else None,
            "vwap_upper": round(self._vwap_upper, 2) if self._vwap_upper else None,
            "vwap_lower": round(self._vwap_lower, 2) if self._vwap_lower else None,
            "current_price": self._current_price,
            "ib_high": self._ib_high,
            "ib_low": self._ib_low,
            "ib_range": self._ib_range,
            "prev_vah": self._prev_vah,
            "prev_val": self._prev_val,
            "timestamp": datetime.now(),
        }

        # Derived metrics
        if self._current_price and self._vwap_value:
            vwap_dist = self._current_price - self._vwap_value
            vwap_dist_pct = (vwap_dist / self._vwap_value) * 100 if self._vwap_value else 0
            result["vwap_distance"] = round(vwap_dist, 2)
            result["vwap_distance_pct"] = round(vwap_dist_pct, 3)
            result["above_vwap"] = self._current_price > self._vwap_value
            # VWAP position: -2 to +2 (bandas)
            if self._vwap_upper and self._vwap_lower:
                band_range = self._vwap_upper - self._vwap_lower
                if band_range > 0:
                    result["vwap_band_position"] = round(
                        (self._current_price - self._vwap_lower) / band_range * 4 - 2, 2
                    )
                else:
                    result["vwap_band_position"] = 0.0
            else:
                result["vwap_band_position"] = 0.0
        else:
            result["vwap_distance"] = None
            result["vwap_distance_pct"] = None
            result["above_vwap"] = None
            result["vwap_band_position"] = None

        # IB classification
        if self._ib_range and self._current_price:
            # Comparar IB com range atual
            if len(self._candles) > 20:
                recent_range = max(c["high"] for c in self._candles[-20:]) - \
                               min(c["low"] for c in self._candles[-20:])
                if recent_range > 0:
                    ib_expansion = self._ib_range / recent_range
                    result["ib_expansion_ratio"] = round(ib_expansion, 3)
                    result["ib_type"] = "EXPANDIDO" if ib_expansion > 0.6 else "CONTRAIDO"
                else:
                    result["ib_expansion_ratio"] = None
                    result["ib_type"] = "INDEFINIDO"
            else:
                result["ib_expansion_ratio"] = None
                result["ib_type"] = "AGUARDANDO"
        else:
            result["ib_expansion_ratio"] = None
            result["ib_type"] = "AGUARDANDO"

        # Position relative to prev VA
        if self._current_price and self._prev_vah and self._prev_val:
            if self._current_price > self._prev_vah:
                result["va_position"] = "ACIMA_VA"
            elif self._current_price < self._prev_val:
                result["va_position"] = "ABAIXO_VA"
            else:
                result["va_position"] = "DENTRO_VA"
        else:
            result["va_position"] = "INDEFINIDO"

        return result

    def _empty_result(self) -> Dict:
        return {
            "enabled": False, "vwap": None, "vwap_upper": None, "vwap_lower": None,
            "current_price": None, "ib_high": None, "ib_low": None, "ib_range": None,
            "prev_vah": None, "prev_val": None, "vwap_distance": None,
            "vwap_distance_pct": None, "above_vwap": None, "vwap_band_position": None,
            "ib_expansion_ratio": None, "ib_type": "AGUARDANDO",
            "va_position": "INDEFINIDO", "timestamp": datetime.now(),
        }

    def get_status(self) -> Dict:
        a = self.get_analysis()
        return {"enabled": self.enabled, "vwap": a.get("vwap"),
                "above_vwap": a.get("above_vwap"), "ib_type": a.get("ib_type"),
                "va_position": a.get("va_position"), "candles_count": len(self._candles)}

    def reset(self):
        self._candles = []
        self._vwap_value = None
        self._vwap_upper = None
        self._vwap_lower = None
        self._ib_high = None
        self._ib_low = None
        self._ib_range = None
        self._cum_tp_vol = 0
        self._cum_vol = 0
        self._cum_tp2_vol = 0
        self._session_date = None
        logger.info("StructuralContext resetado")
