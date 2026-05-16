"""
Context Classifier - Classificacao de Contexto Operacional
============================================================
Combina resultados de TODOS os modulos do sistema para classificar
o contexto operacional do mercado. NAO gera sinais - classifica o
cenario para que o trader tome decisoes informadas.

Contextos:
- TENDENCIA_SAUDAVEL: Score + preco + setores alinhados
- ALTA_PERIGOSA: Preco subindo mas score diverge
- MERCADO_TRANSICAO: Regime mudando
- EXPANSAO_PROVAVEL: Compressao + alinhamento
- MOVIMENTO_SEM_PARTICIPACAO: Preco move mas amplitude fraca
- REVERSAO_PROVAVEL: Divergencia + exaustao
- FLUXO_ABSORVENDO: Agressao contraria sem movimento
- LATERAL_INDEFINIDO: Sem contexto claro

v6.0 - Componente do sistema de macro scoring
"""

import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ContextClassifier:
    """
    Classificador de contexto operacional.

    Combina informacoes de score, regime, divergencia, reversao,
    confluencia e compressao para classificar o cenario atual
    e sugerir a abordagem de trading adequada.
    """

    CONTEXT_TYPES = {
        "TENDENCIA_SAUDAVEL": {
            "label": "TENDENCIA SAUDAVEL",
            "color": "#00E676",
            "icon": "T+",
            "action": "Buscar entradas a favor da tendencia. Movimento sustentado.",
            "risk": "BAIXO",
        },
        "ALTA_PERIGOSA": {
            "label": "ALTA PERIGOSA",
            "color": "#FF9800",
            "icon": "!+",
            "action": "Nao confiar na alta. Score diverge do preco. Proteger posicoes.",
            "risk": "ALTO",
        },
        "BAIXA_PERIGOSA": {
            "label": "BAIXA PERIGOSA",
            "color": "#FF9800",
            "icon": "!-",
            "action": "Nao confiar na baixa. Score diverge do preco. Proteger posicoes.",
            "risk": "ALTO",
        },
        "MERCADO_TRANSICAO": {
            "label": "EM TRANSICAO",
            "color": "#FF5722",
            "icon": "TR",
            "action": "Reduzir tamanho. Regime mudando. Aguardar clareza.",
            "risk": "MUITO ALTO",
        },
        "EXPANSAO_PROVAVEL": {
            "label": "EXPANSAO PROVAVEL",
            "color": "#4FC3F7",
            "icon": "EXP",
            "action": "Mercado comprimido. Preparar ordem, NAO executar. Aguardar breakout.",
            "risk": "MODERADO",
        },
        "MOVIMENTO_SEM_PARTICIPACAO": {
            "label": "SEM PARTICIPACAO",
            "color": "#78909C",
            "icon": "FRG",
            "action": "Preco move mas sem amplitude. Ceticismo. Nao seguir.",
            "risk": "ALTO",
        },
        "REVERSAO_PROVAVEL": {
            "label": "REVERSAO PROVAVEL",
            "color": "#FFD600",
            "icon": "REV",
            "action": "Divergencia + exaustao detectada. Preparar contra-tendencia.",
            "risk": "MODERADO-ALTO",
        },
        "FLUXO_ABSORVENDO": {
            "label": "FLUXO ABSORVENDO",
            "color": "#AB47BC",
            "icon": "ABS",
            "action": "Agressao contraria sem movimento de preco. Possivel exaustao.",
            "risk": "MODERADO",
        },
        "LATERAL_INDEFINIDO": {
            "label": "LATERAL",
            "color": "#607D8B",
            "icon": "LAT",
            "action": "Sem contexto claro. Aguardar. Nao forcar entrada.",
            "risk": "MODERADO",
        },
    }

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.min_periods = self.config.get("min_periods", 5)
        self._last_result: Optional[Dict] = None
        self._classification_history = []
        self._max_history = 200
        logger.info(f"ContextClassifier inicializado: enabled={self.enabled}")

    def classify(self, score: float, delta: float = 0,
                 regime_result: dict = None,
                 divergence_result: dict = None,
                 reversal_result: dict = None,
                 filtered_signal: dict = None,
                 compression_result: dict = None,
                 confidence_result: dict = None,
                 category_scores: dict = None) -> Dict:
        if not self.enabled:
            return self._empty_result("Sistema desabilitado")

        regime_type = self._safe_get(regime_result, "regime", "INDEFINIDO")
        div_type = self._safe_get(divergence_result, "type", "NEUTRO")
        rev_detected = self._safe_get(reversal_result, "detected", False)
        rev_direction = self._safe_get(reversal_result, "direction", "")
        compression_score = self._safe_get(compression_result, "compression_score", 0)
        confidence = self._safe_get(confidence_result, "confidence_score", 50)
        sector_alignment = self._calc_sector_alignment(category_scores)

        # PRIORIDADE 1: Reversao provavel
        if rev_detected and "DIVERGENCIA" in str(div_type).upper():
            ctx_type = "REVERSAO_PROVAVEL"
            reason = f"Divergencia ({div_type}) + reversao ({rev_direction})"
        # PRIORIDADE 2: Mercado em transicao
        elif regime_type == "TRANSICAO":
            ctx_type = "MERCADO_TRANSICAO"
            reason = f"Regime em transicao. Score:{score:+.0f} Delta:{delta:+.1f}"
        # PRIORIDADE 3: Alta/Baixa perigosa
        elif score > 20 and div_type in ("DIVERGENCIA_BAIXA",):
            ctx_type = "ALTA_PERIGOSA"
            reason = f"Score altista ({score:+.0f}) mas divergencia baixista"
        elif score < -20 and div_type in ("DIVERGENCIA_ALTA",):
            ctx_type = "BAIXA_PERIGOSA"
            reason = f"Score baixista ({score:+.0f}) mas divergencia altista"
        elif rev_detected and rev_direction == "BAIXA" and score > 20:
            ctx_type = "ALTA_PERIGOSA"
            reason = f"Reversao para baixa com score altista"
        elif rev_detected and rev_direction == "ALTA" and score < -20:
            ctx_type = "BAIXA_PERIGOSA"
            reason = f"Reversao para alta com score baixista"
        # PRIORIDADE 4: Expansao provavel
        elif compression_score > 60 and sector_alignment > 0.6:
            ctx_type = "EXPANSAO_PROVAVEL"
            reason = f"Compressao ({compression_score:.0f}) + setores convergindo"
        # PRIORIDADE 5: Movimento sem participacao
        elif abs(score) > 25 and sector_alignment < 0.35 and confidence < 40:
            ctx_type = "MOVIMENTO_SEM_PARTICIPACAO"
            reason = f"Score {score:+.0f} mas setores dispersos e baixa confianca"
        # PRIORIDADE 6: Tendencia saudavel
        elif abs(score) > 25 and sector_alignment > 0.55 and confidence > 50:
            if div_type in ("CONVERGENCIA_ALTA", "CONVERGENCIA_BAIXA", "NEUTRO",
                            "INDEFINIDO", "SEM_DIVERGENCIA"):
                ctx_type = "TENDENCIA_SAUDAVEL"
                reason = f"Score {score:+.0f} + setores alinhados + confianca {confidence:.0f}"
            else:
                ctx_type = "LATERAL_INDEFINIDO"
                reason = f"Score {score:+.0f} mas divergencia presente"
        else:
            ctx_type = "LATERAL_INDEFINIDO"
            reason = f"Score {score:+.0f}, Alineamento {sector_alignment:.0%}, Conf {confidence:.0f}"

        ctx_info = self.CONTEXT_TYPES.get(ctx_type, self.CONTEXT_TYPES["LATERAL_INDEFINIDO"])
        result = {
            "context_type": ctx_type,
            "label": ctx_info["label"],
            "color": ctx_info["color"],
            "icon": ctx_info["icon"],
            "action": ctx_info["action"],
            "risk": ctx_info["risk"],
            "reason": reason,
            "score": score,
            "delta": delta,
            "sector_alignment": round(sector_alignment, 3),
            "compression_score": compression_score,
            "confidence": confidence,
            "timestamp": datetime.now(),
        }
        self._last_result = result
        self._classification_history.append(result)
        if len(self._classification_history) > self._max_history:
            self._classification_history = self._classification_history[-self._max_history:]
        return result

    def _calc_sector_alignment(self, category_scores: dict) -> float:
        if not category_scores:
            return 0.5
        scores = []
        for v in category_scores.values():
            if isinstance(v, dict) and "normalized" in v:
                scores.append(v["normalized"])
        if not scores:
            return 0.5
        if len(scores) < 2:
            return 0.5
        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)
        max_var = 10000
        alignment = 1.0 - min(variance / max_var, 1.0)
        return max(0.0, min(1.0, alignment))

    def _safe_get(self, data, key: str, default=None):
        if data is None or not isinstance(data, dict):
            return default
        return data.get(key, default)

    def _empty_result(self, reason: str) -> Dict:
        info = self.CONTEXT_TYPES["LATERAL_INDEFINIDO"]
        return {
            "context_type": "LATERAL_INDEFINIDO",
            "label": info["label"], "color": info["color"], "icon": info["icon"],
            "action": info["action"], "risk": info["risk"], "reason": reason,
            "score": 0, "delta": 0, "sector_alignment": 0.5,
            "compression_score": 0, "confidence": 0, "timestamp": datetime.now(),
        }

    def get_status(self) -> Dict:
        r = self._last_result or self._empty_result("Nenhuma classificacao")
        return {"enabled": self.enabled, "current_context": r["context_type"],
                "context_label": r["label"], "context_color": r["color"],
                "risk_level": r["risk"], "history_size": len(self._classification_history)}

    def reset(self):
        self._last_result = None
        self._classification_history = []
