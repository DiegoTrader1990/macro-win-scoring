"""
Signal Manager - Cooldown + Confluence Filter
================================================
Gerencia a emissao de sinais aplicando:
1. Cooldown: Impede sinais repetidos do mesmo tipo ou direcao
   dentro de um intervalo configuravel.
2. Confluence: Verifica multiplos filtros antes de emitir um sinal.
   Se nao houver confluencia suficiente, o sinal e rebaixado
   (ex: COMPRA → COMPRA_CAUTELA).

Filtros de confluencia:
- score_zone: Score esta em zona consistente com o sinal
- delta_direction: Delta confirma a direcao do sinal
- momentum_confirm: Momentum confirma a direcao
- not_in_divergence: Nao ha divergencia contraria ao sinal
- recovery_confirmed: Se ha recuperacao, ela confirma o sinal

v5.0 - Componente do sistema de macro scoring
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SignalManager:
    """
    Gerenciador de sinais com cooldown e filtro de confluencia.

    Garante que sinais nao sejam emitidos em excesso (spam) e que
    apenas sinais com confirmacao de multiplos fatores sejam emitidos
    com confianca total. Sinais sem confluencia suficiente sao
    rebaixados para cautela.

    Uso tipico:
        manager = SignalManager(config.SIGNAL_FILTER_CONFIG)
        result = manager.process_signal(
            signal_type="COMPRA", score=45, delta=8,
            sector_data={...}, divergence=None, recovery=None
        )
        # result["final_action"] indica acao final apos filtro
    """

    # Mapeamento de sinais para direcao
    SIGNAL_DIRECTIONS = {
        "COMPRA_FORTE": "LONG",
        "COMPRA": "LONG",
        "COMPRA_CAUTELA": "LONG",
        "RECUPERACAO_FORTE": "LONG",
        "RECUPERACAO": "LONG",
        "RECUPERACAO_INICIAL": "LONG",
        "REVERSAO_ALTA": "LONG",
        "REVERSAO_ALTA_PRECO": "LONG",
        "DIVERGENCIA_ALTA_PRECO": "LONG",
        "VENDA_FORTE": "SHORT",
        "VENDA": "SHORT",
        "VENDA_CAUTELA": "SHORT",
        "REVERSAO_BAIXA_INTRADAY": "SHORT",
        "REVERSAO_BAIXA": "SHORT",
        "REVERSAO_BAIXA_PRECO": "SHORT",
        "DIVERGENCIA_BAIXA_PRECO": "SHORT",
        "NEUTRO": "FLAT",
    }

    # Downgrade de sinais quando confluencia insuficiente
    SIGNAL_DOWNGRADE = {
        "COMPRA_FORTE": "COMPRA_CAUTELA",
        "COMPRA": "COMPRA_CAUTELA",
        "VENDA_FORTE": "VENDA_CAUTELA",
        "VENDA": "VENDA_CAUTELA",
        "RECUPERACAO_FORTE": "RECUPERACAO_INICIAL",
        "RECUPERACAO": "RECUPERACAO_INICIAL",
        "REVERSAO_ALTA": "COMPRA_CAUTELA",
        "REVERSAO_BAIXA": "VENDA_CAUTELA",
        "REVERSAO_BAIXA_INTRADAY": "VENDA_CAUTELA",
        "REVERSAO_ALTA_PRECO": "COMPRA_CAUTELA",
        "REVERSAO_BAIXA_PRECO": "VENDA_CAUTELA",
        "DIVERGENCIA_ALTA_PRECO": "COMPRA_CAUTELA",
        "DIVERGENCIA_BAIXA_PRECO": "VENDA_CAUTELA",
    }

    # Sinais que nao sofrem downgrade
    NO_DOWNGRADE = {"COMPRA_CAUTELA", "VENDA_CAUTELA", "NEUTRO",
                     "RECUPERACAO_INICIAL"}

    def __init__(self, config: dict = None):
        """
        Inicializa o gerenciador de sinais.

        Args:
            config: Dict com configuracoes (SIGNAL_FILTER_CONFIG).
                    Campos esperados:
                    - enabled: ativa/desativa filtro (default: True)
                    - cooldown_same_type_seconds: cooldown por tipo (default: 300)
                    - cooldown_same_direction_seconds: cooldown por direcao (default: 120)
                    - min_confluence_filters: minimo de filtros para sinal forte (default: 3)
                    - filters: dict com filtros habilitados
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.cooldown_same_type = self.config.get("cooldown_same_type_seconds", 300)
        self.cooldown_same_direction = self.config.get("cooldown_same_direction_seconds", 120)
        self.min_confluence = self.config.get("min_confluence_filters", 3)
        self.filters_config = self.config.get("filters", {
            "score_zone": True,
            "delta_direction": True,
            "momentum_confirm": True,
            "not_in_divergence": True,
            "recovery_confirmed": True,
        })

        # Registro de ultimos sinais por tipo e direcao
        self._last_signal_by_type: Dict[str, datetime] = {}
        self._last_signal_by_direction: Dict[str, datetime] = {}

        # Historico de sinais processados
        self._signal_history: List[Dict] = []
        self._max_history = 200

        logger.info(
            f"SignalManager inicializado: cooldown_type={self.cooldown_same_type}s, "
            f"cooldown_dir={self.cooldown_same_direction}s, "
            f"min_confluence={self.min_confluence}, "
            f"enabled={self.enabled}"
        )

    def process_signal(self, signal_type: str, score: float,
                       delta: float = None, sector_data: dict = None,
                       divergence: dict = None, recovery: dict = None) -> Dict:
        """
        Processa um sinal aplicando cooldown e filtros de confluencia.

        Etapas:
        1. Verifica cooldown por tipo de sinal
        2. Verifica cooldown por direcao
        3. Avalia filtros de confluencia
        4. Se confluencia < minimo → downgrade
        5. Retorna sinal final com detalhes

        Args:
            signal_type: Tipo do sinal (ex: "COMPRA", "VENDA_FORTE").
            score: Score macro atual.
            delta: Variacao do score.
            sector_data: Dados setoriais (opcional).
            divergence: Resultado da deteccao de divergencia (opcional).
            recovery: Resultado da deteccao de recuperacao (opcional).

        Returns:
            Dict com signal_type, passed_filters, confluence_count,
            was_cooldown, final_action e detalhes.
        """
        if not self.enabled:
            return self._build_result(
                signal_type=signal_type,
                passed_filters=[],
                confluence_count=0,
                was_cooldown=False,
                final_action=signal_type,
                reason="Sistema desabilitado — sinal passado direto",
            )

        now = datetime.now()

        # 1. Verifica cooldown por tipo
        cooldown_type_remaining = self._check_cooldown_type(signal_type, now)
        if cooldown_type_remaining > 0:
            result = self._build_result(
                signal_type=signal_type,
                passed_filters=[],
                confluence_count=0,
                was_cooldown=True,
                final_action="SUPRESSED",
                reason=f"Cooldown por tipo: {cooldown_type_remaining:.0f}s restantes",
            )
            result["cooldown_remaining"] = cooldown_type_remaining
            self._record_signal(result, now)
            return result

        # 2. Verifica cooldown por direcao
        direction = self.SIGNAL_DIRECTIONS.get(signal_type, "FLAT")
        if direction != "FLAT":
            cooldown_dir_remaining = self._check_cooldown_direction(direction, now)
            if cooldown_dir_remaining > 0:
                result = self._build_result(
                    signal_type=signal_type,
                    passed_filters=[],
                    confluence_count=0,
                    was_cooldown=True,
                    final_action="SUPRESSED",
                    reason=f"Cooldown por direcao ({direction}): {cooldown_dir_remaining:.0f}s restantes",
                )
                result["cooldown_remaining"] = cooldown_dir_remaining
                self._record_signal(result, now)
                return result

        # 3. Avalia filtros de confluencia
        passed_filters, filter_details = self._evaluate_confluence_filters(
            signal_type=signal_type,
            score=score,
            delta=delta,
            sector_data=sector_data,
            divergence=divergence,
            recovery=recovery,
        )

        confluence_count = len(passed_filters)

        # 4. Determina acao final
        final_action = signal_type
        reason = ""

        if signal_type in self.NO_DOWNGRADE or signal_type == "NEUTRO":
            # Sinais de cautela ou neutro nao sao rebaixados
            final_action = signal_type
            reason = "Sinal de cautela/neutro — sem downgrade aplicavel"
        elif confluence_count < self.min_confluence:
            # Confluencia insuficiente → downgrade
            final_action = self.SIGNAL_DOWNGRADE.get(signal_type, signal_type)
            reason = (
                f"Confluencia insuficiente ({confluence_count}/{self.min_confluence}). "
                f"Sinal rebaixado de {signal_type} para {final_action}."
            )
            logger.info(
                f"Signal downgrade: {signal_type} → {final_action} "
                f"(confluence={confluence_count}/{self.min_confluence})"
            )
        else:
            delta_str = f"{delta:+.1f}" if delta is not None else "N/A"
            reason = (
                f"Sinal confirmado com {confluence_count} filtros de confluencia. "
                f"Score: {score:+.1f}, Delta: {delta_str}."
            )

        # 5. Atualiza cooldowns
        self._last_signal_by_type[signal_type] = now
        if direction != "FLAT":
            self._last_signal_by_direction[direction] = now

        # 6. Constroi resultado
        result = self._build_result(
            signal_type=signal_type,
            passed_filters=passed_filters,
            confluence_count=confluence_count,
            was_cooldown=False,
            final_action=final_action,
            reason=reason,
            filter_details=filter_details,
            score=score,
            delta=delta,
            direction=direction,
        )

        self._record_signal(result, now)
        return result

    def _check_cooldown_type(self, signal_type: str, now: datetime) -> float:
        """
        Verifica se ha cooldown ativo para o tipo de sinal.

        Args:
            signal_type: Tipo do sinal.
            now: Timestamp atual.

        Returns:
            Segundos restantes de cooldown (0 se livre).
        """
        last_time = self._last_signal_by_type.get(signal_type)
        if last_time is None:
            return 0

        elapsed = (now - last_time).total_seconds()
        remaining = self.cooldown_same_type - elapsed
        return max(0, remaining)

    def _check_cooldown_direction(self, direction: str, now: datetime) -> float:
        """
        Verifica se ha cooldown ativo para a direcao.

        Args:
            direction: Direcao do sinal (LONG/SHORT).
            now: Timestamp atual.

        Returns:
            Segundos restantes de cooldown (0 se livre).
        """
        last_time = self._last_signal_by_direction.get(direction)
        if last_time is None:
            return 0

        elapsed = (now - last_time).total_seconds()
        remaining = self.cooldown_same_direction - elapsed
        return max(0, remaining)

    def _evaluate_confluence_filters(self, signal_type: str, score: float,
                                      delta: float = None,
                                      sector_data: dict = None,
                                      divergence: dict = None,
                                      recovery: dict = None) -> tuple:
        """
        Avalia cada filtro de confluencia habilitado.

        Filtros:
        - score_zone: Score esta em zona consistente com o sinal
          (LONG: score > 0, SHORT: score < 0)
        - delta_direction: Delta confirma a direcao do sinal
          (LONG: delta > 0, SHORT: delta < 0)
        - momentum_confirm: Momentum confirmado via setor
          (se setor majoritario esta na mesma direcao)
        - not_in_divergence: Nao ha divergencia contraria ao sinal
          (LONG: sem divergencia baixista, SHORT: sem divergencia altista)
        - recovery_confirmed: Se ha recuperacao, ela confirma o sinal
          (LONG com recuperacao = confirmacao)

        Args:
            signal_type: Tipo do sinal.
            score: Score macro.
            delta: Variacao do score.
            sector_data: Dados setoriais.
            divergence: Resultado de divergencia.
            recovery: Resultado de recuperacao.

        Returns:
            Tupla (lista_filtros_passados, dict_detalhes_filtros).
        """
        passed = []
        details = {}
        direction = self.SIGNAL_DIRECTIONS.get(signal_type, "FLAT")

        # Filtro 1: score_zone
        if self.filters_config.get("score_zone", True):
            if direction == "LONG" and score > 0:
                passed.append("score_zone")
                details["score_zone"] = {"passed": True, "reason": f"Score {score:+.1f} > 0"}
            elif direction == "SHORT" and score < 0:
                passed.append("score_zone")
                details["score_zone"] = {"passed": True, "reason": f"Score {score:+.1f} < 0"}
            elif direction == "FLAT":
                passed.append("score_zone")
                details["score_zone"] = {"passed": True, "reason": "Sinal neutro"}
            else:
                details["score_zone"] = {
                    "passed": False,
                    "reason": f"Score {score:+.1f} inconsistente com {direction}",
                }

        # Filtro 2: delta_direction
        if self.filters_config.get("delta_direction", True):
            if delta is not None:
                if direction == "LONG" and delta > 0:
                    passed.append("delta_direction")
                    details["delta_direction"] = {"passed": True, "reason": f"Delta {delta:+.1f} > 0"}
                elif direction == "SHORT" and delta < 0:
                    passed.append("delta_direction")
                    details["delta_direction"] = {"passed": True, "reason": f"Delta {delta:+.1f} < 0"}
                elif direction == "FLAT":
                    passed.append("delta_direction")
                    details["delta_direction"] = {"passed": True, "reason": "Sinal neutro"}
                else:
                    details["delta_direction"] = {
                        "passed": False,
                        "reason": f"Delta {delta:+.1f} nao confirma {direction}",
                    }
            else:
                details["delta_direction"] = {"passed": False, "reason": "Delta indisponivel"}

        # Filtro 3: momentum_confirm
        if self.filters_config.get("momentum_confirm", True):
            if sector_data and isinstance(sector_data, dict):
                # Verifica se maioria dos setores confirma
                positive_sectors = sum(
                    1 for v in sector_data.values()
                    if isinstance(v, dict) and v.get("normalized", 0) > 0
                )
                negative_sectors = sum(
                    1 for v in sector_data.values()
                    if isinstance(v, dict) and v.get("normalized", 0) < 0
                )
                total_sectors = positive_sectors + negative_sectors

                if total_sectors > 0:
                    if direction == "LONG" and positive_sectors > negative_sectors:
                        passed.append("momentum_confirm")
                        details["momentum_confirm"] = {
                            "passed": True,
                            "reason": f"{positive_sectors}/{total_sectors} setores positivos",
                        }
                    elif direction == "SHORT" and negative_sectors > positive_sectors:
                        passed.append("momentum_confirm")
                        details["momentum_confirm"] = {
                            "passed": True,
                            "reason": f"{negative_sectors}/{total_sectors} setores negativos",
                        }
                    else:
                        details["momentum_confirm"] = {
                            "passed": False,
                            "reason": f"Setores nao confirmam {direction} "
                                      f"(+:{positive_sectors} -:{negative_sectors})",
                        }
                else:
                    details["momentum_confirm"] = {
                        "passed": False,
                        "reason": "Sem dados setoriais suficientes",
                    }
            else:
                # Sem dados setoriais, nao conta como falha nem como pass
                details["momentum_confirm"] = {
                    "passed": False,
                    "reason": "Dados setoriais indisponiveis",
                }

        # Filtro 4: not_in_divergence
        if self.filters_config.get("not_in_divergence", True):
            if divergence and isinstance(divergence, dict):
                div_type = divergence.get("type", "")
                # LONG: nao pode ter divergencia baixista
                # SHORT: nao pode ter divergencia altista
                if direction == "LONG" and "BAIXA" in div_type:
                    details["not_in_divergence"] = {
                        "passed": False,
                        "reason": f"Divergencia contraria: {div_type}",
                    }
                elif direction == "SHORT" and "ALTA" in div_type:
                    details["not_in_divergence"] = {
                        "passed": False,
                        "reason": f"Divergencia contraria: {div_type}",
                    }
                else:
                    passed.append("not_in_divergence")
                    details["not_in_divergence"] = {
                        "passed": True,
                        "reason": "Sem divergencia contraria",
                    }
            else:
                # Sem divergencia detectada = filtro passa
                passed.append("not_in_divergence")
                details["not_in_divergence"] = {
                    "passed": True,
                    "reason": "Sem divergencia detectada",
                }

        # Filtro 5: recovery_confirmed
        if self.filters_config.get("recovery_confirmed", True):
            if recovery and isinstance(recovery, dict):
                recovery_detected = recovery.get("detected", False)
                if direction == "LONG" and recovery_detected:
                    passed.append("recovery_confirmed")
                    details["recovery_confirmed"] = {
                        "passed": True,
                        "reason": f"Recuperacao confirmada: {recovery.get('strength', 'N/A')}",
                    }
                elif direction == "SHORT" and not recovery_detected:
                    passed.append("recovery_confirmed")
                    details["recovery_confirmed"] = {
                        "passed": True,
                        "reason": "Sem recuperacao (confirma venda)",
                    }
                elif direction == "LONG" and not recovery_detected:
                    # Nao ter recuperacao num sinal LONG nao e falha,
                    # e apenas ausencia de confirmacao extra
                    details["recovery_confirmed"] = {
                        "passed": False,
                        "reason": "Sem recuperacao detectada para confirmar compra",
                    }
                else:
                    details["recovery_confirmed"] = {
                        "passed": False,
                        "reason": "Recuperacao ativa contradiz sinal de venda",
                    }
            else:
                # Sem dados de recuperacao = filtro passa neutralmente
                passed.append("recovery_confirmed")
                details["recovery_confirmed"] = {
                    "passed": True,
                    "reason": "Dados de recuperacao indisponiveis (neutro)",
                }

        return passed, details

    def _build_result(self, signal_type: str, passed_filters: List[str],
                      confluence_count: int, was_cooldown: bool,
                      final_action: str, reason: str,
                      filter_details: dict = None,
                      score: float = None, delta: float = None,
                      direction: str = None) -> Dict:
        """
        Constroi o dict de resultado do processamento de sinal.

        Args:
            signal_type: Tipo original do sinal.
            passed_filters: Lista de filtros que passaram.
            confluence_count: Numero de filtros que passaram.
            was_cooldown: Se o sinal foi suprimido por cooldown.
            final_action: Acao final apos processamento.
            reason: Razao da decisao.
            filter_details: Detalhes de cada filtro.
            score: Score macro.
            delta: Variacao do score.
            direction: Direcao do sinal (LONG/SHORT/FLAT).

        Returns:
            Dict completo com resultado do processamento.
        """
        return {
            "signal_type": signal_type,
            "direction": direction or self.SIGNAL_DIRECTIONS.get(signal_type, "FLAT"),
            "passed_filters": passed_filters,
            "confluence_count": confluence_count,
            "was_cooldown": was_cooldown,
            "final_action": final_action,
            "reason": reason,
            "filter_details": filter_details or {},
            "score": score,
            "delta": delta,
            "timestamp": datetime.now(),
            "downgraded": signal_type != final_action and not was_cooldown,
        }

    def _record_signal(self, result: Dict, timestamp: datetime) -> None:
        """
        Registra o sinal processado no historico.

        Args:
            result: Resultado do processamento.
            timestamp: Momento do processamento.
        """
        self._signal_history.append({**result, "timestamp": timestamp})
        if len(self._signal_history) > self._max_history:
            self._signal_history = self._signal_history[-self._max_history:]

    def get_cooldown_status(self) -> Dict:
        """
        Retorna o status de cooldown para cada tipo e direcao de sinal.

        Returns:
            Dict com cooldowns restantes por tipo e direcao.
        """
        now = datetime.now()

        type_cooldowns = {}
        for signal_type, last_time in self._last_signal_by_type.items():
            elapsed = (now - last_time).total_seconds()
            remaining = max(0, self.cooldown_same_type - elapsed)
            type_cooldowns[signal_type] = {
                "last_signal": last_time.isoformat(),
                "remaining_seconds": round(remaining, 1),
                "active": remaining > 0,
            }

        direction_cooldowns = {}
        for direction, last_time in self._last_signal_by_direction.items():
            elapsed = (now - last_time).total_seconds()
            remaining = max(0, self.cooldown_same_direction - elapsed)
            direction_cooldowns[direction] = {
                "last_signal": last_time.isoformat(),
                "remaining_seconds": round(remaining, 1),
                "active": remaining > 0,
            }

        return {
            "type_cooldowns": type_cooldowns,
            "direction_cooldowns": direction_cooldowns,
            "cooldown_same_type_seconds": self.cooldown_same_type,
            "cooldown_same_direction_seconds": self.cooldown_same_direction,
        }

    def get_recent_signals(self, last_n: int = 20) -> List[Dict]:
        """
        Retorna os sinais mais recentes processados.

        Args:
            last_n: Numero de sinais a retornar.

        Returns:
            Lista de dicts com detalhes de cada sinal.
        """
        return self._signal_history[-last_n:]

    def reset(self) -> None:
        """Reseta o gerenciador, limpando cooldowns e historico."""
        self._last_signal_by_type = {}
        self._last_signal_by_direction = {}
        self._signal_history = []
        logger.info("SignalManager resetado")

    def get_status(self) -> Dict:
        """
        Retorna o status atual do gerenciador para o dashboard.

        Returns:
            Dict com configuracoes e cooldowns ativos.
        """
        cooldown_status = self.get_cooldown_status()
        active_cooldowns = sum(
            1 for v in cooldown_status["type_cooldowns"].values()
            if v["active"]
        )
        active_cooldowns += sum(
            1 for v in cooldown_status["direction_cooldowns"].values()
            if v["active"]
        )

        return {
            "enabled": self.enabled,
            "min_confluence": self.min_confluence,
            "cooldown_same_type": self.cooldown_same_type,
            "cooldown_same_direction": self.cooldown_same_direction,
            "active_cooldowns": active_cooldowns,
            "total_signals_processed": len(self._signal_history),
            "cooldown_status": cooldown_status,
            "filters_enabled": self.filters_config,
        }
