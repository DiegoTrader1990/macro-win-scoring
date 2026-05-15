"""
Motor de Scoring Macro - Mini Índice (WIN)
============================================
Calcula o score composto baseado nas variações dos ativos macro,
ponderado pelas correlações validadas com dados reais.

Score vai de -100 a +100:
  +100 = Máximo viés de alta
  -100 = Máximo viés de baixa
   0   = Neutro
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MacroScorer:
    """
    Motor de scoring macro para o Mini Índice.
    
    Metodologia:
    1. Para cada ativo, calcula o sinal normalizado (-1 a +1)
    2. Multiplica pelo peso (baseado na correlação validada)
    3. Multiplica pela direção (+1 direta, -1 inversa)
    4. Soma tudo e normaliza para -100 a +100
    """
    
    def __init__(self, weights: dict, signal_config: dict = None):
        """
        Args:
            weights: Dict com pesos e direções dos ativos (do config.MACRO_WEIGHTS)
            signal_config: Configuração de thresholds (do config.SIGNAL_CONFIG)
        """
        self.weights = weights
        self.config = signal_config or {}
        self._history = []
        self._max_history = 1000
    
    def calculate_asset_signal(self, asset_data: dict, weight_config: dict) -> Optional[float]:
        """
        Calcula o sinal normalizado de um ativo individual.
        
        Lógica:
        - Variação intraday > threshold → sinal +1 ou -1
        - Variação entre thresholds → sinal proporcional
        - Direção da correlação inverte o sinal se correlação for inversa
        
        Args:
            asset_data: Dict com dados do ativo (price, change_pct, etc.)
            weight_config: Dict com weight, direction, corr do ativo
        
        Returns:
            Sinal normalizado (-1 a +1) multiplicado pelo peso, ou None
        """
        change_pct = asset_data.get("change_pct")
        
        if change_pct is None:
            return None
        
        # Thresholds para normalização
        # Ativos com maior volatilidade precisam de thresholds maiores
        # Usamos 2% como referência para ativos de alta volatilidade
        # e 0.5% para baixa volatilidade
        corr = abs(weight_config.get("corr", 0.5))
        
        # Thresholds adaptativos baseados na correlação
        # Ativos com correlação forte → threshold menor (mais sensível)
        # Ativos com correlação fraca → threshold maior (mais seletivo)
        if corr > 0.60:
            threshold = 0.3   # Alta sensibilidade
        elif corr > 0.40:
            threshold = 0.5   # Sensibilidade média
        else:
            threshold = 0.8   # Baixa sensibilidade (mais seletivo)
        
        # Normaliza a variação para -1 a +1
        if change_pct > 0:
            signal = min(change_pct / threshold, 1.0)
        elif change_pct < 0:
            signal = max(change_pct / threshold, -1.0)
        else:
            signal = 0.0
        
        # Aplica a direção da correlação
        # Se correlação é inversa (direction = -1), inverte o sinal
        direction = weight_config.get("direction", 1)
        signal *= direction
        
        return signal
    
    def calculate_score(self, all_data: Dict[str, dict]) -> dict:
        """
        Calcula o score macro composto a partir dos dados de todos os ativos.
        
        Args:
            all_data: Dict {nome_ativo: dados} do DataManager
        
        Returns:
            Dict com score, breakdown por ativo, sinais individuais
        """
        raw_score = 0.0
        total_weight_used = 0.0
        asset_signals = {}
        category_scores = {}
        missing_assets = []
        
        for asset_name, weight_config in self.weights.items():
            weight = weight_config["weight"]
            category = weight_config.get("category", "Outros")
            
            if asset_name not in all_data:
                missing_assets.append(asset_name)
                continue
            
            asset_data = all_data[asset_name]
            signal = self.calculate_asset_signal(asset_data, weight_config)
            
            if signal is None:
                missing_assets.append(asset_name)
                continue
            
            # Contribuição ponderada
            contribution = signal * weight
            raw_score += contribution
            total_weight_used += weight
            
            # Guarda sinal individual
            asset_signals[asset_name] = {
                "signal": round(signal, 4),
                "weight": weight,
                "contribution": round(contribution, 4),
                "direction": weight_config.get("direction", 1),
                "correlation": weight_config.get("corr", 0),
                "category": category,
                "change_pct": asset_data.get("change_pct"),
                "current_price": asset_data.get("current_price"),
                "source": asset_data.get("source", "unknown"),
            }
            
            # Acumula por categoria
            if category not in category_scores:
                category_scores[category] = {"raw": 0.0, "weight": 0.0}
            category_scores[category]["raw"] += contribution
            category_scores[category]["weight"] += weight
        
        # Normaliza para -100 a +100
        if total_weight_used > 0:
            # Score normalizado: raw_score / total_weight * 100
            normalized_score = (raw_score / total_weight_used) * 100
        else:
            normalized_score = 0.0
        
        # Limita entre -100 e +100
        normalized_score = max(-100, min(100, normalized_score))
        
        # Determina o sinal geral
        signal_type = self._determine_signal(normalized_score)
        
        # Score por categoria normalizado
        for cat in category_scores:
            if category_scores[cat]["weight"] > 0:
                category_scores[cat]["normalized"] = round(
                    (category_scores[cat]["raw"] / category_scores[cat]["weight"]) * 100, 2
                )
            else:
                category_scores[cat]["normalized"] = 0.0
        
        result = {
            "score": round(normalized_score, 2),
            "signal": signal_type,
            "raw_score": round(raw_score, 4),
            "total_weight_used": round(total_weight_used, 4),
            "asset_signals": asset_signals,
            "category_scores": category_scores,
            "missing_assets": missing_assets,
            "timestamp": datetime.now(),
            "assets_available": len(asset_signals),
            "assets_total": len(self.weights),
        }
        
        # Salva no histórico
        self._history.append({
            "timestamp": datetime.now(),
            "score": normalized_score,
            "signal": signal_type,
        })
        if len(self._history) > self._max_history:
            self._history.pop(0)
        
        return result
    
    def _determine_signal(self, score: float) -> dict:
        """
        Determina o tipo de sinal baseado no score e thresholds.
        
        Args:
            score: Score normalizado (-100 a +100)
        
        Returns:
            Dict com tipo, cor, emoji, descrição
        """
        strong_bull = self.config.get("strong_bullish", 60)
        mod_bull = self.config.get("moderate_bullish", 30)
        mod_bear = self.config.get("moderate_bearish", -30)
        strong_bear = self.config.get("strong_bearish", -60)
        
        if score >= strong_bull:
            return {
                "type": "STRONG_BULLISH",
                "label": "FORTE ALTA",
                "emoji": "🟢🟢🟢",
                "color": "#00C853",
                "action": "Busca operações de COMPRA. Viés macro muito forte.",
                "confidence": "ALTA",
            }
        elif score >= mod_bull:
            return {
                "type": "MODERATE_BULLISH",
                "label": "MODERADA ALTA",
                "emoji": "🟢🟢",
                "color": "#4CAF50",
                "action": "Prefira operações de COMPRA. Viés macro favorável.",
                "confidence": "MÉDIA-ALTA",
            }
        elif score >= mod_bear:
            return {
                "type": "NEUTRAL",
                "label": "NEUTRO",
                "emoji": "🟡",
                "color": "#FFC107",
                "action": "Zona de cautela. Aguarde confirmação ou opere ambos os lados com stops curtos.",
                "confidence": "BAIXA",
            }
        elif score >= strong_bear:
            return {
                "type": "MODERATE_BEARISH",
                "label": "MODERADA BAIXA",
                "emoji": "🔴🔴",
                "color": "#FF5722",
                "action": "Prefira operações de VENDA. Viés macro desfavorável.",
                "confidence": "MÉDIA-ALTA",
            }
        else:
            return {
                "type": "STRONG_BEARISH",
                "label": "FORTE BAIXA",
                "emoji": "🔴🔴🔴",
                "color": "#D50000",
                "action": "Busca operações de VENDA. Viés macro muito negativo.",
                "confidence": "ALTA",
            }
    
    def get_delta(self) -> Optional[dict]:
        """
        Calcula o delta (variação) do score em relação à leitura anterior.
        
        Returns:
            Dict com delta, direção, aceleração, ou None se sem histórico
        """
        if len(self._history) < 2:
            return None
        
        current = self._history[-1]["score"]
        previous = self._history[-2]["score"]
        delta = current - previous
        
        # Determina aceleração
        if len(self._history) >= 3:
            prev_delta = self._history[-2]["score"] - self._history[-3]["score"]
            acceleration = delta - prev_delta
        else:
            acceleration = 0.0
        
        # Direção do delta
        if delta > 0:
            direction = "MELHORANDO"
            delta_emoji = "📈"
        elif delta < 0:
            direction = "PIORANDO"
            delta_emoji = "📉"
        else:
            direction = "ESTÁVEL"
            delta_emoji = "➡️"
        
        # Aceleração
        accel_threshold = self.config.get("delta_acceleration", 15)
        if acceleration > accel_threshold:
            accel_type = "ACELERANDO_ALTA"
            accel_emoji = "🚀"
        elif acceleration < -accel_threshold:
            accel_type = "ACELERANDO_BAIXA"
            accel_emoji = "💥"
        else:
            accel_type = "ESTÁVEL"
            accel_emoji = "⚖️"
        
        return {
            "delta": round(delta, 2),
            "direction": direction,
            "delta_emoji": delta_emoji,
            "acceleration": round(acceleration, 2),
            "accel_type": accel_type,
            "accel_emoji": accel_emoji,
            "current_score": round(current, 2),
            "previous_score": round(previous, 2),
        }
    
    def get_history(self, last_n: int = None) -> list:
        """
        Retorna histórico de scores.
        
        Args:
            last_n: Número de leituras mais recentes (None = todas)
        
        Returns:
            Lista de dicts com timestamp e score
        """
        if last_n:
            return self._history[-last_n:]
        return self._history
    
    def get_top_contributors(self, scoring_result: dict, top_n: int = 5) -> dict:
        """
        Retorna os maiores contribuidores positivos e negativos para o score.
        
        Args:
            scoring_result: Resultado do calculate_score()
            top_n: Número de top contribuidores
        
        Returns:
            Dict com top_positives e top_negatives
        """
        signals = scoring_result.get("asset_signals", {})
        
        # Ordena por contribuição
        sorted_assets = sorted(
            signals.items(),
            key=lambda x: abs(x[1]["contribution"]),
            reverse=True
        )
        
        positives = [(name, data) for name, data in sorted_assets if data["contribution"] > 0][:top_n]
        negatives = [(name, data) for name, data in sorted_assets if data["contribution"] < 0][:top_n]
        
        return {
            "top_positives": positives,
            "top_negatives": negatives,
        }
