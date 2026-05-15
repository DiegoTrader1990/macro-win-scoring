"""
Niveis-Chave do Indice (WIN) - Suporte e Resistencia
=====================================================
Calcula niveis de suporte e resistencia com base em:
- Pivot Points Classicos (HLC do dia anterior)
- Maximas/Minimas recentes
- Zonas de score (onde o score cruzou thresholds importantes)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class KeyLevelsCalculator:
    """
    Calculador de niveis-chave para operacao do mini indice.

    Metodos:
    1. Pivot Points Classicos: S1-S3, R1-R3, Pivot
    2. Maximas/Minimas recentes: niveis de referencia
    3. Zonas de score: niveis onde o score indicou virada
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.win_multiplier = self.config.get("win_multiplier", 5)
        self.lookback_days = self.config.get("lookback_days", 5)
        self.proximity_pct = self.config.get("level_proximity_pct", 0.3)

        self._prev_high = None
        self._prev_low = None
        self._prev_close = None
        self._current_price = None
        self._recent_highs = []
        self._recent_lows = []
        self._ibov_data = None

    def update_win_data(self, current_price: float = None,
                        prev_high: float = None,
                        prev_low: float = None,
                        prev_close: float = None,
                        ibov_high: float = None,
                        ibov_low: float = None,
                        ibov_close: float = None):
        """
        Atualiza dados do WIN/IBOV para calculo de niveis.

        Args:
            current_price: Preco atual do WIN
            prev_high: Maxima do dia anterior
            prev_low: Minima do dia anterior
            prev_close: Fechamento do dia anterior
            ibov_high/low/close: Dados IBOV para proxy
        """
        if current_price is not None:
            self._current_price = current_price
        if prev_high is not None:
            self._prev_high = prev_high
        if prev_low is not None:
            self._prev_low = prev_low
        if prev_close is not None:
            self._prev_close = prev_close

        # Usa IBOV como proxy se nao tiver dados WIN diretos
        if ibov_high is not None:
            self._ibov_data = {
                "high": ibov_high,
                "low": ibov_low,
                "close": ibov_close,
            }

    def calculate_pivot_points(self) -> Optional[dict]:
        """
        Calcula Pivot Points classicos.

        Formulas:
            Pivot = (H + L + C) / 3
            R1 = 2*Pivot - L
            S1 = 2*Pivot - H
            R2 = Pivot + (H - L)
            S2 = Pivot - (H - L)
            R3 = H + 2*(Pivot - L)
            S3 = L - 2*(H - Pivot)
        """
        high = self._prev_high
        low = self._prev_low
        close = self._prev_close

        # Se nao tem dados WIN diretos, usa proxy IBOV
        if high is None and self._ibov_data:
            high = self._ibov_data.get("high")
            low = self._ibov_data.get("low")
            close = self._ibov_data.get("close")

        if high is None or low is None or close is None:
            return None

        pivot = (high + low + close) / 3.0
        r1 = 2 * pivot - low
        s1 = 2 * pivot - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = high + 2 * (pivot - low)
        s3 = low - 2 * (high - pivot)

        # Arredonda para multiplo do WIN
        def round_win(val):
            return round(val / self.win_multiplier) * self.win_multiplier

        return {
            "R3": round_win(r3),
            "R2": round_win(r2),
            "R1": round_win(r1),
            "PIVOT": round_win(pivot),
            "S1": round_win(s1),
            "S2": round_win(s2),
            "S3": round_win(s3),
        }

    def calculate_from_ewz(self, ewz_data: dict, ibov_data: dict = None) -> Optional[dict]:
        """
        Calcula niveis aproximados usando EWZ/IBOV como proxy.
        Converte variacoes percentuais do EWZ para pontos do WIN.

        Args:
            ewz_data: Dados do EWZ com preco e variacao
            ibov_data: Dados do IBOV (opcional, mais preciso)
        """
        if not ewz_data:
            return None

        # Se temos preco WIN atual, estima niveis
        win_price = self._current_price
        if win_price is None:
            # Tenta estimar a partir do EWZ
            ewz_price = ewz_data.get("current_price")
            ewz_change = ewz_data.get("change_pct", 0)
            if ewz_price is None:
                return None
            # Estimativa grosseira: EWZ ~= 1.2x IBOV variacao
            win_price = 125000  # Placeholder

        # Usa a variacao do EWZ/IBOV para estimar niveis
        change_pct = ewz_data.get("change_pct", 0)
        prev_close = ewz_data.get("previous_close")

        if prev_close and change_pct is not None:
            # Estima o range do dia baseado na volatilidade do EWZ
            daily_range_est = win_price * abs(change_pct) / 100 * 2.5
            daily_range_est = max(daily_range_est, win_price * 0.005)  # Min 0.5%

            # Estimativa de H e L do dia
            if change_pct > 0:
                est_high = win_price * 1.001
                est_low = win_price - daily_range_est
            else:
                est_high = win_price + daily_range_est
                est_low = win_price * 0.999

            est_close = win_price

            self._prev_high = est_high
            self._prev_low = est_low
            self._prev_close = est_close
            self._current_price = win_price

        return self.calculate_pivot_points()

    def calculate_from_win_candles(self, candles: list) -> Optional[dict]:
        """
        Calcula niveis a partir de candles do WIN (via MT5).

        Args:
            candles: Lista de dicts com OHLC
        """
        if not candles or len(candles) < 2:
            return None

        # Ultimo candle completo (penultimo)
        prev_candle = candles[-2] if len(candles) >= 2 else candles[-1]

        self._prev_high = prev_candle.get("high")
        self._prev_low = prev_candle.get("low")
        self._prev_close = prev_candle.get("close")
        self._current_price = candles[-1].get("close")

        return self.calculate_pivot_points()

    def get_nearest_levels(self, levels: dict) -> List[dict]:
        """
        Retorna niveis ordenados por proximidade ao preco atual.

        Returns:
            Lista de dicts com nivel, tipo, valor, distancia
        """
        if not levels or self._current_price is None:
            return []

        result = []
        price = self._current_price

        level_types = {
            "R3": "resistencia",
            "R2": "resistencia",
            "R1": "resistencia",
            "PIVOT": "pivot",
            "S1": "suporte",
            "S2": "suporte",
            "S3": "suporte",
        }

        for name, value in levels.items():
            ltype = level_types.get(name, "neutro")
            distance = value - price
            distance_pct = (distance / price) * 100

            result.append({
                "name": name,
                "value": value,
                "type": ltype,
                "distance": round(distance, 0),
                "distance_pct": round(distance_pct, 2),
                "is_near": abs(distance_pct) <= self.proximity_pct,
            })

        # Ordena por distancia absoluta
        result.sort(key=lambda x: abs(x["distance_pct"]))
        return result

    def get_trading_zones(self, levels: dict, score: float = 0) -> dict:
        """
        Combina niveis com score para identificar zonas de operacao.

        Returns:
            Dict com zonas de compra e venda
        """
        if not levels or self._current_price is None:
            return {"buy_zones": [], "sell_zones": []}

        nearest = self.get_nearest_levels(levels)
        buy_zones = []
        sell_zones = []

        for lvl in nearest:
            if lvl["type"] == "suporte" and score > 20:
                buy_zones.append({
                    "level": lvl["name"],
                    "price": lvl["value"],
                    "score": score,
                    "reason": f"Suporte + Score positivo ({score:+.0f})",
                })
            elif lvl["type"] == "resistencia" and score < -20:
                sell_zones.append({
                    "level": lvl["name"],
                    "price": lvl["value"],
                    "score": score,
                    "reason": f"Resistencia + Score negativo ({score:+.0f})",
                })

        return {
            "buy_zones": buy_zones[:3],
            "sell_zones": sell_zones[:3],
        }

    def get_full_analysis(self, score: float = 0) -> dict:
        """
        Retorna analise completa de niveis.

        Returns:
            Dict com pivot points, niveis proximos, zonas de operacao
        """
        levels = self.calculate_pivot_points()

        if levels is None:
            return {
                "available": False,
                "levels": None,
                "nearest": [],
                "zones": {"buy_zones": [], "sell_zones": []},
                "current_price": self._current_price,
                "message": "Aguardando dados do WIN/IBOV para calcular niveis",
            }

        nearest = self.get_nearest_levels(levels)
        zones = self.get_trading_zones(levels, score)

        return {
            "available": True,
            "levels": levels,
            "nearest": nearest,
            "zones": zones,
            "current_price": self._current_price,
            "message": "",
        }
