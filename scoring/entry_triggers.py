"""
Sistema de Gatilhos de Entrada - v7.0
======================================
Identifica pontos especificos de entrada baseados em confluencia
de multiplos fatores: score, delta, alinhamento B3, compressao.

Cada gatilho eh independente e pode ser habilitado/desabilitado.
O resultado final combina todos os gatilhos ativos em um
TRIGGER SCORE que indica a forca da entrada.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class EntryTriggers:
    """
    Motor de gatilhos de entrada para day trade WIN.

    Avalia 5 gatilhos independentes:
    1. Score + Delta: viés forte + aceleracao
    2. DOL vs Bancos: divergencia interna B3
    3. Compressao + Breakout: saida de range
    4. Tier1 Alignment: B3 diretos coordenados
    5. Regime Filter: anti-entrada (bloqueio)
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._trigger_history = []
        self._max_history = 500

    def evaluate(self, score: float, delta: float, all_data: dict,
                 compression_result: dict = None, regime_result: dict = None,
                 divergence_result: dict = None, confidence_result: dict = None,
                 category_scores: dict = None) -> dict:
        """
        Avalia todos os gatilhos e retorna resultado consolidado.

        Args:
            score: Score macro atual (-100 a +100)
            delta: Delta do score (variacao)
            all_data: Dict com dados de todos os ativos
            compression_result: Resultado do CompressionDetector
            regime_result: Resultado do RegimeDetector
            divergence_result: Resultado do DivergenceDetector
            confidence_result: Resultado do ConfidenceScore
            category_scores: Scores por categoria

        Returns:
            Dict com resultado de cada gatilho + trigger_score consolidado
        """
        if not self.enabled:
            return {"enabled": False, "trigger_score": 0, "direction": "NEUTRO"}

        results = {}
        trigger_points = 0
        direction = "NEUTRO"
        blocks = []

        # Gatilho 1: Score + Delta
        r1 = self._check_score_delta(score, delta)
        results["score_delta"] = r1
        if r1["triggered"]:
            trigger_points += r1["strength"]
            direction = r1["direction"]

        # Gatilho 2: DOL vs Bancos
        r2 = self._check_dolar_banks(all_data)
        results["dolar_bank"] = r2
        if r2["triggered"]:
            trigger_points += r2["strength"]
            if direction == "NEUTRO":
                direction = r2["direction"]

        # Gatilho 3: Compressao + Breakout
        r3 = self._check_compression_break(score, delta, compression_result)
        results["compression_break"] = r3
        if r3["triggered"]:
            trigger_points += r3["strength"]
            if direction == "NEUTRO":
                direction = r3["direction"]

        # Gatilho 4: Tier1 Alignment
        r4 = self._check_tier1_alignment(all_data)
        results["tier1_alignment"] = r4
        if r4["triggered"]:
            trigger_points += r4["strength"]
            if direction == "NEUTRO":
                direction = r4["direction"]

        # Gatilho 5: Filtros Anti-Entrada
        r5 = self._check_regime_filter(regime_result, divergence_result, confidence_result)
        results["regime_filter"] = r5
        if r5["blocked"]:
            blocks.extend(r5["block_reasons"])
            # Reduz a forca se bloqueado parcialmente
            trigger_points = max(0, trigger_points - r5["penalty"])

        # Consolidar resultado
        triggered = trigger_points >= 2 and len(blocks) == 0
        trigger_score = min(trigger_points, 5)  # Max 5 pontos

        result = {
            "triggered": triggered,
            "trigger_score": trigger_score,
            "direction": direction,
            "blocks": blocks,
            "details": results,
            "timestamp": datetime.now(),
            "summary": self._generate_summary(trigger_score, direction, blocks, results),
        }

        # Salvar no historico
        self._trigger_history.append(result)
        if len(self._trigger_history) > self._max_history:
            self._trigger_history.pop(0)

        return result

    def _check_score_delta(self, score: float, delta: float) -> dict:
        """Gatilho 1: Score forte + Delta acelerando."""
        cfg = self.config.get("score_delta_trigger", {})
        if not cfg.get("enabled", True):
            return {"triggered": False, "reason": "disabled"}

        triggered = False
        direction = "NEUTRO"
        strength = 0

        long_score = cfg.get("long_score_min", 35)
        long_delta = cfg.get("long_delta_min", 10)
        short_score = cfg.get("short_score_max", -35)
        short_delta = cfg.get("short_delta_max", -10)

        if score >= long_score and delta >= long_delta:
            triggered = True
            direction = "LONG"
            strength = 2 if score >= 55 else 1
        elif score <= short_score and delta <= short_delta:
            triggered = True
            direction = "SHORT"
            strength = 2 if score <= -55 else 1

        return {
            "triggered": triggered,
            "direction": direction,
            "strength": strength,
            "score": score,
            "delta": delta,
            "reason": f"Score={score:.0f} Delta={delta:.0f}" if triggered else "condicoes nao atendidas",
        }

    def _check_dolar_banks(self, all_data: dict) -> dict:
        """Gatilho 2: Divergencia DOL vs Bancos."""
        cfg = self.config.get("dolar_bank_trigger", {})
        if not cfg.get("enabled", True):
            return {"triggered": False, "reason": "disabled"}

        triggered = False
        direction = "NEUTRO"
        strength = 0

        # Pegar variacao do WDO
        wdo_data = all_data.get("WDO")
        wdo_change = wdo_data.get("change_pct") if wdo_data else None

        # Pegar variacao media dos bancos
        bank_assets = cfg.get("bank_assets", ["ITUB4", "BBDC4", "BBAS3", "IFNC"])
        bank_changes = []
        for asset in bank_assets:
            data = all_data.get(asset)
            if data and data.get("change_pct") is not None:
                bank_changes.append(data["change_pct"])

        if wdo_change is None or not bank_changes:
            return {"triggered": False, "reason": "dados insuficientes"}

        avg_bank = sum(bank_changes) / len(bank_changes)

        long_wdo_max = cfg.get("long_wdo_max_change", -0.3)
        long_banks_min = cfg.get("long_banks_min_change", 0.2)
        short_wdo_min = cfg.get("short_wdo_min_change", 0.3)
        short_banks_max = cfg.get("short_banks_max_change", -0.2)

        # LONG: WDO caindo (dolar caindo) + Bancos subindo
        if wdo_change <= long_wdo_max and avg_bank >= long_banks_min:
            triggered = True
            direction = "LONG"
            strength = 2

        # SHORT: WDO subindo (dolar subindo) + Bancos caindo
        elif wdo_change >= short_wdo_min and avg_bank <= short_banks_max:
            triggered = True
            direction = "SHORT"
            strength = 2

        return {
            "triggered": triggered,
            "direction": direction,
            "strength": strength,
            "wdo_change": wdo_change,
            "avg_bank_change": avg_bank,
            "reason": f"WDO={wdo_change:.2f}% Banks={avg_bank:.2f}%" if triggered else "sem divergencia",
        }

    def _check_compression_break(self, score: float, delta: float,
                                  compression_result: dict = None) -> dict:
        """Gatilho 3: Saida de compressao com delta forte."""
        cfg = self.config.get("compression_break_trigger", {})
        if not cfg.get("enabled", True):
            return {"triggered": False, "reason": "disabled"}

        if not compression_result:
            return {"triggered": False, "reason": "sem dados de compressao"}

        triggered = False
        direction = "NEUTRO"
        strength = 0

        is_compressed = compression_result.get("compressed", False)
        was_compressed = compression_result.get("was_compressed", False)
        breakout_delta = cfg.get("breakout_delta_min", 8)

        # Se estava comprimido e agora saiu com delta forte
        if was_compressed and abs(delta) >= breakout_delta:
            triggered = True
            direction = "LONG" if delta > 0 else "SHORT"
            strength = 2 if abs(delta) >= 15 else 1

        return {
            "triggered": triggered,
            "direction": direction,
            "strength": strength,
            "delta": delta,
            "was_compressed": was_compressed,
            "reason": f"Breakout Delta={delta:.0f}" if triggered else "sem breakout",
        }

    def _check_tier1_alignment(self, all_data: dict) -> dict:
        """Gatilho 4: Ativos Tier1 (B3 diretos) alinhados na mesma direcao."""
        cfg = self.config.get("tier1_alignment_trigger", {})
        if not cfg.get("enabled", True):
            return {"triggered": False, "reason": "disabled"}

        tier1_assets = cfg.get("tier1_assets", [
            "WDO", "DI1_FUTURES", "ITUB4", "BBDC4", "BBAS3",
            "VALE3", "PETR4", "IFNC", "IMAT", "ICON"
        ])
        threshold = cfg.get("aligned_change_threshold", 0.15)
        min_aligned = cfg.get("min_aligned_assets", 6)

        # Direcoes baseadas em correlacao com WIN (do MACRO_WEIGHTS)
        direction_map = {
            "WDO": -1, "DI1_FUTURES": +1, "ITUB4": +1, "BBDC4": +1,
            "BBAS3": +1, "VALE3": +1, "PETR4": +1, "IFNC": +1,
            "IMAT": +1, "ICON": +1,
        }

        bullish_count = 0
        bearish_count = 0
        asset_directions = {}

        for asset in tier1_assets:
            data = all_data.get(asset)
            if not data or data.get("change_pct") is None:
                continue

            change = data["change_pct"]
            corr_dir = direction_map.get(asset, +1)

            # Se ativo sobe E tem correlacao positiva -> BULLISH para WIN
            # Se ativo desce E tem correlacao negativa -> BULLISH para WIN
            effective_signal = change * corr_dir

            if effective_signal >= threshold:
                bullish_count += 1
                asset_directions[asset] = "BULL"
            elif effective_signal <= -threshold:
                bearish_count += 1
                asset_directions[asset] = "BEAR"
            else:
                asset_directions[asset] = "NEUTRO"

        triggered = False
        direction = "NEUTRO"
        strength = 0

        if bullish_count >= min_aligned:
            triggered = True
            direction = "LONG"
            strength = 2 if bullish_count >= 8 else 1
        elif bearish_count >= min_aligned:
            triggered = True
            direction = "SHORT"
            strength = 2 if bearish_count >= 8 else 1

        return {
            "triggered": triggered,
            "direction": direction,
            "strength": strength,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "total_tier1": len(tier1_assets),
            "asset_directions": asset_directions,
            "reason": f"{bullish_count}B/{bearish_count}S de {len(tier1_assets)}" if triggered else "sem alinhamento",
        }

    def _check_regime_filter(self, regime_result: dict = None,
                              divergence_result: dict = None,
                              confidence_result: dict = None) -> dict:
        """Gatilho 5: Filtro anti-entrada."""
        cfg = self.config.get("regime_filter_trigger", {})
        if not cfg.get("enabled", True):
            return {"blocked": False, "block_reasons": [], "penalty": 0}

        blocked = False
        block_reasons = []
        penalty = 0

        # Verificar regime lateral
        if cfg.get("block_on_lateral", True) and regime_result:
            regime = regime_result.get("regime", "")
            if regime in ("LATERAL", "TRANSICAO"):
                block_reasons.append(f"Regime {regime}")
                penalty += 1

        # Verificar divergencia ativa
        if cfg.get("block_on_divergence", True) and divergence_result:
            if divergence_result.get("divergence_active", False):
                div_type = divergence_result.get("type", "")
                block_reasons.append(f"Divergencia {div_type}")
                penalty += 1

        # Verificar confianca baixa
        if cfg.get("block_on_low_confidence", True) and confidence_result:
            conf_pct = confidence_result.get("confidence_pct", 100)
            min_conf = cfg.get("min_confidence_pct", 50)
            if conf_pct < min_conf:
                block_reasons.append(f"Confianca {conf_pct:.0f}% < {min_conf}%")
                penalty += 1

        blocked = len(block_reasons) > 0

        return {
            "blocked": blocked,
            "block_reasons": block_reasons,
            "penalty": penalty,
        }

    def _generate_summary(self, trigger_score: int, direction: str,
                           blocks: list, details: dict) -> str:
        """Gera resumo textual do resultado dos gatilhos."""
        if blocks:
            return f"BLOQUEADO: {', '.join(blocks)}"

        triggered_names = []
        for name, result in details.items():
            if result.get("triggered"):
                triggered_names.append(name.upper())

        if not triggered_names:
            return "Sem gatilhos ativos"

        strength_label = {1: "FRACO", 2: "MODERADO", 3: "FORTE", 4: "MUITO FORTE", 5: "MAXIMO"}
        label = strength_label.get(trigger_score, "FRACO")

        return f"{direction} {label} ({trigger_score}/5) - {' + '.join(triggered_names)}"

    def get_history(self, last_n: int = None) -> list:
        """Retorna historico de gatilhos."""
        if last_n:
            return self._trigger_history[-last_n:]
        return self._trigger_history
