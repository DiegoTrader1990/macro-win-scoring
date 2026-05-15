"""
Detecção de Divergência - Score Macro vs Preço WIN
====================================================
Compara a direção do score macro com o preço real do WIN.
Divergências indicam que o movimento do WIN pode não ser sustentável
pelo cenário macro, sinalizando possível reversão ou armadilha.

Tipos:
- CONVERGÊNCIA: Score e WIN na mesma direção (confirmação)
- DIVERGÊNCIA ALTA: Score subindo + WIN caindo (WIN pode subir)
- DIVERGÊNCIA BAIXA: Score caindo + WIN subindo (WIN pode cair)
- NEUTRO: Sem direção clara em ambos
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class DivergenceDetector:
    """
    Detector de divergência entre Score Macro e Preço WIN.
    
    Metodologia:
    1. Armazena histórico de scores e preços WIN
    2. Calcula a tendência de cada um (regressão linear simples)
    3. Compara as direções
    4. Classifica o nível de divergência
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.score_history: List[dict] = []
        self.win_price_history: List[dict] = []
        self.max_history = self.config.get("divergence_periods", 20)
        self.min_periods = self.config.get("divergence_min_periods", 5)
        self.score_threshold = self.config.get("divergence_score_threshold", 3)
        self.win_threshold_pct = self.config.get("divergence_win_threshold_pct", 0.1)

    def update_score(self, score: float, timestamp: datetime = None):
        """Registra nova leitura de score."""
        timestamp = timestamp or datetime.now()
        self.score_history.append({"timestamp": timestamp, "value": score})
        if len(self.score_history) > self.max_history:
            self.score_history = self.score_history[-self.max_history:]

    def update_win_price(self, price: float, timestamp: datetime = None):
        """Registra nova leitura de preço WIN."""
        timestamp = timestamp or datetime.now()
        self.win_price_history.append({"timestamp": timestamp, "value": price})
        if len(self.win_price_history) > self.max_history:
            self.win_price_history = self.win_price_history[-self.max_history:]

    def _calc_trend(self, data: List[dict]) -> Optional[dict]:
        """
        Calcula tendência via regressão linear simples.
        
        Returns:
            Dict com slope, direction, strength ou None se dados insuficientes
        """
        if len(data) < self.min_periods:
            return None

        values = [d["value"] for d in data]
        n = len(values)
        x = list(range(n))

        # Regressão linear: y = a + bx
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(xi * yi for xi, yi in zip(x, values))
        sum_x2 = sum(xi ** 2 for xi in x)

        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return None

        slope = (n * sum_xy - sum_x * sum_y) / denominator

        # Normaliza slope para comparabilidade
        value_range = max(values) - min(values) if max(values) != min(values) else 1
        normalized_slope = slope / (value_range / n) if value_range != 0 else 0

        if normalized_slope > 0.15:
            direction = "UP"
        elif normalized_slope < -0.15:
            direction = "DOWN"
        else:
            direction = "FLAT"

        return {
            "slope": slope,
            "normalized_slope": round(normalized_slope, 4),
            "direction": direction,
            "strength": abs(normalized_slope),
            "first_value": values[0],
            "last_value": values[-1],
            "change": values[-1] - values[0],
        }

    def check_divergence(self) -> dict:
        """
        Verifica divergência entre score e preço WIN.
        
        Returns:
            Dict com tipo de divergência, força, descrição e alerta
        """
        score_trend = self._calc_trend(self.score_history)
        win_trend = self._calc_trend(self.win_price_history)

        result = {
            "timestamp": datetime.now(),
            "score_trend": score_trend,
            "win_trend": win_trend,
            "type": "INDEFINIDO",
            "label": "Dados insuficientes",
            "color": "#666666",
            "severity": "none",
            "description": "Aguardando dados suficientes para análise de divergência.",
            "action": "Continue operando normalmente.",
            "icon": "WAIT",
        }

        if score_trend is None or win_trend is None:
            return result

        score_dir = score_trend["direction"]
        win_dir = win_trend["direction"]
        score_strength = score_trend["strength"]
        win_strength = win_trend["strength"]

        # Mesma direção = CONVERGÊNCIA (confirmação)
        if score_dir == "UP" and win_dir == "UP":
            result.update({
                "type": "CONVERGENCIA_ALTA",
                "label": "CONVERGÊNCIA DE ALTA",
                "color": "#00E676",
                "severity": "low",
                "description": f"Score subindo (+{score_trend['change']:.1f}) e WIN subindo (+{win_trend['change']:.0f} pts). Cenário macro confirma o movimento.",
                "action": "Movimento sustentado. Viés de compra confirmado.",
                "icon": "CONV+",
            })
        elif score_dir == "DOWN" and win_dir == "DOWN":
            result.update({
                "type": "CONVERGENCIA_BAIXA",
                "label": "CONVERGÊNCIA DE BAIXA",
                "color": "#FF1744",
                "severity": "low",
                "description": f"Score caindo ({score_trend['change']:.1f}) e WIN caindo ({win_trend['change']:.0f} pts). Cenário macro confirma o movimento.",
                "action": "Queda sustentada. Viés de venda confirmado.",
                "icon": "CONV-",
            })

        # Divergência = CUIDADO
        elif score_dir == "UP" and win_dir == "DOWN":
            result.update({
                "type": "DIVERGENCIA_ALTA",
                "label": "DIVERGÊNCIA DE ALTA",
                "color": "#FFD600",
                "severity": "medium" if score_strength < 0.5 else "high",
                "description": f"Score subindo (+{score_trend['change']:.1f}) mas WIN caindo ({win_trend['change']:.0f} pts). Macro não confirma a queda.",
                "action": "WIN pode reverter para alta. Cuidado com posições vendadas.",
                "icon": "DIV+",
            })
        elif score_dir == "DOWN" and win_dir == "UP":
            result.update({
                "type": "DIVERGENCIA_BAIXA",
                "label": "DIVERGÊNCIA DE BAIXA",
                "color": "#FFD600",
                "severity": "medium" if score_strength < 0.5 else "high",
                "description": f"Score caindo ({score_trend['change']:.1f}) mas WIN subindo (+{win_trend['change']:.0f} pts). Macro não confirma a alta.",
                "action": "WIN pode reverter para baixa. Cuidado com posições compradas.",
                "icon": "DIV-",
            })

        # Um dos dois flat
        elif score_dir == "FLAT" or win_dir == "FLAT":
            result.update({
                "type": "NEUTRO",
                "label": "SEM DIVERGÊNCIA",
                "color": "#78909C",
                "severity": "none",
                "description": f"Score: {score_dir} | WIN: {win_dir}. Sem conflito significativo.",
                "action": "Continue observando o painel.",
                "icon": "NEUTRO",
            })

        return result

    def get_status_summary(self) -> dict:
        """Retorna resumo rápido para o dashboard."""
        div = self.check_divergence()
        score_trend = div.get("score_trend")
        win_trend = div.get("win_trend")

        return {
            "type": div["type"],
            "label": div["label"],
            "color": div["color"],
            "severity": div["severity"],
            "icon": div["icon"],
            "score_direction": score_trend["direction"] if score_trend else "N/A",
            "win_direction": win_trend["direction"] if win_trend else "N/A",
            "score_change": score_trend["change"] if score_trend else 0,
            "win_change": win_trend["change"] if win_trend else 0,
            "has_enough_data": score_trend is not None and win_trend is not None,
        }
