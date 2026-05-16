"""
Confidence Score - Auto-Avaliacao do Sistema
==============================================
Avalia o nivel de confianca que o sistema deve ter sobre sua
propria leitura. Quando a confianca e baixa, o sistema deve
alertar o trader para reduzir tamanho de posicao.

Componentes:
- Data quality: quantos ativos tem dados validos
- Sector alignment: quao alinhados os setores estao
- Regime stability: regime estavel ou em transicao
- Divergence presence: divergencias reduzem confianca
- Score consistency: score estavel vs oscilante

Confidence Score: 0-100
- 0-30: BAIXA - Reduzir tamanho, nao confiar no score
- 30-60: MEDIA - Operar com cautela
- 60-100: ALTA - Score confiavel, operar normalmente

v6.0 - Componente do sistema de macro scoring
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class ConfidenceScore:
    """
    Avaliador de confianca do sistema sobre sua propria leitura.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.min_data_quality = self.config.get("min_data_quality", 0.6)
        self._score_history: List[float] = []
        self._max_history = 200
        self._last_result: Optional[Dict] = None
        logger.info(f"ConfidenceScore inicializado: enabled={self.enabled}")

    def update(self, score: float) -> None:
        if not self.enabled:
            return
        self._score_history.append(score)
        if len(self._score_history) > self._max_history:
            self._score_history = self._score_history[-self._max_history:]

    def calculate(self, assets_available: int = 0, assets_total: int = 20,
                  regime_result: dict = None,
                  divergence_result: dict = None,
                  category_scores: dict = None) -> Dict:
        """Calcula o Confidence Score combinando todos os fatores."""
        if not self.enabled:
            return self._empty_result()

        # 1. Data Quality (0-25 points)
        data_ratio = assets_available / max(assets_total, 1)
        if data_ratio >= 0.8:
            data_quality_score = 25
        elif data_ratio >= 0.6:
            data_quality_score = 18
        elif data_ratio >= 0.4:
            data_quality_score = 10
        else:
            data_quality_score = 5

        # 2. Sector Alignment (0-25 points)
        sector_score = 12  # default moderate
        if category_scores:
            scores = []
            for v in category_scores.values():
                if isinstance(v, dict) and "normalized" in v:
                    scores.append(v["normalized"])
            if len(scores) >= 3:
                avg = sum(scores) / len(scores)
                variance = sum((s - avg) ** 2 for s in scores) / len(scores)
                alignment = 1.0 - min(variance / 10000, 1.0)
                if alignment > 0.7:
                    sector_score = 25
                elif alignment > 0.5:
                    sector_score = 18
                else:
                    sector_score = 8

        # 3. Regime Stability (0-25 points)
        regime_score = 12
        if regime_result:
            regime_type = regime_result.get("regime", "INDEFINIDO")
            regime_conf = regime_result.get("confidence", "")
            if regime_type in ("TENDENCIA_ALTA", "TENDENCIA_BAIXA") and regime_conf == "ALTA":
                regime_score = 25
            elif regime_type in ("TENDENCIA_ALTA", "TENDENCIA_BAIXA"):
                regime_score = 18
            elif regime_type == "LATERAL":
                regime_score = 15
            elif regime_type == "VOLATIL":
                regime_score = 8
            elif regime_type == "TRANSICAO":
                regime_score = 3
            elif regime_type == "INDEFINIDO":
                regime_score = 5

        # 4. Divergence Presence (0-25 points)
        divergence_score = 25  # no divergence = high confidence
        if divergence_result:
            div_type = divergence_result.get("type", "NEUTRO")
            div_severity = divergence_result.get("severity", "none")
            if "DIVERGENCIA" in str(div_type).upper():
                if div_severity == "high":
                    divergence_score = 5
                elif div_severity == "medium":
                    divergence_score = 12
                else:
                    divergence_score = 18

        # Combined
        confidence_score = min(100, data_quality_score + sector_score + regime_score + divergence_score)

        # Classification
        if confidence_score >= 60:
            level = "ALTA"
            color = "#00E676"
            label = "CONFIANCA ALTA"
            advice = "Score confiavel. Operar normalmente."
        elif confidence_score >= 30:
            level = "MEDIA"
            color = "#FFD600"
            label = "CONFIANCA MEDIA"
            advice = "Operar com cautela. Reduzir tamanho."
        else:
            level = "BAIXA"
            color = "#FF1744"
            label = "CONFIANCA BAIXA"
            advice = "Nao confiar no score. Reduzir posicoes. Aguardar."

        result = {
            "confidence_score": round(confidence_score, 1),
            "level": level,
            "label": label,
            "color": color,
            "advice": advice,
            "data_quality_score": data_quality_score,
            "data_ratio": round(data_ratio, 2),
            "sector_score": sector_score,
            "regime_score": regime_score,
            "divergence_score": divergence_score,
            "timestamp": datetime.now(),
        }

        self._last_result = result
        return result

    def _empty_result(self) -> Dict:
        return {
            "confidence_score": 0, "level": "INDEFINIDA",
            "label": "Aguardando dados", "color": "#607D8B",
            "advice": "Aguardando dados suficientes.",
            "data_quality_score": 0, "data_ratio": 0,
            "sector_score": 0, "regime_score": 0,
            "divergence_score": 0, "timestamp": datetime.now(),
        }

    def get_status(self) -> Dict:
        r = self._last_result or self._empty_result()
        return {"enabled": self.enabled, "confidence": r["confidence_score"],
                "level": r["level"], "label": r["label"]}

    def reset(self):
        self._score_history = []
        self._last_result = None
