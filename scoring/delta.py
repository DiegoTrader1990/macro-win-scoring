"""
Calculo de Delta e Timing de Entrada - v4.1
==============================================
Analisa a variacao do score macro para identificar:
- Momentum (direcao e velocidade da mudanca)
- Divergencias (score vs preco)
- Sinais de entrada (timing baseado em delta)
- RECUPERACAO INTRADAY: detecta quando o preco esta subindo
  mesmo com score negativo (o cenario que o sistema anterior perdia)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DeltaAnalyzer:
    """
    Analisador de Delta para timing de entrada.

    Conceitos:
    - Delta: Variacao do score entre leituras
    - Momentum: Taxa de variacao do delta (2a derivada)
    - Reversal: Quando delta muda de sinal (possivel reversao)
    - Confluence: Quando score e delta apontam na mesma direcao
    - RECUPERACAO: Score negativo + Delta positivo = preco subindo em dia de baixa
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.score_history = []
        self.delta_history = []
        self._max_history = 500
        # Tracking intraday para deteccao de recuperacao
        self._session_low_score = None
        self._session_high_score = None
        self._session_start_score = None

    def update(self, score: float, timestamp: datetime = None):
        """
        Adiciona uma nova leitura de score ao historico.
        """
        timestamp = timestamp or datetime.now()

        # Track session extremes
        if self._session_low_score is None or score < self._session_low_score:
            self._session_low_score = score
        if self._session_high_score is None or score > self._session_high_score:
            self._session_high_score = score
        if self._session_start_score is None:
            self._session_start_score = score

        self.score_history.append({"score": score, "timestamp": timestamp})

        # Calcula delta
        if len(self.score_history) >= 2:
            delta = score - self.score_history[-2]["score"]
            self.delta_history.append({
                "delta": delta,
                "timestamp": timestamp,
                "score": score,
            })

        # Limita historico
        if len(self.score_history) > self._max_history:
            self.score_history.pop(0)
        if len(self.delta_history) > self._max_history:
            self.delta_history.pop(0)

    def _detect_intraday_recovery(self, score: float, current_delta: float) -> Optional[dict]:
        """
        Detecta quando o preco esta se recuperando dentro de um dia de baixa.
        
        Cenario: Score negativo (macro em baixa) MAS:
        - Delta esta POSITIVO (score melhorando)
        - Score esta subindo do minimo da sessao
        - Momentum positivo (aceleracao para cima)
        
        Este e o cenario que o sistema anterior perdia:
        "O dia era de baixa mas depois que caiu o indice so subiu"
        
        Returns:
            Dict com info de recuperacao ou None
        """
        if len(self.delta_history) < 3:
            return None

        # Score negativo = dia de baixa macro
        if score >= -10:
            return None

        # Verifica se delta esta positivo (score melhorando)
        if current_delta <= 0:
            return None

        # Verifica se score subiu do minimo da sessao
        if self._session_low_score is None:
            return None

        recovery_from_low = score - self._session_low_score
        total_range = self._session_high_score - self._session_low_score if (self._session_high_score and self._session_low_score) else 0

        if total_range == 0:
            return None

        recovery_pct = recovery_from_low / total_range * 100 if total_range > 0 else 0

        # Verifica momentum: ultimos 3 deltas
        recent_deltas = [d["delta"] for d in self.delta_history[-3:]]
        avg_recent_delta = sum(recent_deltas) / len(recent_deltas) if recent_deltas else 0

        # Quantos dos ultimos deltas sao positivos
        positive_deltas = sum(1 for d in recent_deltas if d > 0)
        consistent_improvement = positive_deltas >= 2

        # Determina forca da recuperacao
        if recovery_pct > 60 and consistent_improvement:
            strength = "FORTE"
            color = "#00E676"
        elif recovery_pct > 30 and consistent_improvement:
            strength = "MODERADA"
            color = "#66BB6A"
        elif recovery_pct > 15 or (current_delta > 3 and consistent_improvement):
            strength = "INICIAL"
            color = "#FFD600"
        else:
            return None  # Ainda nao e uma recuperacao significativa

        return {
            "detected": True,
            "strength": strength,
            "color": color,
            "recovery_pct": round(recovery_pct, 1),
            "recovery_points": round(recovery_from_low, 1),
            "session_low": round(self._session_low_score, 1),
            "session_high": round(self._session_high_score, 1),
            "avg_delta": round(avg_recent_delta, 2),
            "consistent": consistent_improvement,
            "description": f"Score negativo ({score:+.0f}) mas melhorando ha {positive_deltas}/3 leituras. Recuperou {recovery_pct:.0f}% da faixa da sessao.",
        }

    def _detect_intraday_reversal_down(self, score: float, current_delta: float) -> Optional[dict]:
        """
        Detecta quando o preco esta caindo dentro de um dia de alta.
        Espelho do recovery: Score positivo + Delta negativo = reversao para baixo.
        """
        if len(self.delta_history) < 3:
            return None

        if score <= 10:
            return None

        if current_delta >= 0:
            return None

        if self._session_high_score is None:
            return None

        drop_from_high = self._session_high_score - score
        total_range = self._session_high_score - self._session_low_score if (self._session_high_score and self._session_low_score) else 0

        if total_range == 0:
            return None

        drop_pct = drop_from_high / total_range * 100 if total_range > 0 else 0

        recent_deltas = [d["delta"] for d in self.delta_history[-3:]]
        negative_deltas = sum(1 for d in recent_deltas if d < 0)
        consistent_decline = negative_deltas >= 2

        if drop_pct > 60 and consistent_decline:
            strength = "FORTE"
            color = "#FF1744"
        elif drop_pct > 30 and consistent_decline:
            strength = "MODERADA"
            color = "#EF5350"
        elif drop_pct > 15 or (current_delta < -3 and consistent_decline):
            strength = "INICIAL"
            color = "#FFD600"
        else:
            return None

        return {
            "detected": True,
            "strength": strength,
            "color": color,
            "drop_pct": round(drop_pct, 1),
            "drop_points": round(drop_from_high, 1),
            "session_high": round(self._session_high_score, 1),
            "session_low": round(self._session_low_score, 1),
            "avg_delta": round(sum(recent_deltas) / len(recent_deltas), 2),
            "consistent": consistent_decline,
            "description": f"Score positivo ({score:+.0f}) mas piorando ha {negative_deltas}/3 leituras. Caiu {drop_pct:.0f}% da faixa da sessao.",
        }

    def get_entry_signal(self, current_score_result: dict) -> dict:
        """
        Gera sinal de entrada baseado no score e delta.
        Inclui deteccao de RECUPERACAO INTRADAY.
        """
        score = current_score_result["score"]

        # Dados basicos
        result = {
            "timestamp": datetime.now(),
            "score": score,
            "signal_type": current_score_result["signal"]["type"],
        }

        # Calcula delta atual
        if len(self.delta_history) >= 1:
            current_delta = self.delta_history[-1]["delta"]
            result["delta"] = round(current_delta, 2)
        else:
            current_delta = 0
            result["delta"] = 0

        # Calcula momentum (variacao do delta)
        if len(self.delta_history) >= 2:
            prev_delta = self.delta_history[-2]["delta"]
            momentum = current_delta - prev_delta
            result["momentum"] = round(momentum, 2)
        else:
            momentum = 0
            result["momentum"] = 0

        # ---- LOGICA DE SINAL ----

        # Confluence: Score e Delta na mesma direcao
        score_bullish = score > 30
        score_bearish = score < -30
        delta_bullish = current_delta > 5
        delta_bearish = current_delta < -5

        # Reversal: Delta muda de direcao
        if len(self.delta_history) >= 2:
            prev_delta = self.delta_history[-2]["delta"]
            reversal_up = prev_delta < 0 and current_delta > 0
            reversal_down = prev_delta > 0 and current_delta < 0
        else:
            reversal_up = False
            reversal_down = False

        # === NOVO: Deteccao de recuperacao intraday ===
        recovery = self._detect_intraday_recovery(score, current_delta)
        reversal_down_signal = self._detect_intraday_reversal_down(score, current_delta)

        result["intraday_recovery"] = recovery
        result["intraday_reversal_down"] = reversal_down_signal

        # Determina sinal de entrada - ORDEM IMPORTANTE:
        # Primeiro verifica recuperacoes (prioridade alta!)
        if recovery and recovery["strength"] == "FORTE":
            entry = {
                "type": "RECUPERACAO_FORTE",
                "label": "RECUPERACAO FORTE",
                "action": f"Macro em baixa mas score melhorando forte (+{recovery['recovery_points']:.0f}pts). Indice provavelmente subindo. CUIDADO com venda.",
                "confidence": "ALTA",
                "suggested_side": "LONG",
            }
        elif recovery and recovery["strength"] == "MODERADA":
            entry = {
                "type": "RECUPERACAO",
                "label": "RECUPERACAO INTRADAY",
                "action": f"Score negativo mas recuperando ({recovery['recovery_pct']:.0f}% da faixa). Possivel compra em suporte.",
                "confidence": "MEDIA-ALTA",
                "suggested_side": "LONG",
            }
        elif recovery and recovery["strength"] == "INICIAL":
            entry = {
                "type": "RECUPERACAO_INICIAL",
                "label": "INICIO RECUPERACAO",
                "action": f"Sinais iniciais de melhora no score. Aguarde confirmacao para entrar compra.",
                "confidence": "MEDIA",
                "suggested_side": "LONG",
            }
        elif reversal_down_signal and reversal_down_signal["strength"] in ("FORTE", "MODERADA"):
            entry = {
                "type": "REVERSAO_BAIXA_INTRADAY",
                "label": "REVERSAO INTRADAY BAIXA",
                "action": f"Score positivo mas piorando. Possivel saida de compra ou entrada de venda.",
                "confidence": "MEDIA-ALTA",
                "suggested_side": "SHORT",
            }
        # Sinais tradicionais (mantidos)
        elif score >= 50 and delta_bullish:
            entry = {
                "type": "COMPRA_FORTE",
                "label": "COMPRA FORTE",
                "action": "Entrada agressiva de COMPRA. Score forte + Delta confirmando.",
                "confidence": "ALTA",
                "suggested_side": "LONG",
            }
        elif score >= 30 and delta_bullish:
            entry = {
                "type": "COMPRA",
                "label": "COMPRA",
                "action": "Entrada de COMPRA. Score positivo + Delta melhorando.",
                "confidence": "MEDIA-ALTA",
                "suggested_side": "LONG",
            }
        elif score >= 30 and not delta_bearish:
            entry = {
                "type": "COMPRA_CAUTELA",
                "label": "COMPRA COM CAUTELA",
                "action": "Vies de compra mas sem confirmacao de delta.",
                "confidence": "MEDIA",
                "suggested_side": "LONG",
            }
        elif score <= -50 and delta_bearish:
            entry = {
                "type": "VENDA_FORTE",
                "label": "VENDA FORTE",
                "action": "Entrada agressiva de VENDA. Score negativo + Delta confirmando.",
                "confidence": "ALTA",
                "suggested_side": "SHORT",
            }
        elif score <= -30 and delta_bearish:
            entry = {
                "type": "VENDA",
                "label": "VENDA",
                "action": "Entrada de VENDA. Score negativo + Delta piorando.",
                "confidence": "MEDIA-ALTA",
                "suggested_side": "SHORT",
            }
        elif score <= -30 and not delta_bullish:
            entry = {
                "type": "VENDA_CAUTELA",
                "label": "VENDA COM CAUTELA",
                "action": "Vies de venda mas sem confirmacao de delta.",
                "confidence": "MEDIA",
                "suggested_side": "SHORT",
            }
        elif reversal_up and score > -10:
            entry = {
                "type": "REVERSAO_ALTA",
                "label": "POSSIVEL REVERSAO DE ALTA",
                "action": "Delta revertendo para positivo. Possivel oportunidade de COMPRA.",
                "confidence": "MEDIA",
                "suggested_side": "LONG",
            }
        elif reversal_down and score < 10:
            entry = {
                "type": "REVERSAO_BAIXA",
                "label": "POSSIVEL REVERSAO DE BAIXA",
                "action": "Delta revertendo para negativo. Possivel oportunidade de VENDA.",
                "confidence": "MEDIA",
                "suggested_side": "SHORT",
            }
        else:
            entry = {
                "type": "NEUTRO",
                "label": "SEM SINAL CLARO",
                "action": "Score e Delta sem alinhamento. Fique fora ou opere com stops rigorosos.",
                "confidence": "BAIXA",
                "suggested_side": "FLAT",
            }

        result["entry_signal"] = entry
        result["confluence"] = {
            "score_delta_aligned": (score_bullish and delta_bullish) or (score_bearish and delta_bearish),
            "reversal_detected": reversal_up or reversal_down,
            "recovery_detected": recovery is not None and recovery.get("detected", False),
        }

        return result

    def get_score_trend(self, periods: int = 10) -> dict:
        """Analisa a tendencia recente do score."""
        if len(self.score_history) < periods:
            periods = len(self.score_history)

        if periods < 2:
            return {"trend": "INSUFICIENTE", "data_points": periods}

        recent = self.score_history[-periods:]
        scores = [s["score"] for s in recent]

        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)

        mid = len(scores) // 2
        first_half_avg = sum(scores[:mid]) / max(mid, 1)
        second_half_avg = sum(scores[mid:]) / max(len(scores) - mid, 1)

        trend_delta = second_half_avg - first_half_avg

        if trend_delta > 10:
            trend = "ALTISTA"
        elif trend_delta < -10:
            trend = "BAIXISTA"
        else:
            trend = "LATERAL"

        variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5

        return {
            "trend": trend,
            "trend_delta": round(trend_delta, 2),
            "average": round(avg_score, 2),
            "min": round(min_score, 2),
            "max": round(max_score, 2),
            "std_dev": round(std_dev, 2),
            "data_points": periods,
        }

    def reset_session(self):
        """Reseta tracking da sessao (chamar no inicio de cada dia)."""
        self._session_low_score = None
        self._session_high_score = None
        self._session_start_score = None
