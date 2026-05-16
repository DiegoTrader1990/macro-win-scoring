"""
Validação Empírica de Correlação Intraday - v7.0
=================================================
Script para testar a correlação REAL de cada ativo com o WIN
usando dados intraday de 5 minutos.

Rodar: python validate_correlations.py

Este script:
1. Baixa dados intraday de WIN (via IBOV/EWZ) e todos os ativos
2. Calcula correlação de Pearson em janelas de 5min
3. Testa com lag (0s, 30s, 60s) para ver qual ativo LIDEROU
4. Gera relatório com correlações reais vs pesos configurados
5. Sugere ajustes de peso baseados nos dados
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta

# Adicionar raiz do projeto ao path
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Importar config
try:
    from config import MACRO_WEIGHTS, YF_SYMBOLS, DUAL_SOURCE_ASSETS, CORRELATION_VALIDATOR_CONFIG
    from data_sources.yahoo_source import YahooFinanceSource
except ImportError as e:
    logger.error(f"Erro de importacao: {e}")
    logger.info("Execute este script a partir da raiz do projeto: python validate_correlations.py")
    sys.exit(1)


def fetch_intraday_data(symbol: str, days: int = 60, interval: str = "5m") -> pd.DataFrame:
    """Baixa dados intraday de um ativo via Yahoo Finance."""
    try:
        import yfinance as yf
        end = datetime.now()
        start = end - timedelta(days=days)
        df = yf.download(symbol, start=start, end=end, interval=interval, progress=False)
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        logger.warning(f"Erro ao baixar {symbol}: {e}")
        return pd.DataFrame()


def calculate_correlation_with_lag(win_series: pd.Series, asset_series: pd.Series,
                                    lag: int = 0) -> dict:
    """Calcula correlação com lag (asset liderando WIN)."""
    if len(win_series) < 30 or len(asset_series) < 30:
        return {"correlation": 0, "p_value": 1, "n_obs": 0}

    # Alinhar series
    if lag > 0:
        asset_shifted = asset_series.shift(lag)
        combined = pd.concat([win_series, asset_shifted], axis=1).dropna()
    else:
        combined = pd.concat([win_series, asset_series], axis=1).dropna()

    if len(combined) < 30:
        return {"correlation": 0, "p_value": 1, "n_obs": len(combined)}

    from scipy import stats
    corr, p_value = stats.pearsonr(combined.iloc[:, 0], combined.iloc[:, 1])

    return {
        "correlation": round(corr, 4),
        "p_value": round(p_value, 6),
        "n_obs": len(combined),
    }


def validate_all_correlations():
    """Executa validação completa de correlações."""
    cfg = CORRELATION_VALIDATOR_CONFIG
    if not cfg.get("enabled", True):
        logger.info("Validacao de correlacao desabilitada")
        return

    lookback_days = cfg.get("lookback_days", 60)
    interval = cfg.get("interval", "5m")
    lags = cfg.get("lag_seconds", [0, 30, 60])
    output_file = cfg.get("output_file", "correlation_report.json")

    logger.info(f"=== VALIDACAO EMPIRICA DE CORRELACOES v7.0 ===")
    logger.info(f"Periodo: {lookback_days} dias | Intervalo: {interval}")

    # 1. Baixar dados do WIN (proxy IBOV)
    logger.info("Baixando dados do WIN (IBOV proxy)...")
    win_symbol = "^BVSP"
    win_df = fetch_intraday_data(win_symbol, lookback_days, interval)

    if win_df.empty:
        logger.error("Nao conseguiu baixar dados do IBOV. Tentando EWZ...")
        win_df = fetch_intraday_data("EWZ", lookback_days, interval)

    if win_df.empty:
        logger.error("Sem dados de referencia. Abortando.")
        return

    # Calcular retornos percentuais do WIN
    win_returns = win_df["Close"].pct_change().dropna()
    logger.info(f"WIN: {len(win_returns)} observacoes")

    # 2. Testar cada ativo
    results = {}
    all_yf_symbols = dict(YF_SYMBOLS)
    all_dual = dict(DUAL_SOURCE_ASSETS)

    # Combinar simbolos YF
    all_symbols = {}
    for name, yf_sym in all_yf_symbols.items():
        all_symbols[name] = yf_sym
    for name, sources in all_dual.items():
        all_symbols[name] = sources.get("yf", "")

    # Adicionar WIN
    all_symbols["WIN_PROXY"] = win_symbol

    total = len(all_symbols)
    for i, (name, symbol) in enumerate(all_symbols.items()):
        if name == "WIN_PROXY":
            continue

        logger.info(f"[{i+1}/{total}] Testando {name} ({symbol})...")

        asset_df = fetch_intraday_data(symbol, lookback_days, interval)
        if asset_df.empty:
            logger.warning(f"  Sem dados para {name}")
            results[name] = {"error": "sem dados", "symbol": symbol}
            continue

        asset_returns = asset_df["Close"].pct_change().dropna()

        # Calcular correlações com diferentes lags
        lag_results = {}
        best_corr = 0
        best_lag = 0

        # Converter lag de segundos para número de candles
        # 5min = 300s, então lag 30s ≈ 0.1 candles, 60s ≈ 0.2
        # Para YF 5min, lag real é limitado, mas testamos 0, 1, 2 candles
        lag_candles = [0, 1, 2, 3]

        for lag in lag_candles:
            lag_name = f"lag_{lag}"
            corr_result = calculate_correlation_with_lag(win_returns, asset_returns, lag)
            lag_results[lag_name] = corr_result

            if abs(corr_result["correlation"]) > abs(best_corr):
                best_corr = corr_result["correlation"]
                best_lag = lag

        # Pegar peso atual do config
        current_weight = MACRO_WEIGHTS.get(name, {})
        weight = current_weight.get("weight", 0)
        configured_corr = current_weight.get("corr_intraday") or current_weight.get("corr", 0)
        tier = current_weight.get("tier", "N/A")
        category = current_weight.get("category", "N/A")

        # Sugerir novo peso baseado na correlação real
        suggested_weight = _suggest_weight(best_corr, tier)

        results[name] = {
            "symbol": symbol,
            "n_obs": len(asset_returns),
            "best_correlation": best_corr,
            "best_lag": best_lag,
            "lag_details": lag_results,
            "configured_weight": weight,
            "configured_corr": configured_corr,
            "configured_tier": tier,
            "category": category,
            "suggested_weight": suggested_weight,
            "weight_divergence": round(abs(best_corr) - abs(configured_corr), 4) if configured_corr else 0,
        }

        direction = "+" if best_corr > 0 else "-"
        logger.info(f"  Corr: {direction}{abs(best_corr):.3f} (lag {best_lag}) | "
                    f"Peso atual: {weight} | Sugerido: {suggested_weight}")

    # 3. Gerar relatório
    report = {
        "timestamp": datetime.now().isoformat(),
        "period_days": lookback_days,
        "interval": interval,
        "win_observations": len(win_returns),
        "assets_tested": len([r for r in results.values() if "error" not in r]),
        "results": results,
        "summary": _generate_report_summary(results),
    }

    # Salvar relatório
    output_path = os.path.join(_APP_DIR, output_file)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"\nRelatorio salvo em: {output_path}")
    _print_report(report)

    return report


def _suggest_weight(correlation: float, tier: int = None) -> float:
    """Sugere peso baseado na correlação empírica."""
    abs_corr = abs(correlation)

    if abs_corr >= 0.80:
        base = 0.10
    elif abs_corr >= 0.70:
        base = 0.08
    elif abs_corr >= 0.60:
        base = 0.06
    elif abs_corr >= 0.50:
        base = 0.04
    elif abs_corr >= 0.40:
        base = 0.03
    elif abs_corr >= 0.30:
        base = 0.02
    else:
        base = 0.01

    # Ajustar por tier
    if tier == 1:
        base *= 1.3  # B3 diretos ganham bonus
    elif tier == 3:
        base *= 0.7  # Complementares perdem

    return round(min(base, 0.15), 3)


def _generate_report_summary(results: dict) -> dict:
    """Gera resumo do relatório."""
    valid = {k: v for k, v in results.items() if "error" not in v}

    # Ordenar por correlação real
    by_corr = sorted(valid.items(), key=lambda x: abs(x[1].get("best_correlation", 0)), reverse=True)

    # Maiores divergências entre config e realidade
    by_divergence = sorted(valid.items(),
                           key=lambda x: abs(x[1].get("weight_divergence", 0)), reverse=True)

    return {
        "top_correlated": [(name, r["best_correlation"]) for name, r in by_corr[:5]],
        "least_correlated": [(name, r["best_correlation"]) for name, r in by_corr[-5:]],
        "biggest_divergences": [(name, r["weight_divergence"]) for name, r in by_divergence[:5]],
        "total_weight_current": sum(r.get("configured_weight", 0) for r in valid.values()),
        "total_weight_suggested": sum(r.get("suggested_weight", 0) for r in valid.values()),
    }


def _print_report(report: dict):
    """Imprime relatório formatado no console."""
    print("\n" + "=" * 70)
    print("RELATORIO DE CORRELACAO INTRADAY v7.0")
    print("=" * 70)
    print(f"Periodo: {report['period_days']} dias | Intervalo: {report['interval']}")
    print(f"Observacoes WIN: {report['win_observations']}")
    print(f"Ativos testados: {report['assets_tested']}")
    print("-" * 70)

    results = report["results"]
    valid = {k: v for k, v in results.items() if "error" not in v}

    # Ordenar por correlação
    sorted_results = sorted(valid.items(), key=lambda x: abs(x[1].get("best_correlation", 0)), reverse=True)

    print(f"\n{'Ativo':<15} {'Corr Real':>10} {'Corr Config':>11} {'Peso Atual':>11} {'Peso Suger':>11} {'Lag':>5} {'Tier':>5}")
    print("-" * 70)

    for name, r in sorted_results:
        corr_real = r.get("best_correlation", 0)
        corr_cfg = r.get("configured_corr", 0)
        weight = r.get("configured_weight", 0)
        suggested = r.get("suggested_weight", 0)
        lag = r.get("best_lag", 0)
        tier = r.get("configured_tier", "-")

        flag = " ***" if abs(corr_real - corr_cfg) > 0.2 else ""
        print(f"{name:<15} {corr_real:>+10.3f} {corr_cfg:>+11.3f} {weight:>11.3f} {suggested:>11.3f} {lag:>5} T{tier}{flag}")

    print("-" * 70)
    print("*** = Divergencia > 0.2 entre correlacao real e configurada")
    print("\nResumo:")
    summary = report.get("summary", {})
    print(f"  Top correlacionados: {summary.get('top_correlated', [])}")
    print(f"  Maiores divergencias: {summary.get('biggest_divergences', [])}")
    print(f"  Peso total atual: {summary.get('total_weight_current', 0):.3f}")
    print(f"  Peso total sugerido: {summary.get('total_weight_suggested', 0):.3f}")
    print("=" * 70)


if __name__ == "__main__":
    validate_all_correlations()
