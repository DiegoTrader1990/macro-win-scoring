"""
Dynamic Weights - Pesos Dinamicos Intraday
============================================
Recalcula os pesos dos ativos com base na correlacao intraday
com o WIN/score. Em dias de COPOM o DI domina, em dias de
risco global o VIX domina, etc.

Recalcula a cada 15 minutos (nao a cada refresh) para evitar
instabilidade. Suaviza mudancas (max 20% por recalc).

v6.0 - Componente do sistema de macro scoring
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class DynamicWeights:
    """
    Ajuste dinamico de pesos baseado em correlacao intraday.

    Metodologia:
    1. Coleta variacoes de cada ativo e do WIN nos ultimos N periodos
    2. Calcula correlacao rolling de cada ativo com o WIN
    3. Quando correlacao se destaca acima da media historica, aumenta peso
    4. Quando correlacao cai abaixo de threshold, reduz peso
    5. Suaviza mudancas (max 20% por recalc)
    6. Recalcula apenas a cada 15 minutos
    """

    def __init__(self, base_weights: dict = None, config: dict = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.lookback = self.config.get("lookback_periods", 78)
        self.recalc_interval = self.config.get("recalc_interval_seconds", 900)
        self.max_change_pct = self.config.get("max_weight_change_pct", 20) / 100.0
        self.min_corr = self.config.get("min_correlation_threshold", 0.3)

        # Base weights from config
        self._base_weights: Dict[str, float] = {}
        if base_weights:
            for name, wcfg in base_weights.items():
                if isinstance(wcfg, dict) and "weight" in wcfg:
                    self._base_weights[name] = wcfg["weight"]

        # Current adjusted weights
        self._adjusted_weights: Dict[str, float] = dict(self._base_weights)

        # History of asset changes and WIN changes
        self._asset_changes: Dict[str, List[float]] = {}
        self._win_changes: List[float] = []
        self._max_history = 200

        # Timing
        self._last_recalc: Optional[datetime] = None

        # Calendar adjustments
        self._calendar_multipliers: Dict[str, float] = {}

        logger.info(
            f"DynamicWeights inicializado: lookback={self.lookback}, "
            f"recalc={self.recalc_interval}s, enabled={self.enabled}"
        )

    def update(self, asset_name: str, change_pct: float) -> None:
        """Registra variacao de um ativo."""
        if not self.enabled:
            return
        if asset_name not in self._asset_changes:
            self._asset_changes[asset_name] = []
        self._asset_changes[asset_name].append(change_pct)
        if len(self._asset_changes[asset_name]) > self._max_history:
            self._asset_changes[asset_name] = self._asset_changes[asset_name][-self._max_history:]

    def update_win(self, change_pct: float) -> None:
        """Registra variacao do WIN/proxy."""
        if not self.enabled:
            return
        self._win_changes.append(change_pct)
        if len(self._win_changes) > self._max_history:
            self._win_changes = self._win_changes[-self._max_history:]

    def set_calendar_multipliers(self, multipliers: Dict[str, float]) -> None:
        """Define multiplicadores de peso do calendario de eventos."""
        self._calendar_multipliers = multipliers or {}

    def maybe_recalculate(self, force: bool = False) -> Dict:
        """
        Recalcula pesos se intervalo minimo passou.

        Returns:
            Dict com pesos ajustados e detalhes das mudancas.
        """
        if not self.enabled:
            return {"weights": dict(self._base_weights), "changes": {}, "recalculated": False}

        now = datetime.now()
        if not force and self._last_recalc is not None:
            elapsed = (now - self._last_recalc).total_seconds()
            if elapsed < self.recalc_interval:
                return {
                    "weights": dict(self._adjusted_weights),
                    "changes": {},
                    "recalculated": False,
                    "next_recalc": round(self.recalc_interval - elapsed, 0),
                }

        changes = {}
        new_weights = {}

        for asset_name, base_weight in self._base_weights.items():
            asset_data = self._asset_changes.get(asset_name, [])
            n = min(len(asset_data), len(self._win_changes), self.lookback)

            if n < 10:
                # Dados insuficientes, manter peso base
                new_weight = base_weight
            else:
                # Calcular correlacao rolling
                asset_slice = asset_data[-n:]
                win_slice = self._win_changes[-n:]

                corr = self._pearson_corr(asset_slice, win_slice)

                if corr is None:
                    new_weight = base_weight
                else:
                    # Ajustar peso baseado na correlacao
                    abs_corr = abs(corr)
                    base_corr = abs(self._base_weights.get(asset_name, 0))
                    if base_corr > 0 and abs_corr > base_corr * 1.3:
                        # Correlacao acima da media → aumentar peso
                        adjustment = 1.0 + min(0.5, (abs_corr / base_corr - 1.0) * 0.3)
                    elif abs_corr < self.min_corr:
                        # Correlacao fraca → reduzir peso
                        adjustment = 0.7
                    else:
                        adjustment = 1.0

                    new_weight = base_weight * adjustment

            # Aplicar multiplicador do calendario
            if asset_name in self._calendar_multipliers:
                new_weight *= self._calendar_multipliers[asset_name]

            # Suavizar: max max_change_pct de mudanca
            old_weight = self._adjusted_weights.get(asset_name, base_weight)
            if old_weight > 0:
                max_delta = old_weight * self.max_change_pct
                delta = new_weight - old_weight
                delta = max(-max_delta, min(max_delta, delta))
                new_weight = old_weight + delta

            new_weights[asset_name] = round(new_weight, 4)

            if abs(new_weight - base_weight) > 0.001:
                changes[asset_name] = {
                    "base": base_weight,
                    "adjusted": new_weight,
                    "change_pct": round((new_weight / base_weight - 1) * 100, 1) if base_weight > 0 else 0,
                }

        self._adjusted_weights = new_weights
        self._last_recalc = now

        return {
            "weights": dict(self._adjusted_weights),
            "changes": changes,
            "recalculated": True,
            "timestamp": now,
        }

    def _pearson_corr(self, x: List[float], y: List[float]) -> Optional[float]:
        """Calcula correlacao de Pearson entre duas series."""
        n = min(len(x), len(y))
        if n < 5:
            return None
        x = x[:n]
        y = y[:n]
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        var_x = sum((xi - mean_x) ** 2 for xi in x)
        var_y = sum((yi - mean_y) ** 2 for yi in y)
        denom = (var_x * var_y) ** 0.5
        if denom == 0:
            return None
        return cov / denom

    def get_weights(self) -> Dict[str, float]:
        """Retorna pesos atuais (base ou ajustados)."""
        if self.enabled and self._adjusted_weights:
            return dict(self._adjusted_weights)
        return dict(self._base_weights)

    def get_status(self) -> Dict:
        return {
            "enabled": self.enabled,
            "last_recalc": self._last_recalc.isoformat() if self._last_recalc else None,
            "base_weights_count": len(self._base_weights),
            "adjusted_weights_count": len(self._adjusted_weights),
            "calendar_multipliers": self._calendar_multipliers,
        }

    def reset(self):
        self._adjusted_weights = dict(self._base_weights)
        self._asset_changes = {}
        self._win_changes = []
        self._last_recalc = None
        self._calendar_multipliers = {}
        logger.info("DynamicWeights resetado")
