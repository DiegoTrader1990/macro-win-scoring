"""
Price Reversal Detector - Divergencia Preco vs Score Macro
============================================================
Detecta quando o WIN esta se movendo CONTRA o score macro.
Este e o componente CHAVE que faltava quando "o macro estava baixista
mas o WIN so subiu apos a queda".

Cenarios detectados:
- DIVERGENCIA_ALTA_PRECO: Score < -25 mas WIN com momentum positivo
  em 2+ periodos → O indice esta subindo apesar do macro negativo
- DIVERGENCIA_BAIXA_PRECO: Score > +25 mas WIN com momentum negativo
  em 2+ periodos → O indice esta caindo apesar do macro positivo
- REVERSAO_ALTA_PRECO: Momentum do WIN muda de negativo para positivo
  enquanto score e baixista → Possivel virada de alta
- REVERSAO_BAIXA_PRECO: Momentum do WIN muda de positivo para negativo
  enquanto score e altista → Possivel virada de baixa

Forca: FORTE / MODERADA / INICIAL baseada na magnitude do momentum.

v5.0 - O recurso que faltava para capturar movimentos contra o macro
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PriceReversalDetector:
    """
    Detector de reversao baseado em preco vs score macro.

    Rastreia o preco do WIN e o score macro em paralelo. Quando o
    preco se move na direcao oposta ao score, uma divergencia de
    preco e detectada, sinalizando que o movimento do indice pode
    nao ser sustentado pelo cenario macro.

    Metodologia:
    1. Calcula momentum do WIN em multiplos periodos (rate of change)
    2. Compara a direcao do momentum com o score macro
    3. Se divergirem em 2+ periodos → divergencia confirmada
    4. Se momentum muda de sinal enquanto score e extremo → reversao
    5. Classifica a forca pela magnitude do momentum
    """

    def __init__(self, config: dict = None):
        """
        Inicializa o detector com parametros de configuracao.

        Args:
            config: Dict com configuracoes (PRICE_REVERSAL_CONFIG).
                    Campos esperados:
                    - enabled: ativa/desativa deteccao (default: True)
                    - momentum_periods: periodos para calculo de momentum (default: [3,5,10])
                    - score_threshold_bearish: score abaixo = baixista (default: -25)
                    - score_threshold_bullish: score acima = altista (default: 25)
                    - min_positive_periods: minimo de periodos com momentum favoravel (default: 2)
                    - strong_momentum_threshold: momentum acima = FORTE (default: 0.5)
                    - moderate_momentum_threshold: momentum acima = MODERADA (default: 0.2)
                    - max_history: maximo de entradas no historico (default: 500)
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.momentum_periods = self.config.get("momentum_periods", [3, 5, 10])
        self.score_threshold_bearish = self.config.get("score_threshold_bearish", -25)
        self.score_threshold_bullish = self.config.get("score_threshold_bullish", 25)
        self.min_positive_periods = self.config.get("min_positive_periods", 2)
        self.strong_momentum_threshold = self.config.get("strong_momentum_threshold", 0.5)
        self.moderate_momentum_threshold = self.config.get("moderate_momentum_threshold", 0.2)
        self.max_history = self.config.get("max_history", 500)

        # Historicos paralelos
        self._win_history: List[Dict] = []
        self._score_history: List[Dict] = []

        # Cache do ultimo resultado
        self._last_result: Optional[Dict] = None

        logger.info(
            f"PriceReversalDetector inicializado: periods={self.momentum_periods}, "
            f"score_bearish={self.score_threshold_bearish}, "
            f"score_bullish={self.score_threshold_bullish}, "
            f"enabled={self.enabled}"
        )

    def update_win_data(self, price: float, change_pct: float = None,
                        timestamp: datetime = None) -> None:
        """
        Registra uma nova leitura de preco/variacao do WIN.

        Args:
            price: Preco atual do WIN (em pontos).
            change_pct: Variacao percentual do WIN (opcional).
            timestamp: Momento da leitura (default: agora).
        """
        if not self.enabled:
            return

        timestamp = timestamp or datetime.now()

        entry = {
            "timestamp": timestamp,
            "price": price,
            "change_pct": change_pct,
        }
        self._win_history.append(entry)

        # Limita historico
        if len(self._win_history) > self.max_history:
            self._win_history = self._win_history[-self.max_history:]

        logger.debug(
            f"WIN data atualizado: price={price:.0f}, "
            f"change_pct={change_pct}, "
            f"history_size={len(self._win_history)}"
        )

    def update_score(self, score: float, delta: float = None,
                     timestamp: datetime = None) -> None:
        """
        Registra uma nova leitura do score macro.

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
            "delta": delta,
        }
        self._score_history.append(entry)

        # Limita historico
        if len(self._score_history) > self.max_history:
            self._score_history = self._score_history[-self.max_history:]

        logger.debug(
            f"Score atualizado: score={score:.2f}, delta={delta}, "
            f"history_size={len(self._score_history)}"
        )

    def _calculate_momentum(self, period: int) -> Optional[float]:
        """
        Calcula o momentum (rate of change) do WIN para um dado periodo.

        Rate of Change (ROC) = (preco_atual - preco_N_atras) / preco_N_atras * 100

        Args:
            period: Numero de leituras para tras.

        Returns:
            Taxa de variacao em percentual, ou None se dados insuficientes.
        """
        if len(self._win_history) <= period:
            return None

        current_price = self._win_history[-1]["price"]
        past_price = self._win_history[-(period + 1)]["price"]

        if past_price == 0:
            return None

        roc = (current_price - past_price) / past_price * 100
        return roc

    def _calculate_all_momentum(self) -> Dict[int, Optional[float]]:
        """
        Calcula momentum para todos os periodos configurados.

        Returns:
            Dict {periodo: valor_momentum} para cada periodo.
        """
        momenta = {}
        for period in self.momentum_periods:
            momenta[period] = self._calculate_momentum(period)
        return momenta

    def _determine_strength(self, momenta: Dict[int, Optional[float]],
                            positive_count: int) -> str:
        """
        Determina a forca da divergencia/reversao baseada no momentum.

        Criterios:
        - FORTE: 3+ periodos com momentum favoravel E magnitude > strong_threshold
        - MODERADA: 2+ periodos com momentum favoravel E magnitude > moderate_threshold
        - INICIAL: 2+ periodos com momentum favoravel (magnitude menor)

        Args:
            momenta: Dict com momentum por periodo.
            positive_count: Quantos periodos tem momentum na direcao esperada.

        Returns:
            'FORTE', 'MODERADA' ou 'INICIAL'.
        """
        # Calcula magnitude media dos momenta validos
        valid_momenta = [abs(m) for m in momenta.values() if m is not None]
        if not valid_momenta:
            return "INICIAL"

        avg_magnitude = sum(valid_momenta) / len(valid_momenta)
        max_magnitude = max(valid_momenta)

        if positive_count >= 3 and max_magnitude > self.strong_momentum_threshold:
            return "FORTE"
        elif positive_count >= 2 and max_magnitude > self.moderate_momentum_threshold:
            return "MODERADA"
        elif positive_count >= 2:
            return "INICIAL"
        else:
            return "INICIAL"

    def check_price_reversal(self) -> Dict:
        """
        Metodo principal de deteccao de reversao baseada em preco.

        Logica:
        1. Calcula momentum do WIN em multiplos periodos
        2. Verifica se score e baixista/altista (thresholds)
        3. Conta periodos com momentum divergente do score
        4. Se 2+ periodos divergem → divergencia de preco
        5. Verifica mudanca de sinal do momentum → reversao

        Returns:
            Dict com tipo de reversao, forca, detalhes e acao sugerida.
        """
        if not self.enabled:
            return self._empty_result("Sistema desabilitado")

        # Precisa de pelo menos o maior periodo + 1 leituras
        max_period = max(self.momentum_periods)
        if len(self._win_history) <= max_period:
            return self._empty_result(
                f"Dados insuficientes ({len(self._win_history)}/{max_period + 1})"
            )

        if not self._score_history:
            return self._empty_result("Sem dados de score")

        # Pega score e delta mais recentes
        current_score = self._score_history[-1]["score"]
        current_delta = self._score_history[-1].get("delta", 0)

        # Calcula momentum em todos os periodos
        momenta = self._calculate_all_momentum()

        # Verifica momentum anterior para deteccao de reversao
        prev_momenta = self._get_previous_momenta()

        # Conta periodos com momentum positivo e negativo
        positive_momentum_count = sum(
            1 for m in momenta.values() if m is not None and m > 0
        )
        negative_momentum_count = sum(
            1 for m in momenta.values() if m is not None and m < 0
        )

        # === LOGICA DE DETECCAO ===

        # 1. DIVERGENCIA DE ALTA NO PRECO
        # Score baixista mas WIN subindo em 2+ periodos
        if current_score < self.score_threshold_bearish and positive_momentum_count >= self.min_positive_periods:
            strength = self._determine_strength(momenta, positive_momentum_count)
            result = self._build_divergence_result(
                divergence_type="DIVERGENCIA_ALTA_PRECO",
                label="DIVERGENCIA DE ALTA (PRECO)",
                score=current_score,
                momenta=momenta,
                positive_count=positive_momentum_count,
                strength=strength,
                direction="ALTA",
                description=(
                    f"Score baixista ({current_score:+.0f}) mas WIN subindo em "
                    f"{positive_momentum_count}/{len(self.momentum_periods)} periodos. "
                    f"O indice descolou do macro — CUIDADO com venda."
                ),
                action=(
                    "Nao confie cegamente no score de venda. O WIN esta mostrando "
                    "forca real. Considere reduzir posicao vendida ou buscar compra "
                    "com stop curto."
                ),
            )
            self._last_result = result
            return result

        # 2. DIVERGENCIA DE BAIXA NO PRECO
        # Score altista mas WIN caindo em 2+ periodos
        if current_score > self.score_threshold_bullish and negative_momentum_count >= self.min_positive_periods:
            strength = self._determine_strength(momenta, negative_momentum_count)
            result = self._build_divergence_result(
                divergence_type="DIVERGENCIA_BAIXA_PRECO",
                label="DIVERGENCIA DE BAIXA (PRECO)",
                score=current_score,
                momenta=momenta,
                positive_count=negative_momentum_count,
                strength=strength,
                direction="BAIXA",
                description=(
                    f"Score altista ({current_score:+.0f}) mas WIN caindo em "
                    f"{negative_momentum_count}/{len(self.momentum_periods)} periodos. "
                    f"O indice descolou do macro — CUIDADO com compra."
                ),
                action=(
                    "Nao confie cegamente no score de compra. O WIN esta mostrando "
                    "fraqueza real. Considere reduzir posicao comprada ou buscar venda "
                    "com stop curto."
                ),
            )
            self._last_result = result
            return result

        # 3. REVERSAO DE ALTA NO PRECO
        # Momentum do WIN mudou de negativo para positivo enquanto score e baixista
        if current_score < self.score_threshold_bearish:
            reversal = self._check_momentum_reversal(
                prev_momenta, momenta, expected_sign_change="neg_to_pos"
            )
            if reversal:
                strength = self._determine_strength(momenta, positive_momentum_count)
                result = self._build_reversal_result(
                    reversal_type="REVERSAO_ALTA_PRECO",
                    label="REVERSAO DE ALTA (PRECO)",
                    score=current_score,
                    momenta=momenta,
                    prev_momenta=prev_momenta,
                    strength=max(strength, "MODERADA") if reversal["count"] >= 2 else "INICIAL",
                    direction="ALTA",
                    description=(
                        f"Score baixista ({current_score:+.0f}) mas momentum do WIN "
                        f"virou positivo em {reversal['count']} periodos. "
                        f"Possivel inicio de virada de alta."
                    ),
                    action=(
                        "Atencao: o WIN pode estar virando para alta apesar do macro "
                        "negativo. Aguarde confirmacao mas esteja pronto para compra."
                    ),
                )
                self._last_result = result
                return result

        # 4. REVERSAO DE BAIXA NO PRECO
        # Momentum do WIN mudou de positivo para negativo enquanto score e altista
        if current_score > self.score_threshold_bullish:
            reversal = self._check_momentum_reversal(
                prev_momenta, momenta, expected_sign_change="pos_to_neg"
            )
            if reversal:
                strength = self._determine_strength(momenta, negative_momentum_count)
                result = self._build_reversal_result(
                    reversal_type="REVERSAO_BAIXA_PRECO",
                    label="REVERSAO DE BAIXA (PRECO)",
                    score=current_score,
                    momenta=momenta,
                    prev_momenta=prev_momenta,
                    strength=max(strength, "MODERADA") if reversal["count"] >= 2 else "INICIAL",
                    direction="BAIXA",
                    description=(
                        f"Score altista ({current_score:+.0f}) mas momentum do WIN "
                        f"virou negativo em {reversal['count']} periodos. "
                        f"Possivel inicio de virada de baixa."
                    ),
                    action=(
                        "Atencao: o WIN pode estar virando para baixa apesar do macro "
                        "positivo. Proteja posicoes compradas com stops."
                    ),
                )
                self._last_result = result
                return result

        # Nenhuma divergencia/reversao detectada
        result = {
            "detected": False,
            "type": "SEM_REVERSAO",
            "label": "Sem divergencia de preco",
            "timestamp": datetime.now(),
            "current_score": current_score,
            "momenta": {k: round(v, 4) if v is not None else None for k, v in momenta.items()},
            "description": "Preco e score macro estao alinhados ou sem divergencia significativa.",
            "action": "Continue operando normalmente com base no score.",
            "severity": "none",
            "color": "#78909C",
        }
        self._last_result = result
        return result

    def _get_previous_momenta(self) -> Dict[int, Optional[float]]:
        """
        Calcula os momenta da leitura anterior (uma posicao atras).

        Returns:
            Dict com momentum por periodo da leitura anterior.
        """
        # Temporariamente remove o ultimo ponto para calcular momenta anteriores
        if len(self._win_history) < 2:
            return {p: None for p in self.momentum_periods}

        # Salva e restaura
        last = self._win_history.pop()
        prev_momenta = self._calculate_all_momentum()
        self._win_history.append(last)
        return prev_momenta

    def _check_momentum_reversal(self, prev_momenta: Dict[int, Optional[float]],
                                  current_momenta: Dict[int, Optional[float]],
                                  expected_sign_change: str) -> Optional[Dict]:
        """
        Verifica se houve mudanca de sinal no momentum entre leituras.

        Args:
            prev_momenta: Momenta da leitura anterior.
            current_momenta: Momenta da leitura atual.
            expected_sign_change: 'neg_to_pos' ou 'pos_to_neg'.

        Returns:
            Dict com count de reversoes e periodos, ou None.
        """
        reversal_count = 0
        reversal_periods = []

        for period in self.momentum_periods:
            prev_m = prev_momenta.get(period)
            curr_m = current_momenta.get(period)

            if prev_m is None or curr_m is None:
                continue

            if expected_sign_change == "neg_to_pos":
                if prev_m < 0 and curr_m > 0:
                    reversal_count += 1
                    reversal_periods.append(period)
            elif expected_sign_change == "pos_to_neg":
                if prev_m > 0 and curr_m < 0:
                    reversal_count += 1
                    reversal_periods.append(period)

        if reversal_count > 0:
            return {
                "count": reversal_count,
                "periods": reversal_periods,
            }
        return None

    def _build_divergence_result(self, divergence_type: str, label: str,
                                  score: float, momenta: Dict,
                                  positive_count: int, strength: str,
                                  direction: str, description: str,
                                  action: str) -> Dict:
        """
        Constroi o dict de resultado para divergencia de preco.

        Args:
            divergence_type: Tipo tecnico da divergencia.
            label: Label legivel para o dashboard.
            score: Score macro atual.
            momenta: Momentum por periodo.
            positive_count: Periodos com momentum na direcao esperada.
            strength: FORTE/MODERADA/INICIAL.
            direction: ALTA ou BAIXA.
            description: Descricao humana do cenario.
            action: Acao sugerida.

        Returns:
            Dict completo com resultado da divergencia.
        """
        severity_map = {"FORTE": "high", "MODERADA": "medium", "INICIAL": "low"}
        color_map = {
            "ALTA": {"FORTE": "#00E676", "MODERADA": "#66BB6A", "INICIAL": "#FFD600"},
            "BAIXA": {"FORTE": "#FF1744", "MODERADA": "#EF5350", "INICIAL": "#FFD600"},
        }

        return {
            "detected": True,
            "type": divergence_type,
            "label": label,
            "timestamp": datetime.now(),
            "current_score": round(score, 2),
            "momenta": {k: round(v, 4) if v is not None else None for k, v in momenta.items()},
            "aligned_periods": positive_count,
            "total_periods": len(self.momentum_periods),
            "strength": strength,
            "direction": direction,
            "description": description,
            "action": action,
            "severity": severity_map.get(strength, "low"),
            "color": color_map.get(direction, {}).get(strength, "#FFD600"),
        }

    def _build_reversal_result(self, reversal_type: str, label: str,
                                score: float, momenta: Dict,
                                prev_momenta: Dict, strength: str,
                                direction: str, description: str,
                                action: str) -> Dict:
        """
        Constroi o dict de resultado para reversao de momentum.

        Args:
            reversal_type: Tipo tecnico da reversao.
            label: Label legivel para o dashboard.
            score: Score macro atual.
            momenta: Momentum atual por periodo.
            prev_momenta: Momentum anterior por periodo.
            strength: FORTE/MODERADA/INICIAL.
            direction: ALTA ou BAIXA.
            description: Descricao humana do cenario.
            action: Acao sugerida.

        Returns:
            Dict completo com resultado da reversao.
        """
        severity_map = {"FORTE": "high", "MODERADA": "medium", "INICIAL": "low"}
        color_map = {
            "ALTA": {"FORTE": "#00E676", "MODERADA": "#66BB6A", "INICIAL": "#FFD600"},
            "BAIXA": {"FORTE": "#FF1744", "MODERADA": "#EF5350", "INICIAL": "#FFD600"},
        }

        return {
            "detected": True,
            "type": reversal_type,
            "label": label,
            "timestamp": datetime.now(),
            "current_score": round(score, 2),
            "momenta": {k: round(v, 4) if v is not None else None for k, v in momenta.items()},
            "prev_momenta": {k: round(v, 4) if v is not None else None for k, v in prev_momenta.items()},
            "strength": strength,
            "direction": direction,
            "description": description,
            "action": action,
            "severity": severity_map.get(strength, "low"),
            "color": color_map.get(direction, {}).get(strength, "#FFD600"),
        }

    def _empty_result(self, reason: str) -> Dict:
        """
        Retorna resultado vazio com motivo.

        Args:
            reason: Razao pela qual nao ha deteccao.

        Returns:
            Dict com tipo NEUTRO e motivo.
        """
        return {
            "detected": False,
            "type": "SEM_REVERSAO",
            "label": "Sem divergencia de preco",
            "timestamp": datetime.now(),
            "current_score": self._score_history[-1]["score"] if self._score_history else None,
            "momenta": {},
            "description": reason,
            "action": "Aguardando dados suficientes.",
            "severity": "none",
            "color": "#78909C",
        }

    def get_status(self) -> Dict:
        """
        Retorna o status atual do detector para o dashboard.

        Returns:
            Dict com ultimo resultado, tamanhos de historico, etc.
        """
        result = self._last_result or self._empty_result("Nenhuma verificacao realizada")

        return {
            "enabled": self.enabled,
            "win_history_size": len(self._win_history),
            "score_history_size": len(self._score_history),
            "last_reversal": result,
            "momentum_periods": self.momentum_periods,
            "current_momenta": {
                k: round(v, 4) if v is not None else None
                for k, v in self._calculate_all_momentum().items()
            } if len(self._win_history) > max(self.momentum_periods) else {},
        }

    def reset(self) -> None:
        """Reseta o detector, limpando todos os historicos."""
        self._win_history = []
        self._score_history = []
        self._last_result = None
        logger.info("PriceReversalDetector resetado")
