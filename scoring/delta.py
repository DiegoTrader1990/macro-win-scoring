"""
Cálculo de Delta e Timing de Entrada
======================================
Analisa a variação do score macro para identificar:
- Momentum (direção e velocidade da mudança)
- Divergências (score vs preço)
- Sinais de entrada (timing baseado em delta)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DeltaAnalyzer:
    """
    Analisador de Delta para timing de entrada.
    
    Conceitos:
    - Delta: Variação do score entre leituras
    - Momentum: Taxa de variação do delta (2ª derivada)
    - Reversal: Quando delta muda de sinal (possível reversão)
    - Confluence: Quando score e delta apontam na mesma direção
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.score_history = []
        self.delta_history = []
        self._max_history = 500
    
    def update(self, score: float, timestamp: datetime = None):
        """
        Adiciona uma nova leitura de score ao histórico.
        
        Args:
            score: Score atual
            timestamp: Momento da leitura
        """
        timestamp = timestamp or datetime.now()
        
        self.score_history.append({"score": score, "timestamp": timestamp})
        
        # Calcula delta
        if len(self.score_history) >= 2:
            delta = score - self.score_history[-2]["score"]
            self.delta_history.append({
                "delta": delta,
                "timestamp": timestamp,
                "score": score,
            })
        
        # Limita histórico
        if len(self.score_history) > self._max_history:
            self.score_history.pop(0)
        if len(self.delta_history) > self._max_history:
            self.delta_history.pop(0)
    
    def get_entry_signal(self, current_score_result: dict) -> dict:
        """
        Gera sinal de entrada baseado no score e delta.
        
        Args:
            current_score_result: Resultado do MacroScorer.calculate_score()
        
        Returns:
            Dict com sinal de entrada, tipo, força, justificativa
        """
        score = current_score_result["score"]
        
        # Dados básicos
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
        
        # Calcula momentum (variação do delta)
        if len(self.delta_history) >= 2:
            prev_delta = self.delta_history[-2]["delta"]
            momentum = current_delta - prev_delta
            result["momentum"] = round(momentum, 2)
        else:
            momentum = 0
            result["momentum"] = 0
        
        # ---- LÓGICA DE SINAL ----
        
        # Confluence: Score e Delta na mesma direção
        score_bullish = score > 30
        score_bearish = score < -30
        delta_bullish = current_delta > 5
        delta_bearish = current_delta < -5
        
        # Reversal: Delta muda de direção
        if len(self.delta_history) >= 2:
            prev_delta = self.delta_history[-2]["delta"]
            reversal_up = prev_delta < 0 and current_delta > 0
            reversal_down = prev_delta > 0 and current_delta < 0
        else:
            reversal_up = False
            reversal_down = False
        
        # Determina sinal de entrada
        if score >= 50 and delta_bullish:
            entry = {
                "type": "COMPRA_FORTE",
                "label": "COMPRA FORTE",
                "emoji": "🟢🟢🟢",
                "action": "Entrada agressiva de COMPRA. Score forte + Delta confirmando.",
                "confidence": "ALTA",
                "suggested_side": "LONG",
            }
        elif score >= 30 and delta_bullish:
            entry = {
                "type": "COMPRA",
                "label": "COMPRA",
                "emoji": "🟢🟢",
                "action": "Entrada de COMPRA. Score positivo + Delta melhorando.",
                "confidence": "MÉDIA-ALTA",
                "suggested_side": "LONG",
            }
        elif score >= 30 and not delta_bearish:
            entry = {
                "type": "COMPRA_CAUTELA",
                "label": "COMPRA COM CAUTELA",
                "emoji": "🟢",
                "action": "Viés de compra mas sem confirmação de delta. Aguarde confirmação.",
                "confidence": "MÉDIA",
                "suggested_side": "LONG",
            }
        elif score <= -50 and delta_bearish:
            entry = {
                "type": "VENDA_FORTE",
                "label": "VENDA FORTE",
                "emoji": "🔴🔴🔴",
                "action": "Entrada agressiva de VENDA. Score negativo + Delta confirmando.",
                "confidence": "ALTA",
                "suggested_side": "SHORT",
            }
        elif score <= -30 and delta_bearish:
            entry = {
                "type": "VENDA",
                "label": "VENDA",
                "emoji": "🔴🔴",
                "action": "Entrada de VENDA. Score negativo + Delta piorando.",
                "confidence": "MÉDIA-ALTA",
                "suggested_side": "SHORT",
            }
        elif score <= -30 and not delta_bullish:
            entry = {
                "type": "VENDA_CAUTELA",
                "label": "VENDA COM CAUTELA",
                "emoji": "🔴",
                "action": "Viés de venda mas sem confirmação de delta. Aguarde confirmação.",
                "confidence": "MÉDIA",
                "suggested_side": "SHORT",
            }
        elif reversal_up and score > -10:
            entry = {
                "type": "REVERSAO_ALTA",
                "label": "POSSÍVEL REVERSÃO DE ALTA",
                "emoji": "🔄🟢",
                "action": "Delta revertendo para positivo. Possível oportunidade de COMPRA.",
                "confidence": "MÉDIA",
                "suggested_side": "LONG",
            }
        elif reversal_down and score < 10:
            entry = {
                "type": "REVERSAO_BAIXA",
                "label": "POSSÍVEL REVERSÃO DE BAIXA",
                "emoji": "🔄🔴",
                "action": "Delta revertendo para negativo. Possível oportunidade de VENDA.",
                "confidence": "MÉDIA",
                "suggested_side": "SHORT",
            }
        else:
            entry = {
                "type": "NEUTRO",
                "label": "SEM SINAL CLARO",
                "emoji": "⚪",
                "action": "Score e Delta sem alinhamento. Fique fora ou opere com stops rigorosos.",
                "confidence": "BAIXA",
                "suggested_side": "FLAT",
            }
        
        result["entry_signal"] = entry
        result["confluence"] = {
            "score_delta_aligned": (score_bullish and delta_bullish) or (score_bearish and delta_bearish),
            "reversal_detected": reversal_up or reversal_down,
        }
        
        return result
    
    def get_score_trend(self, periods: int = 10) -> dict:
        """
        Analisa a tendência recente do score.
        
        Args:
            periods: Número de leituras para análise
        
        Returns:
            Dict com tendência, média, volatilidade
        """
        if len(self.score_history) < periods:
            periods = len(self.score_history)
        
        if periods < 2:
            return {"trend": "INSUFICIENTE", "data_points": periods}
        
        recent = self.score_history[-periods:]
        scores = [s["score"] for s in recent]
        
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
        
        # Tendência: compara primeira metade com segunda metade
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
        
        # Volatilidade do score
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
