"""
Score Smoother - EMA/SMA Suavizacao do Score Macro
====================================================
Aplica suavizacao Exponential Moving Average (EMA) ou Simple Moving
Average (SMA) ao score bruto para reduzir ruido e fornecer um sinal
mais estavel para tomada de decisao.

O score bruto pode oscilar rapidamente entre leituras devido a
volatilidade intrinseca dos ativos. O smoother reduz essas oscilacoes
preservando a direcao da tendencia.

v5.0 - Componente do sistema de macro scoring
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ScoreSmoother:
    """
    Suavizador de score via EMA ou SMA.

    O EMA da mais peso as leituras recentes, reagindo mais rapido a
    mudancas de tendencia, enquanto o SMA trata todas as leituras
    igualmente, fornecendo uma visao mais estavel.

    Formula EMA:
        ema = alpha * new_value + (1 - alpha) * prev_ema
        onde alpha = 2 / (periods + 1)

    Uso tipico:
        smoother = ScoreSmoother(config.SCORE_SMOOTHER_CONFIG)
        smoother.add_score(raw_score, timestamp)
        smoothed = smoother.get_smoothed_score()
    """

    def __init__(self, config: dict = None):
        """
        Inicializa o suavizador com parametros de configuracao.

        Args:
            config: Dict com configuracoes (SCORE_SMOOTHER_CONFIG).
                    Campos esperados:
                    - ema_period: periodo do EMA (default: 5)
                    - sma_period: periodo do SMA (default: 10)
                    - use_ema: True para EMA, False para SMA (default: True)
                    - max_history: maximo de entradas no historico (default: 500)
                    - enabled: ativa/desativa suavizacao (default: True)
        """
        self.config = config or {}
        self.ema_period = self.config.get("ema_period", 5)
        self.sma_period = self.config.get("sma_period", 10)
        self.use_ema = self.config.get("use_ema", True)
        self.max_history = self.config.get("max_history", 500)
        self.enabled = self.config.get("enabled", True)

        # Historico de scores brutos
        self._history: List[Dict] = []

        # Estado do EMA
        self._ema_initialized = False
        self._ema_value: Optional[float] = None

        # Constante de suavizacao EMA
        self._alpha = 2.0 / (self.ema_period + 1)

        logger.info(
            f"ScoreSmoother inicializado: mode={'EMA' if self.use_ema else 'SMA'}, "
            f"ema_period={self.ema_period}, sma_period={self.sma_period}, "
            f"alpha={self._alpha:.4f}, enabled={self.enabled}"
        )

    def add_score(self, raw_score: float, timestamp: datetime = None) -> None:
        """
        Adiciona uma nova leitura de score bruto ao historico.

        Atualiza o EMA incrementalmente para evitar recalcular
        toda vez. O primeiro valor inicializa o EMA.

        Args:
            raw_score: Score bruto entre -100 e +100.
            timestamp: Momento da leitura (default: agora).
        """
        if not self.enabled:
            return

        timestamp = timestamp or datetime.now()

        # Registra no historico
        entry = {
            "timestamp": timestamp,
            "raw_score": raw_score,
        }
        self._history.append(entry)

        # Limita historico
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

        # Atualiza EMA incrementalmente
        if not self._ema_initialized:
            # Primeiro valor inicializa o EMA
            self._ema_value = raw_score
            self._ema_initialized = True
        else:
            # EMA formula: ema = alpha * new + (1 - alpha) * prev_ema
            self._ema_value = (
                self._alpha * raw_score + (1 - self._alpha) * self._ema_value
            )

        logger.debug(
            f"Score adicionado: raw={raw_score:.2f}, "
            f"ema={self._ema_value:.2f}, "
            f"history_size={len(self._history)}"
        )

    def get_smoothed_score(self) -> Optional[float]:
        """
        Retorna o score suavizado (EMA ou SMA dependendo da config).

        Returns:
            Score suavizado ou None se nao ha dados suficientes.
        """
        if not self.enabled or not self._history:
            return None

        if self.use_ema:
            return self._get_ema()
        else:
            return self._get_sma()

    def _get_ema(self) -> Optional[float]:
        """
        Retorna o valor atual do EMA.

        Returns:
            Valor EMA ou None se nao inicializado.
        """
        if not self._ema_initialized or self._ema_value is None:
            return None
        return round(self._ema_value, 2)

    def _get_sma(self) -> Optional[float]:
        """
        Calcula e retorna o SMA baseado no periodo configurado.

        SMA = soma dos ultimos N valores / N

        Returns:
            Valor SMA ou None se nao ha dados suficientes.
        """
        if len(self._history) < self.sma_period:
            # Se nao tem dados suficientes, usa o que tem
            if not self._history:
                return None
            values = [h["raw_score"] for h in self._history]
            return round(sum(values) / len(values), 2)

        recent = self._history[-self.sma_period:]
        values = [h["raw_score"] for h in recent]
        return round(sum(values) / len(values), 2)

    def get_both(self) -> Dict:
        """
        Retorna um dict com score bruto, suavizado e delta EMA.

        O ema_delta indica a velocidade de mudanca do EMA:
        - Positivo: EMA subindo (score melhorando)
        - Negativo: EMA caindo (score piorando)
        - Zero: EMA estavel

        Returns:
            Dict com:
            - raw: ultimo score bruto
            - smoothed: score suavizado (EMA ou SMA)
            - ema_delta: diferenca entre EMA atual e anterior
            - ema_value: valor EMA atual
            - sma_value: valor SMA atual
            - history_size: tamanho do historico
            - mode: 'EMA' ou 'SMA'
        """
        if not self._history:
            return {
                "raw": None,
                "smoothed": None,
                "ema_delta": None,
                "ema_value": None,
                "sma_value": None,
                "history_size": 0,
                "mode": "EMA" if self.use_ema else "SMA",
            }

        raw = self._history[-1]["raw_score"]
        smoothed = self.get_smoothed_score()
        ema_value = self._get_ema()
        sma_value = self._get_sma()

        # Calcula delta do EMA (variacao entre as 2 ultimas posicoes)
        ema_delta = None
        if len(self._history) >= 2:
            # Recalcula EMA anterior para obter delta
            prev_ema = self._compute_ema_at(len(self._history) - 2)
            if prev_ema is not None and ema_value is not None:
                ema_delta = round(ema_value - prev_ema, 2)

        return {
            "raw": round(raw, 2),
            "smoothed": smoothed,
            "ema_delta": ema_delta,
            "ema_value": ema_value,
            "sma_value": sma_value,
            "history_size": len(self._history),
            "mode": "EMA" if self.use_ema else "SMA",
        }

    def _compute_ema_at(self, index: int) -> Optional[float]:
        """
        Computa o valor do EMA em uma posicao especifica do historico.

        Percorre o historico desde o inicio ate o indice dado,
        recalculando o EMA passo a passo.

        Args:
            index: Indice no historico (0-based).

        Returns:
            Valor EMA na posicao ou None se indice invalido.
        """
        if index < 0 or index >= len(self._history):
            return None

        ema = self._history[0]["raw_score"]
        for i in range(1, index + 1):
            ema = self._alpha * self._history[i]["raw_score"] + (1 - self._alpha) * ema

        return round(ema, 2)

    def get_history(self, last_n: int = None) -> List[Dict]:
        """
        Retorna historico de scores com scores suavizados.

        Args:
            last_n: Numero de entradas mais recentes (None = todas).

        Returns:
            Lista de dicts com raw_score, ema, sma, timestamp.
        """
        if not self._history:
            return []

        history = self._history if last_n is None else self._history[-last_n:]

        # Reconstruir EMA historico para cada ponto
        result = []
        running_ema = None

        start_idx = 0
        if last_n is not None:
            start_idx = max(0, len(self._history) - last_n)

        # Precisa computar EMA desde o inicio para ter valores corretos
        ema = self._history[0]["raw_score"]
        for i in range(len(self._history)):
            if i > 0:
                ema = (
                    self._alpha * self._history[i]["raw_score"]
                    + (1 - self._alpha) * ema
                )

            if i >= start_idx:
                # SMA na posicao i
                sma_start = max(0, i - self.sma_period + 1)
                sma_values = [
                    self._history[j]["raw_score"]
                    for j in range(sma_start, i + 1)
                ]
                sma = sum(sma_values) / len(sma_values)

                result.append({
                    "timestamp": self._history[i]["timestamp"],
                    "raw_score": round(self._history[i]["raw_score"], 2),
                    "ema": round(ema, 2),
                    "sma": round(sma, 2),
                })

        return result

    def reset(self) -> None:
        """
        Reseta o estado do suavizador, limpando historico e EMA.
        """
        self._history = []
        self._ema_initialized = False
        self._ema_value = None
        logger.info("ScoreSmoother resetado")

    def get_status(self) -> Dict:
        """
        Retorna status atual do suavizador para o dashboard.

        Returns:
            Dict com estado atual e parametros.
        """
        both = self.get_both()
        return {
            "enabled": self.enabled,
            "mode": both["mode"],
            "ema_period": self.ema_period,
            "sma_period": self.sma_period,
            "alpha": round(self._alpha, 4),
            "history_size": both["history_size"],
            "raw_score": both["raw"],
            "smoothed_score": both["smoothed"],
            "ema_delta": both["ema_delta"],
            "ema_initialized": self._ema_initialized,
        }
