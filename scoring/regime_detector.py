"""
Regime Detector - Deteccao de Regime de Mercado
==================================================
Classifica o regime atual do mercado com base no historico do score
macro para sugerir a melhor abordagem de trading.

Regimes detectados:
- TENDENCIA_ALTA: Score medio alto, baixa volatilidade → operar a favor
- TENDENCIA_BAIXA: Score medio baixo, baixa volatilidade → operar a favor
- LATERAL: Score dentro de faixa estreita, baixa volatilidade → reversoes
- VOLATIL: Alta volatilidade no score → reduzir tamanho, stops largos
- TRANSICAO: Regime mudando (delta grande) → aguardar confirmacao

Cada regime sugere uma abordagem diferente de trading, ajudando o
operador a adaptar sua estrategia ao contexto atual do mercado.

v5.0 - Componente do sistema de macro scoring
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RegimeDetector:
    """
    Detector de regime de mercado baseado no score macro.

    Analisa o historico recente de scores para classificar o regime
    atual e sugerir a melhor abordagem de trading.

    Metodologia:
    1. Coleta as ultimas N leituras de score
    2. Calcula media, desvio padrao e range
    3. Verifica a presenca de transicao (delta grande)
    4. Classifica o regime com base nos parametros
    5. Sugere abordagem de trading adequada
    """

    def __init__(self, config: dict = None):
        """
        Inicializa o detector de regime.

        Args:
            config: Dict com configuracoes (REGIME_CONFIG).
                    Campos esperados:
                    - enabled: ativa/desativa deteccao (default: True)
                    - lookback_periods: periodos para analise (default: 20)
                    - trend_threshold: score medio acima = tendencia (default: 20)
                    - lateral_range: range do score para lateral (default: 15)
                    - volatility_threshold: desvio padrao acima = volatil (default: 15)
                    - transition_delta_threshold: delta acima = transicao (default: 10)
                    - min_periods: minimo de periodos para classificar (default: 5)
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.lookback_periods = self.config.get("lookback_periods", 20)
        self.trend_threshold = self.config.get("trend_threshold", 20)
        self.lateral_range = self.config.get("lateral_range", 15)
        self.volatility_threshold = self.config.get("volatility_threshold", 15)
        self.transition_delta_threshold = self.config.get("transition_delta_threshold", 10)
        self.min_periods = self.config.get("min_periods", 5)

        # Historico de scores com timestamp
        self._score_history: List[Dict] = []

        # Regime atual (cache)
        self._current_regime: Optional[Dict] = None

        logger.info(
            f"RegimeDetector inicializado: lookback={self.lookback_periods}, "
            f"trend_threshold={self.trend_threshold}, "
            f"lateral_range={self.lateral_range}, "
            f"volatility_threshold={self.volatility_threshold}, "
            f"enabled={self.enabled}"
        )

    def update(self, score: float, delta: float = None,
               timestamp: datetime = None) -> None:
        """
        Adiciona uma nova leitura de score ao historico.

        Args:
            score: Score macro atual (-100 a +100).
            delta: Variacao do score desde a ultima leitura.
            timestamp: Momento da leitura (default: agora).
        """
        if not self.enabled:
            return

        timestamp = timestamp or datetime.now()

        entry = {
            "timestamp": timestamp,
            "score": score,
            "delta": delta if delta is not None else 0,
        }
        self._score_history.append(entry)

        # Limita historico ao dobro do lookback para analises extras
        max_history = self.lookback_periods * 2
        if len(self._score_history) > max_history:
            self._score_history = self._score_history[-max_history:]

        logger.debug(
            f"RegimeDetector update: score={score:.2f}, delta={delta}, "
            f"history_size={len(self._score_history)}"
        )

    def _get_recent_scores(self) -> List[Dict]:
        """
        Retorna as leituras mais recentes dentro do lookback.

        Returns:
            Lista de dicts com score, delta, timestamp.
        """
        return self._score_history[-self.lookback_periods:]

    def _calc_stats(self, scores: List[float]) -> Dict:
        """
        Calcula estatisticas basicas de uma lista de scores.

        Args:
            scores: Lista de valores de score.

        Returns:
            Dict com mean, std_dev, min, max, range, median.
        """
        if not scores:
            return {
                "mean": 0, "std_dev": 0, "min": 0,
                "max": 0, "range": 0, "median": 0,
                "count": 0,
            }

        n = len(scores)
        mean = sum(scores) / n
        variance = sum((s - mean) ** 2 for s in scores) / n
        std_dev = variance ** 0.5

        sorted_scores = sorted(scores)
        if n % 2 == 0:
            median = (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
        else:
            median = sorted_scores[n // 2]

        return {
            "mean": round(mean, 2),
            "std_dev": round(std_dev, 2),
            "min": round(min(scores), 2),
            "max": round(max(scores), 2),
            "range": round(max(scores) - min(scores), 2),
            "median": round(median, 2),
            "count": n,
        }

    def _check_transition(self, recent: List[Dict]) -> bool:
        """
        Verifica se o mercado esta em transicao de regime.

        Uma transicao e detectada quando:
        - O delta medio recente e grande (acima do threshold)
        - A direcao do score mudou recentemente

        Args:
            recent: Lista de leituras recentes.

        Returns:
            True se transicao detectada.
        """
        if len(recent) < self.min_periods:
            return False

        deltas = [r["delta"] for r in recent if r["delta"] is not None]
        if not deltas:
            return False

        # Verifica se ha deltas grandes
        avg_abs_delta = sum(abs(d) for d in deltas) / len(deltas)
        large_deltas = sum(1 for d in deltas if abs(d) > self.transition_delta_threshold)

        # Transicao: mais de 30% das leituras com delta grande
        if large_deltas / len(deltas) > 0.3:
            return True

        # Transicao: delta medio absoluto acima do threshold
        if avg_abs_delta > self.transition_delta_threshold:
            return True

        return False

    def detect_regime(self) -> Dict:
        """
        Classifica o regime atual do mercado.

        Prioridade de classificacao:
        1. TRANSICAO: Se ha mudanca de regime em andamento
        2. VOLATIL: Se o desvio padrao e alto
        3. TENDENCIA_ALTA: Se score medio e alto e volatilidade baixa
        4. TENDENCIA_BAIXA: Se score medio e baixo e volatilidade baixa
        5. LATERAL: Se score oscila em faixa estreita

        Returns:
            Dict com regime, stats, confianca e detalhes.
        """
        if not self.enabled:
            return self._empty_result("Sistema desabilitado")

        recent = self._get_recent_scores()

        if len(recent) < self.min_periods:
            return self._empty_result(
                f"Dados insuficientes ({len(recent)}/{self.min_periods})"
            )

        scores = [r["score"] for r in recent]
        stats = self._calc_stats(scores)

        is_transition = self._check_transition(recent)
        is_volatile = stats["std_dev"] > self.volatility_threshold
        is_high_trend = stats["mean"] > self.trend_threshold and not is_volatile
        is_low_trend = stats["mean"] < -self.trend_threshold and not is_volatile
        is_lateral = (
            abs(stats["mean"]) <= self.lateral_range
            and stats["range"] <= self.lateral_range * 2
            and not is_volatile
        )

        # Classificacao por prioridade
        if is_transition:
            regime = self._build_regime(
                regime_type="TRANSICAO",
                label="TRANSICAO",
                stats=stats,
                description=(
                    f"Regime em transicao. Score variando rapidamente "
                    f"(delta medio: {stats.get('mean', 0):+.1f}). "
                    f"O mercado esta mudando de contexto."
                ),
                color="#FF9800",
                confidence="BAIXA",
            )
        elif is_volatile:
            regime = self._build_regime(
                regime_type="VOLATIL",
                label="VOLATIL",
                stats=stats,
                description=(
                    f"Mercado volatil. Desvio padrao do score: {stats['std_dev']:.1f} "
                    f"(threshold: {self.volatility_threshold}). "
                    f"Scores oscilando entre {stats['min']:.0f} e {stats['max']:.0f}."
                ),
                color="#FF5722",
                confidence="MEDIA",
            )
        elif is_high_trend:
            regime = self._build_regime(
                regime_type="TENDENCIA_ALTA",
                label="TENDENCIA DE ALTA",
                stats=stats,
                description=(
                    f"Tendencia de alta consistente. Score medio: {stats['mean']:+.1f} "
                    f"com baixa volatilidade ({stats['std_dev']:.1f}). "
                    f"Viés macro favoravel sustentado."
                ),
                color="#00E676",
                confidence="ALTA",
            )
        elif is_low_trend:
            regime = self._build_regime(
                regime_type="TENDENCIA_BAIXA",
                label="TENDENCIA DE BAIXA",
                stats=stats,
                description=(
                    f"Tendencia de baixa consistente. Score medio: {stats['mean']:+.1f} "
                    f"com baixa volatilidade ({stats['std_dev']:.1f}). "
                    f"Viés macro desfavoravel sustentado."
                ),
                color="#FF1744",
                confidence="ALTA",
            )
        elif is_lateral:
            regime = self._build_regime(
                regime_type="LATERAL",
                label="LATERAL",
                stats=stats,
                description=(
                    f"Mercado lateral. Score oscilando entre {stats['min']:.0f} e "
                    f"{stats['max']:.0f} (range: {stats['range']:.0f}). "
                    f"Sem direcao clara no macro."
                ),
                color="#FFD600",
                confidence="MEDIA",
            )
        else:
            # Regime misto — nao se encaixa perfeitamente em nenhum
            if stats["mean"] > 0:
                regime = self._build_regime(
                    regime_type="TENDENCIA_ALTA",
                    label="TENDENCIA DE ALTA (FRACA)",
                    stats=stats,
                    description=(
                        f"Viés levemente altista. Score medio: {stats['mean']:+.1f} "
                        f"mas com volatilidade moderada ({stats['std_dev']:.1f})."
                    ),
                    color="#66BB6A",
                    confidence="MEDIA-BAIXA",
                )
            else:
                regime = self._build_regime(
                    regime_type="TENDENCIA_BAIXA",
                    label="TENDENCIA DE BAIXA (FRACA)",
                    stats=stats,
                    description=(
                        f"Viés levemente baixista. Score medio: {stats['mean']:+.1f} "
                        f"mas com volatilidade moderada ({stats['std_dev']:.1f})."
                    ),
                    color="#EF5350",
                    confidence="MEDIA-BAIXA",
                )

        self._current_regime = regime
        return regime

    def _build_regime(self, regime_type: str, label: str, stats: Dict,
                      description: str, color: str, confidence: str) -> Dict:
        """
        Constroi o dict de resultado do regime.

        Args:
            regime_type: Tipo tecnico do regime.
            label: Label legivel para o dashboard.
            stats: Estatisticas calculadas.
            description: Descricao humana do regime.
            color: Cor para o dashboard.
            confidence: Nivel de confianca da classificacao.

        Returns:
            Dict completo com resultado do regime.
        """
        return {
            "regime": regime_type,
            "label": label,
            "description": description,
            "color": color,
            "confidence": confidence,
            "stats": stats,
            "timestamp": datetime.now(),
            "lookback_periods": self.lookback_periods,
            "parameters": {
                "trend_threshold": self.trend_threshold,
                "lateral_range": self.lateral_range,
                "volatility_threshold": self.volatility_threshold,
                "transition_delta_threshold": self.transition_delta_threshold,
            },
        }

    def _empty_result(self, reason: str) -> Dict:
        """
        Retorna resultado vazio com motivo.

        Args:
            reason: Razao pela qual nao ha classificacao.

        Returns:
            Dict com regime INDEFINIDO e motivo.
        """
        return {
            "regime": "INDEFINIDO",
            "label": "Indefinido",
            "description": reason,
            "color": "#78909C",
            "confidence": "N/A",
            "stats": {},
            "timestamp": datetime.now(),
            "lookback_periods": self.lookback_periods,
            "parameters": {},
        }

    def get_regime_info(self) -> Dict:
        """
        Retorna informacoes detalhadas sobre o regime atual.

        Inclui o regime, estatisticas, e abordagem sugerida.

        Returns:
            Dict com regime, details, e suggested_approach.
        """
        regime = self.detect_regime()
        approach = self.get_trading_recommendation()

        return {
            "regime": regime["regime"],
            "label": regime["label"],
            "description": regime["description"],
            "color": regime["color"],
            "confidence": regime["confidence"],
            "stats": regime["stats"],
            "suggested_approach": approach,
            "timestamp": regime["timestamp"],
        }

    def get_trading_recommendation(self) -> Dict:
        """
        Retorna a recomendacao de trading baseada no regime atual.

        Cada regime sugere uma abordagem diferente:
        - TENDENCIA: Operar a favor da tendencia
        - LATERAL: Operar reversoes nos extremos com stops curtos
        - VOLATIL: Reduzir tamanho, stops mais largos
        - TRANSICAO: Aguardar confirmacao de novo regime

        Returns:
            Dict com recomendacao, acao, stops e gerenciamento de risco.
        """
        regime = self._current_regime or self.detect_regime()
        regime_type = regime.get("regime", "INDEFINIDO")
        stats = regime.get("stats", {})

        recommendations = {
            "TENDENCIA_ALTA": {
                "approach": "Operar a favor da tendencia",
                "action": "Buscar entradas de COMPRA nos retrocessos. "
                          "Priorizar operacoes a favor do viés macro.",
                "stop_strategy": "Stops abaixo de suportes. "
                                 "Pode usar stops mais largos para acomodar retrocessos.",
                "position_size": "Tamanho normal ou ligeiramente aumentado.",
                "risk_level": "MODERADO-BAIXO",
                "color": "#00E676",
            },
            "TENDENCIA_BAIXA": {
                "approach": "Operar a favor da tendencia",
                "action": "Buscar entradas de VENDA nos altas. "
                          "Priorizar operacoes a favor do viés macro.",
                "stop_strategy": "Stops acima de resistencias. "
                                 "Pode usar stops mais largos para acomodar altas.",
                "position_size": "Tamanho normal ou ligeiramente aumentado.",
                "risk_level": "MODERADO-BAIXO",
                "color": "#FF1744",
            },
            "LATERAL": {
                "approach": "Operar reversoes nos extremos com stops curtos",
                "action": "Comprar proximo a suportes, vender proximo a resistencias. "
                          "Nao segurar posicoes por muito tempo.",
                "stop_strategy": "Stops curtos logo abaixo/acima dos niveis. "
                                 "Saida rapida se o nivel nao segurar.",
                "position_size": "Tamanho reduzido. Max 50% do normal.",
                "risk_level": "MODERADO",
                "color": "#FFD600",
            },
            "VOLATIL": {
                "approach": "Reduzir tamanho, stops mais largos",
                "action": "Operar apenas sinais muito fortes com alta confianca. "
                          "Evitar overtrading. Esperar clareza.",
                "stop_strategy": "Stops mais largos que o normal para acomodar "
                                 "oscilacoes. Nao usar stops justos.",
                "position_size": "Tamanho reduzido. Max 30% do normal.",
                "risk_level": "ALTO",
                "color": "#FF5722",
            },
            "TRANSICAO": {
                "approach": "Aguardar confirmacao de novo regime",
                "action": "Nao entrar em posicoes novas agora. "
                          "Fechar posicoes existentes ou protege-las. "
                          "O mercado esta mudando de contexto.",
                "stop_strategy": "Proteger posicoes existentes com stops apertados. "
                                 "Saida rapida em qualquer sinal contrario.",
                "position_size": "Zero ou minimo. Apenas protecao.",
                "risk_level": "MUITO ALTO",
                "color": "#FF9800",
            },
            "INDEFINIDO": {
                "approach": "Aguardar dados",
                "action": "Dados insuficientes para classificar o regime. "
                          "Continue coletando dados antes de operar.",
                "stop_strategy": "N/A — nao operar.",
                "position_size": "Zero.",
                "risk_level": "INDEFINIDO",
                "color": "#78909C",
            },
        }

        rec = recommendations.get(
            regime_type, recommendations["INDEFINIDO"]
        )

        # Adiciona contexto adicional baseado nas stats
        context = {}
        if stats:
            context["avg_score"] = stats.get("mean", 0)
            context["volatility"] = stats.get("std_dev", 0)
            context["score_range"] = stats.get("range", 0)

        return {
            "regime": regime_type,
            "approach": rec["approach"],
            "action": rec["action"],
            "stop_strategy": rec["stop_strategy"],
            "position_size": rec["position_size"],
            "risk_level": rec["risk_level"],
            "color": rec["color"],
            "context": context,
        }

    def get_status(self) -> Dict:
        """
        Retorna o status atual do detector para o dashboard.

        Returns:
            Dict com regime atual, recomendacao e historico.
        """
        regime = self._current_regime or self.detect_regime()
        recommendation = self.get_trading_recommendation()

        return {
            "enabled": self.enabled,
            "current_regime": regime["regime"],
            "regime_label": regime["label"],
            "regime_color": regime["color"],
            "confidence": regime["confidence"],
            "recommendation": recommendation,
            "history_size": len(self._score_history),
            "lookback_periods": self.lookback_periods,
        }

    def reset(self) -> None:
        """Reseta o detector, limpando historico e regime atual."""
        self._score_history = []
        self._current_regime = None
        logger.info("RegimeDetector resetado")
