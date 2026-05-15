"""
Performance Tracker - Rastreamento de Performance Real
========================================================
Rastreia o resultado real dos sinais emitidos pelo sistema,
calculando win rate, payoff ratio, e performance por tipo de sinal.

Funcionamento:
1. Quando um sinal e emitido, registra o preco de entrada do WIN
2. A cada nova leitura, verifica se o sinal atingiu TP ou SL
3. Se o tempo maximo for excedido, registra como EXPIRADO
4. Calcula estatisticas de performance em tempo real

Resultados possiveis:
- WIN: Preco atingiu Take Profit
- LOSS: Preco atingiu Stop Loss
- EXPIRED: Tempo maximo excedido sem atingir TP ou SL

v5.0 - Componente do sistema de macro scoring
"""

import logging
import csv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Rastreador de performance de sinais emitidos.

    Registra cada sinal emitido e acompanha o resultado real
    baseado nos niveis de suporte/resistencia e no tempo de vida
    do sinal.

    Uso tipico:
        tracker = PerformanceTracker(config.PERFORMANCE_CONFIG)
        tracker.register_signal("COMPRA", 45, 8, 125000, timestamp, levels)
        # ... a cada nova leitura:
        tracker.check_outcomes(current_win_price, current_timestamp)
        stats = tracker.get_statistics()
    """

    # Direcao dos sinais
    LONG_SIGNALS = {
        "COMPRA_FORTE", "COMPRA", "COMPRA_CAUTELA",
        "RECUPERACAO_FORTE", "RECUPERACAO", "RECUPERACAO_INICIAL",
        "REVERSAO_ALTA", "REVERSAO_ALTA_PRECO", "DIVERGENCIA_ALTA_PRECO",
    }
    SHORT_SIGNALS = {
        "VENDA_FORTE", "VENDA", "VENDA_CAUTELA",
        "REVERSAO_BAIXA_INTRADAY", "REVERSAO_BAIXA", "REVERSAO_BAIXA_PRECO",
        "DIVERGENCIA_BAIXA_PRECO",
    }

    def __init__(self, config: dict = None, key_levels: dict = None):
        """
        Inicializa o rastreador de performance.

        Args:
            config: Dict com configuracoes (PERFORMANCE_CONFIG).
                    Campos esperados:
                    - enabled: ativa/desativa tracking (default: True)
                    - max_pending_signals: maximo de sinais pendentes (default: 50)
                    - max_signal_lifetime_seconds: tempo maximo de vida (default: 1800)
                    - default_sl_points: stop loss padrao em pontos (default: 200)
                    - default_tp_points: take profit padrao em pontos (default: 400)
                    - track_all_signals: rastrear todos os sinais (default: True)
            key_levels: Niveis-chave (suporte/resistencia) para SL/TP adaptativos.
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.max_pending = self.config.get("max_pending_signals", 50)
        self.max_lifetime = self.config.get("max_signal_lifetime_seconds", 1800)
        self.default_sl = self.config.get("default_sl_points", 200)
        self.default_tp = self.config.get("default_tp_points", 400)
        self.track_all = self.config.get("track_all_signals", True)

        # Niveis-chave para SL/TP adaptativos
        self._key_levels = key_levels or {}

        # Sinais pendentes (aguardando resultado)
        self._pending_signals: List[Dict] = []

        # Sinais finalizados (com resultado)
        self._closed_signals: List[Dict] = []

        logger.info(
            f"PerformanceTracker inicializado: max_pending={self.max_pending}, "
            f"max_lifetime={self.max_lifetime}s, "
            f"SL={self.default_sl}pts, TP={self.default_tp}pts, "
            f"enabled={self.enabled}"
        )

    def register_signal(self, signal_type: str, score: float, delta: float,
                        win_price: float, timestamp: datetime = None,
                        levels_result: dict = None) -> None:
        """
        Registra um novo sinal para rastreamento.

        Define os niveis de SL e TP baseados em:
        1. Niveis de suporte/resistencia mais proximos (se disponiveis)
        2. Valores padrao de SL/TP em pontos (fallback)

        Args:
            signal_type: Tipo do sinal (ex: "COMPRA", "VENDA").
            score: Score macro no momento do sinal.
            delta: Delta do score no momento do sinal.
            win_price: Preco do WIN no momento do sinal.
            timestamp: Momento do sinal (default: agora).
            levels_result: Resultado da analise de niveis-chave (opcional).
        """
        if not self.enabled:
            return

        # Ignora sinais neutros
        if signal_type == "NEUTRO" and not self.track_all:
            return

        timestamp = timestamp or datetime.now()

        # Determina direcao
        if signal_type in self.LONG_SIGNALS:
            direction = "LONG"
        elif signal_type in self.SHORT_SIGNALS:
            direction = "SHORT"
        else:
            direction = "FLAT"

        # Calcula SL e TP
        sl_price, tp_price, sl_method, tp_method = self._calculate_sl_tp(
            win_price=win_price,
            direction=direction,
            levels_result=levels_result,
        )

        signal_entry = {
            "id": len(self._pending_signals) + len(self._closed_signals) + 1,
            "signal_type": signal_type,
            "direction": direction,
            "score": score,
            "delta": delta,
            "entry_price": win_price,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "sl_method": sl_method,
            "tp_method": tp_method,
            "timestamp": timestamp,
            "expiry": timestamp + timedelta(seconds=self.max_lifetime),
            "status": "PENDING",
            "result": None,
            "exit_price": None,
            "pnl_points": None,
            "close_timestamp": None,
        }

        self._pending_signals.append(signal_entry)

        # Limita sinais pendentes
        if len(self._pending_signals) > self.max_pending:
            # Expira o mais antigo
            expired = self._pending_signals.pop(0)
            expired["status"] = "EXPIRED"
            expired["result"] = "EXPIRED"
            expired["close_timestamp"] = datetime.now()
            self._closed_signals.append(expired)
            logger.warning(
                f"Sinal {expired['id']} expirado por limite de pendentes"
            )

        logger.info(
            f"Sinal registrado: #{signal_entry['id']} {signal_type} "
            f"dir={direction} entry={win_price:.0f} "
            f"SL={sl_price:.0f} ({sl_method}) TP={tp_price:.0f} ({tp_method})"
        )

    def _calculate_sl_tp(self, win_price: float, direction: str,
                          levels_result: dict = None) -> tuple:
        """
        Calcula os niveis de Stop Loss e Take Profit.

        Prioriza niveis de suporte/resistencia proximos. Se nao
        disponiveis, usa os valores padrao em pontos.

        Args:
            win_price: Preco de entrada do WIN.
            direction: Direcao do sinal (LONG/SHORT/FLAT).
            levels_result: Resultado da analise de niveis-chave.

        Returns:
            Tupla (sl_price, tp_price, sl_method, tp_method).
        """
        sl_price = None
        tp_price = None
        sl_method = "default"
        tp_method = "default"

        # Tenta usar niveis-chave adaptativos
        if levels_result and levels_result.get("available"):
            nearest = levels_result.get("nearest", [])

            if direction == "LONG":
                # SL: suporte mais proximo abaixo do preco
                supports_below = [
                    lvl for lvl in nearest
                    if lvl["type"] == "suporte" and lvl["value"] < win_price
                ]
                if supports_below:
                    sl_price = supports_below[0]["value"]
                    sl_method = f"suporte_{supports_below[0]['name']}"

                # TP: resistencia mais proxima acima do preco
                resistances_above = [
                    lvl for lvl in nearest
                    if lvl["type"] == "resistencia" and lvl["value"] > win_price
                ]
                if resistances_above:
                    tp_price = resistances_above[0]["value"]
                    tp_method = f"resistencia_{resistances_above[0]['name']}"

            elif direction == "SHORT":
                # SL: resistencia mais proxima acima do preco
                resistances_above = [
                    lvl for lvl in nearest
                    if lvl["type"] == "resistencia" and lvl["value"] > win_price
                ]
                if resistances_above:
                    sl_price = resistances_above[0]["value"]
                    sl_method = f"resistencia_{resistances_above[0]['name']}"

                # TP: suporte mais proximo abaixo do preco
                supports_below = [
                    lvl for lvl in nearest
                    if lvl["type"] == "suporte" and lvl["value"] < win_price
                ]
                if supports_below:
                    tp_price = supports_below[0]["value"]
                    tp_method = f"suporte_{supports_below[0]['name']}"

        # Fallback para valores padrao
        if sl_price is None:
            if direction == "LONG":
                sl_price = win_price - self.default_sl
            elif direction == "SHORT":
                sl_price = win_price + self.default_sl
            else:
                sl_price = win_price - self.default_sl  # Flat usa LONG como padrao
            sl_method = "default_points"

        if tp_price is None:
            if direction == "LONG":
                tp_price = win_price + self.default_tp
            elif direction == "SHORT":
                tp_price = win_price - self.default_tp
            else:
                tp_price = win_price + self.default_tp
            tp_method = "default_points"

        return sl_price, tp_price, sl_method, tp_method

    def check_outcomes(self, current_win_price: float,
                       current_timestamp: datetime = None) -> List[Dict]:
        """
        Verifica o resultado dos sinais pendentes.

        Para cada sinal pendente, verifica se:
        - Atingiu o Stop Loss → LOSS
        - Atingiu o Take Profit → WIN
        - Tempo maximo excedido → EXPIRED

        Args:
            current_win_price: Preco atual do WIN.
            current_timestamp: Timestamp atual (default: agora).

        Returns:
            Lista de sinais que foram finalizados nesta verificacao.
        """
        if not self.enabled or not self._pending_signals:
            return []

        current_timestamp = current_timestamp or datetime.now()
        closed = []

        still_pending = []

        for signal in self._pending_signals:
            result = self._evaluate_signal(signal, current_win_price, current_timestamp)

            if result is not None:
                # Sinal finalizado
                signal["status"] = "CLOSED"
                signal["result"] = result["result"]
                signal["exit_price"] = result["exit_price"]
                signal["pnl_points"] = result["pnl_points"]
                signal["close_timestamp"] = current_timestamp
                closed.append(signal)
                self._closed_signals.append(signal)

                logger.info(
                    f"Sinal #{signal['id']} {signal['signal_type']}: "
                    f"{result['result']} P&L={result['pnl_points']:+.0f}pts "
                    f"(entry={signal['entry_price']:.0f} exit={result['exit_price']:.0f})"
                )
            else:
                still_pending.append(signal)

        self._pending_signals = still_pending
        return closed

    def _evaluate_signal(self, signal: Dict, current_price: float,
                         current_timestamp: datetime) -> Optional[Dict]:
        """
        Avalia se um sinal pendente atingiu TP, SL ou expirou.

        Args:
            signal: Dict do sinal pendente.
            current_price: Preco atual do WIN.
            current_timestamp: Timestamp atual.

        Returns:
            Dict com resultado ou None se sinal continua pendente.
        """
        direction = signal["direction"]
        entry_price = signal["entry_price"]
        sl_price = signal["sl_price"]
        tp_price = signal["tp_price"]

        # Verifica expiracao por tempo
        if current_timestamp >= signal["expiry"]:
            # Calcula P&L no preco atual
            pnl = self._calc_pnl(entry_price, current_price, direction)
            return {
                "result": "EXPIRED",
                "exit_price": current_price,
                "pnl_points": pnl,
            }

        # Verifica Stop Loss
        if direction == "LONG":
            if current_price <= sl_price:
                return {
                    "result": "LOSS",
                    "exit_price": sl_price,
                    "pnl_points": self._calc_pnl(entry_price, sl_price, direction),
                }
            # Verifica Take Profit
            if current_price >= tp_price:
                return {
                    "result": "WIN",
                    "exit_price": tp_price,
                    "pnl_points": self._calc_pnl(entry_price, tp_price, direction),
                }

        elif direction == "SHORT":
            if current_price >= sl_price:
                return {
                    "result": "LOSS",
                    "exit_price": sl_price,
                    "pnl_points": self._calc_pnl(entry_price, sl_price, direction),
                }
            # Verifica Take Profit
            if current_price <= tp_price:
                return {
                    "result": "WIN",
                    "exit_price": tp_price,
                    "pnl_points": self._calc_pnl(entry_price, tp_price, direction),
                }

        # Sinal continua pendente
        return None

    def _calc_pnl(self, entry_price: float, exit_price: float,
                  direction: str) -> float:
        """
        Calcula o P&L em pontos.

        Args:
            entry_price: Preco de entrada.
            exit_price: Preco de saida.
            direction: Direcao da operacao.

        Returns:
            P&L em pontos (positivo = lucro, negativo = perda).
        """
        if direction == "LONG":
            return exit_price - entry_price
        elif direction == "SHORT":
            return entry_price - exit_price
        else:
            return 0.0

    def get_statistics(self) -> Dict:
        """
        Calcula estatisticas de performance de todos os sinais finalizados.

        Returns:
            Dict com:
            - win_rate: taxa de acerto (%)
            - avg_win: media de ganhos (pontos)
            - avg_loss: media de perdas (pontos)
            - payoff_ratio: razao media ganho / media perda
            - total_signals: total de sinais processados
            - total_wins: numero de vitorias
            - total_losses: numero de derrotas
            - total_expired: numero de expirados
            - performance_by_type: performance segmentada por tipo de sinal
        """
        if not self._closed_signals:
            return {
                "win_rate": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "payoff_ratio": 0,
                "total_signals": 0,
                "total_wins": 0,
                "total_losses": 0,
                "total_expired": 0,
                "performance_by_type": {},
                "pending_count": len(self._pending_signals),
            }

        wins = [s for s in self._closed_signals if s["result"] == "WIN"]
        losses = [s for s in self._closed_signals if s["result"] == "LOSS"]
        expired = [s for s in self._closed_signals if s["result"] == "EXPIRED"]

        total_decisive = len(wins) + len(losses)
        win_rate = (len(wins) / total_decisive * 100) if total_decisive > 0 else 0

        win_pnls = [s["pnl_points"] for s in wins if s["pnl_points"] is not None]
        loss_pnls = [s["pnl_points"] for s in losses if s["pnl_points"] is not None]

        avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0
        avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0

        # Payoff ratio: |avg_win| / |avg_loss|
        if avg_loss != 0:
            payoff_ratio = abs(avg_win / avg_loss)
        else:
            payoff_ratio = float("inf") if avg_win > 0 else 0

        # Performance por tipo de sinal
        by_type = self._calc_performance_by_type()

        return {
            "win_rate": round(win_rate, 1),
            "avg_win": round(avg_win, 1),
            "avg_loss": round(avg_loss, 1),
            "payoff_ratio": round(payoff_ratio, 2),
            "total_signals": len(self._closed_signals),
            "total_wins": len(wins),
            "total_losses": len(losses),
            "total_expired": len(expired),
            "performance_by_type": by_type,
            "pending_count": len(self._pending_signals),
        }

    def _calc_performance_by_type(self) -> Dict:
        """
        Calcula performance segmentada por tipo de sinal.

        Returns:
            Dict {signal_type: {wins, losses, win_rate, avg_pnl}}.
        """
        by_type = {}

        for signal in self._closed_signals:
            stype = signal["signal_type"]
            if stype not in by_type:
                by_type[stype] = {
                    "wins": 0,
                    "losses": 0,
                    "expired": 0,
                    "pnl_sum": 0.0,
                    "count": 0,
                }

            entry = by_type[stype]
            entry["count"] += 1

            if signal["result"] == "WIN":
                entry["wins"] += 1
            elif signal["result"] == "LOSS":
                entry["losses"] += 1
            elif signal["result"] == "EXPIRED":
                entry["expired"] += 1

            if signal["pnl_points"] is not None:
                entry["pnl_sum"] += signal["pnl_points"]

        # Calcula win_rate e avg_pnl
        for stype, data in by_type.items():
            decisive = data["wins"] + data["losses"]
            data["win_rate"] = round(
                data["wins"] / decisive * 100, 1
            ) if decisive > 0 else 0
            data["avg_pnl"] = round(
                data["pnl_sum"] / data["count"], 1
            ) if data["count"] > 0 else 0

        return by_type

    def get_pending_signals(self) -> List[Dict]:
        """
        Retorna lista de sinais pendentes (sem resultado ainda).

        Returns:
            Lista de dicts com detalhes dos sinais pendentes.
        """
        now = datetime.now()
        result = []
        for signal in self._pending_signals:
            remaining = (signal["expiry"] - now).total_seconds()
            entry = {**signal}
            entry["remaining_seconds"] = max(0, round(remaining, 0))
            # Converte timestamps para string
            entry["timestamp"] = signal["timestamp"].isoformat()
            entry["expiry"] = signal["expiry"].isoformat()
            result.append(entry)
        return result

    def save_to_log(self, logger_obj=None) -> None:
        """
        Persiste os resultados em arquivo CSV de log.

        Args:
            logger_obj: Objeto MacroLogger (opcional). Se fornecido,
                        usa o diretorio de log dele. Caso contrario,
                        salva em ./logs/.
        """
        if not self._closed_signals:
            return

        # Determina diretorio de log
        if logger_obj and hasattr(logger_obj, "log_dir"):
            log_dir = logger_obj.log_dir
        else:
            log_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "logs"
            )

        os.makedirs(log_dir, exist_ok=True)

        today = datetime.now().strftime("%Y%m%d")
        filepath = os.path.join(log_dir, f"{today}_performance_log.csv")

        try:
            file_exists = os.path.exists(filepath)

            with open(filepath, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                if not file_exists:
                    writer.writerow([
                        "signal_id", "signal_type", "direction",
                        "score", "delta", "entry_price",
                        "sl_price", "tp_price", "sl_method", "tp_method",
                        "result", "exit_price", "pnl_points",
                        "timestamp", "close_timestamp",
                    ])

                for signal in self._closed_signals:
                    writer.writerow([
                        signal["id"],
                        signal["signal_type"],
                        signal["direction"],
                        signal["score"],
                        signal["delta"],
                        signal["entry_price"],
                        signal["sl_price"],
                        signal["tp_price"],
                        signal["sl_method"],
                        signal["tp_method"],
                        signal["result"],
                        signal.get("exit_price", ""),
                        signal.get("pnl_points", ""),
                        signal["timestamp"].isoformat() if isinstance(signal["timestamp"], datetime) else signal["timestamp"],
                        signal.get("close_timestamp", ""),
                    ])

            logger.info(f"Performance log salvo: {filepath}")

        except Exception as e:
            logger.error(f"Erro ao salvar performance log: {e}")

    def get_status(self) -> Dict:
        """
        Retorna o status atual do tracker para o dashboard.

        Returns:
            Dict com estatisticas resumidas e sinais pendentes.
        """
        stats = self.get_statistics()
        return {
            "enabled": self.enabled,
            "total_signals": stats["total_signals"],
            "win_rate": stats["win_rate"],
            "payoff_ratio": stats["payoff_ratio"],
            "pending_signals": len(self._pending_signals),
            "total_wins": stats["total_wins"],
            "total_losses": stats["total_losses"],
            "total_expired": stats["total_expired"],
        }

    def reset(self) -> None:
        """Reseta o tracker, limpando sinais pendentes e historico."""
        self._pending_signals = []
        self._closed_signals = []
        logger.info("PerformanceTracker resetado")
