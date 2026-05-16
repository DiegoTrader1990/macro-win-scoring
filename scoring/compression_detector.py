"""
Compression Detector - Detector de Compressao/Expansao
========================================================
Detecta quando o mercado esta comprimido (volatilidade baixa,
score lateral, setores dispersos) e prestes a expandir.

Nao gera sinais de entrada - apenas classifica o contexto
de compressao para que o trader aumente a atencao.

v6.0 - Componente do sistema de macro scoring
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class CompressionDetector:
    """
    Detector de compressao de volatilidade.

    Analisa:
    - ATR percentile (ATR atual vs historico recente)
    - Score variance (variacao do score)
    - Sector convergence (setores convergindo)

    Retorna Compression Score (0-100):
    - 0-30: Sem compressao
    - 30-60: Compressao moderada
    - 60-100: Alta compressao (expansao provavel)
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.atr_lookback = self.config.get("atr_lookback", 20)
        self.atr_pct_low = self.config.get("atr_percentile_low", 20)
        self.score_var_window = self.config.get("score_variance_window", 15)
        self.sector_conv_threshold = self.config.get("sector_convergence_threshold", 0.7)

        self._atr_history: List[float] = []
        self._score_history: List[float] = []
        self._max_history = 500
        self._last_result: Optional[Dict] = None

        logger.info(f"CompressionDetector inicializado: enabled={self.enabled}")

    def update_atr(self, atr_value: float) -> None:
        """Registra valor do ATR."""
        if not self.enabled:
            return
        self._atr_history.append(atr_value)
        if len(self._atr_history) > self._max_history:
            self._atr_history = self._atr_history[-self._max_history:]

    def update_score(self, score: float) -> None:
        """Registra valor do score."""
        if not self.enabled:
            return
        self._score_history.append(score)
        if len(self._score_history) > self._max_history:
            self._score_history = self._score_history[-self._max_history:]

    def detect(self, category_scores: dict = None) -> Dict:
        """Detecta compressao e retorna Compression Score."""
        if not self.enabled:
            return self._empty_result()

        # ATR Percentile
        atr_score = 0.0
        atr_pct = None
        if len(self._atr_history) >= 5:
            current_atr = self._atr_history[-1]
            sorted_atr = sorted(self._atr_history[-self.atr_lookback:])
            if sorted_atr:
                rank = 0
                for v in sorted_atr:
                    if v <= current_atr:
                        rank += 1
                atr_pct = (rank / len(sorted_atr)) * 100
                # ATR baixo = mais compressao
                if atr_pct < self.atr_pct_low:
                    atr_score = (1.0 - atr_pct / self.atr_pct_low) * 40
                else:
                    atr_score = 0.0

        # Score Variance
        var_score = 0.0
        score_std = None
        if len(self._score_history) >= 5:
            recent = self._score_history[-self.score_var_window:]
            mean = sum(recent) / len(recent)
            variance = sum((s - mean) ** 2 for s in recent) / len(recent)
            score_std = variance ** 0.5
            # Score variance baixa = mais compressao
            if score_std < 10:
                var_score = (1.0 - score_std / 10) * 30
            else:
                var_score = 0.0

        # Sector Convergence
        conv_score = 0.0
        sector_alignment = None
        if category_scores:
            scores = []
            for v in category_scores.values():
                if isinstance(v, dict) and "normalized" in v:
                    scores.append(v["normalized"])
            if len(scores) >= 3:
                avg = sum(scores) / len(scores)
                variance = sum((s - avg) ** 2 for s in scores) / len(scores)
                sector_alignment = 1.0 - min(variance / 10000, 1.0)
                if sector_alignment > self.sector_conv_threshold:
                    # Setores convergindo = prestes a expandir
                    conv_score = sector_alignment * 30

        # Combined Compression Score
        compression_score = min(100, atr_score + var_score + conv_score)

        # Classification
        if compression_score >= 60:
            level = "ALTA"
            color = "#4FC3F7"
            label = "COMPRESSAO ALTA"
        elif compression_score >= 30:
            level = "MODERADA"
            color = "#FFD600"
            label = "COMPRESSAO MODERADA"
        else:
            level = "BAIXA"
            color = "#607D8B"
            label = "SEM COMPRESSAO"

        result = {
            "compression_score": round(compression_score, 1),
            "level": level,
            "label": label,
            "color": color,
            "atr_percentile": round(atr_pct, 1) if atr_pct is not None else None,
            "atr_contribution": round(atr_score, 1),
            "score_std": round(score_std, 1) if score_std is not None else None,
            "var_contribution": round(var_score, 1),
            "sector_alignment": round(sector_alignment, 3) if sector_alignment is not None else None,
            "conv_contribution": round(conv_score, 1),
            "timestamp": datetime.now(),
        }

        self._last_result = result
        return result

    def _empty_result(self) -> Dict:
        return {
            "compression_score": 0, "level": "INDEFINIDO",
            "label": "Aguardando dados", "color": "#607D8B",
            "atr_percentile": None, "atr_contribution": 0,
            "score_std": None, "var_contribution": 0,
            "sector_alignment": None, "conv_contribution": 0,
            "timestamp": datetime.now(),
        }

    def get_status(self) -> Dict:
        r = self._last_result or self._empty_result()
        return {"enabled": self.enabled, "compression_score": r["compression_score"],
                "level": r["level"], "label": r["label"]}

    def reset(self):
        self._atr_history = []
        self._score_history = []
        self._last_result = None
