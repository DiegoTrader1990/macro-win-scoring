"""
Análise de Logs - Sistema Macro Scoring WIN
============================================
Carrega os logs CSV gerados pelo sistema e produz análises
para otimização de pesos, thresholds e gatilhos de entrada.

Uso: python analyze_logs.py [data]
Exemplo: python analyze_logs.py 20250515
         python analyze_logs.py           (usa data de hoje)
"""

import sys
import os
import json
import glob
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np


def load_logs(log_dir: str = "logs", target_date: str = None) -> dict:
    """
    Carrega os arquivos de log para um dia específico.

    Args:
        log_dir: Diretório de logs
        target_date: Data no formato YYYYMMDD (default: hoje)

    Returns:
        Dict com DataFrames: score_df, asset_df, signal_df, session_df
    """
    if target_date is None:
        target_date = date.today().strftime("%Y%m%d")

    # Busca arquivos que começam com a data
    score_files = glob.glob(os.path.join(log_dir, f"{target_date}_score_log.csv"))
    asset_files = glob.glob(os.path.join(log_dir, f"{target_date}_asset_log.csv"))
    signal_files = glob.glob(os.path.join(log_dir, f"{target_date}_signal_log.csv"))
    session_files = glob.glob(os.path.join(log_dir, f"{target_date}_session_log.jsonl"))

    result = {}

    if score_files:
        result["score"] = pd.read_csv(score_files[0])
        print(f"  Score log: {len(result['score'])} registros")
    else:
        print(f"  Score log: NAO ENCONTRADO para {target_date}")

    if asset_files:
        result["asset"] = pd.read_csv(asset_files[0])
        print(f"  Asset log: {len(result['asset'])} registros")
    else:
        print(f"  Asset log: NAO ENCONTRADO para {target_date}")

    if signal_files:
        result["signal"] = pd.read_csv(signal_files[0])
        print(f"  Signal log: {len(result['signal'])} registros")
    else:
        print(f"  Signal log: NAO ENCONTRADO para {target_date}")

    if session_files:
        sessions = []
        with open(session_files[0], 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    sessions.append(json.loads(line.strip()))
                except:
                    pass
        result["session"] = pd.DataFrame(sessions)
        print(f"  Session log: {len(sessions)} eventos")

    return result


def analyze_score_distribution(score_df: pd.DataFrame) -> dict:
    """Analisa a distribuição dos scores."""
    if score_df is None or score_df.empty:
        return {}

    stats = {
        "total_reads": len(score_df),
        "score_mean": round(score_df["score"].mean(), 2),
        "score_std": round(score_df["score"].std(), 2),
        "score_min": round(score_df["score"].min(), 2),
        "score_max": round(score_df["score"].max(), 2),
        "score_median": round(score_df["score"].median(), 2),
        "time_range": f"{score_df['time'].min()} - {score_df['time'].max()}",

        # Distribuição por zona
        "zona_forte_alta": len(score_df[score_df["score"] >= 60]),
        "zona_moderada_alta": len(score_df[(score_df["score"] >= 30) & (score_df["score"] < 60)]),
        "zona_neutro": len(score_df[(score_df["score"] > -30) & (score_df["score"] < 30)]),
        "zona_moderada_baixa": len(score_df[(score_df["score"] <= -30) & (score_df["score"] > -60)]),
        "zona_forte_baixa": len(score_df[score_df["score"] <= -60]),

        # Delta stats
        "delta_mean": round(score_df["delta"].mean(), 2),
        "delta_std": round(score_df["delta"].std(), 2),

        # Confluence
        "confluence_count": int(score_df["confluence_aligned"].sum()) if "confluence_aligned" in score_df.columns else 0,
        "reversal_count": int(score_df["reversal_detected"].sum()) if "reversal_detected" in score_df.columns else 0,
    }

    # Percentuais
    total = stats["total_reads"]
    if total > 0:
        stats["pct_forte_alta"] = round(stats["zona_forte_alta"] / total * 100, 1)
        stats["pct_moderada_alta"] = round(stats["zona_moderada_alta"] / total * 100, 1)
        stats["pct_neutro"] = round(stats["zona_neutro"] / total * 100, 1)
        stats["pct_moderada_baixa"] = round(stats["zona_moderada_baixa"] / total * 100, 1)
        stats["pct_forte_baixa"] = round(stats["zona_forte_baixa"] / total * 100, 1)
        stats["pct_confluence"] = round(stats["confluence_count"] / total * 100, 1)
        stats["pct_reversal"] = round(stats["reversal_count"] / total * 100, 1)

    return stats


def analyze_asset_contributions(asset_df: pd.DataFrame) -> dict:
    """Analisa a contribuição de cada ativo ao longo do dia."""
    if asset_df is None or asset_df.empty:
        return {}

    # Contribuição média por ativo
    contrib_by_asset = asset_df.groupby("asset").agg(
        contrib_mean=("contribution", "mean"),
        contrib_std=("contribution", "std"),
        contrib_abs_mean=("contribution", lambda x: x.abs().mean()),
        change_mean=("change_pct", "mean"),
        change_std=("change_pct", "std"),
        reads=("contribution", "count"),
    ).sort_values("contrib_abs_mean", ascending=False)

    return {
        "contributions": contrib_by_asset,
        "top_positive": contrib_by_asset.nlargest(5, "contrib_mean"),
        "top_negative": contrib_by_asset.nsmallest(5, "contrib_mean"),
        "top_impact": contrib_by_asset.nlargest(5, "contrib_abs_mean"),
    }


def analyze_signals(signal_df: pd.DataFrame) -> dict:
    """Analisa os sinais de entrada gerados."""
    if signal_df is None or signal_df.empty:
        return {"total_signals": 0, "message": "Nenhum sinal registrado"}

    signal_counts = signal_df["signal_type"].value_counts().to_dict()

    # Sinais com confluence
    if "confluence_aligned" in signal_df.columns:
        confluence_signals = signal_df[signal_df["confluence_aligned"] == True]
        reversal_signals = signal_df[signal_df["reversal_detected"] == True]
    else:
        confluence_signals = pd.DataFrame()
        reversal_signals = pd.DataFrame()

    # Score médio quando cada tipo de sinal foi gerado
    score_by_signal = signal_df.groupby("signal_type")["score"].agg(["mean", "min", "max"]).to_dict()

    return {
        "total_signals": len(signal_df),
        "signal_counts": signal_counts,
        "confluence_signals": len(confluence_signals),
        "reversal_signals": len(reversal_signals),
        "score_by_signal": score_by_signal,
        "first_signal_time": signal_df["time"].min(),
        "last_signal_time": signal_df["time"].max(),
    }


def analyze_delta_patterns(score_df: pd.DataFrame) -> dict:
    """Analisa padrões de delta para otimizar gatilhos."""
    if score_df is None or score_df.empty:
        return {}

    # Delta transitions
    deltas = score_df["delta"].values

    # Quantas vezes delta cruzou zero (reversão)
    zero_crossings = sum(1 for i in range(1, len(deltas)) if deltas[i-1] * deltas[i] < 0)

    # Score transitions (mudança de zona)
    scores = score_df["score"].values
    zone_changes = 0
    for i in range(1, len(scores)):
        prev_zone = get_zone(scores[i-1])
        curr_zone = get_zone(scores[i])
        if prev_zone != curr_zone:
            zone_changes += 1

    return {
        "delta_zero_crossings": zero_crossings,
        "zone_transitions": zone_changes,
        "delta_volatility": round(float(np.std(deltas)), 2),
        "avg_delta_magnitude": round(float(np.mean(np.abs(deltas))), 2),
        "max_positive_delta": round(float(np.max(deltas)), 2),
        "max_negative_delta": round(float(np.min(deltas)), 2),
    }


def get_zone(score: float) -> str:
    if score >= 60: return "FORTE_ALTA"
    if score >= 30: return "MODERADA_ALTA"
    if score > -30: return "NEUTRO"
    if score > -60: return "MODERADA_BAIXA"
    return "FORTE_BAIXA"


def suggest_optimizations(score_stats: dict, asset_stats: dict, signal_stats: dict, delta_stats: dict) -> list:
    """Gera sugestões de otimização baseadas na análise."""
    suggestions = []

    if not score_stats:
        return ["Dados insuficientes para sugestões"]

    # Score muito concentrado no neutro?
    pct_neutro = score_stats.get("pct_neutro", 0)
    if pct_neutro > 70:
        suggestions.append(
            f"ALERTA: {pct_neutro}% das leituras estao na zona NEUTRA. "
            "Considere reduzir thresholds (ex: moderate_bullish de 30 para 20) "
            "ou aumentar pesos de ativos com maior contribuicao absoluta."
        )

    # Score muito volátil?
    score_std = score_stats.get("score_std", 0)
    if score_std > 40:
        suggestions.append(
            f"Score muito volatil (std={score_std}). Considere suavizar com "
            "media movel das ultimas 3 leituras antes de gerar sinal."
        )

    # Delta com muitas reversões?
    if delta_stats:
        crossings = delta_stats.get("delta_zero_crossings", 0)
        if crossings > 10:
            suggestions.append(
                f"Delta cruzou zero {crossings} vezes. Muitas reversoes podem gerar "
                "falsos sinais. Considere aumentar o threshold de delta (ex: de 5 para 10)."
            )

    # Confluence baixo?
    pct_conf = score_stats.get("pct_confluence", 0)
    if pct_conf < 10:
        suggestions.append(
            f"Apenas {pct_conf}% das leituras com confluencia Score+Delta. "
            "Considere ajustar os thresholds de delta_bullish/bearish para capturar mais alinhamentos."
        )

    # Ativos com baixa contribuição
    if asset_stats and "contributions" in asset_stats:
        contribs = asset_stats["contributions"]
        low_impact = contribs[contribs["contrib_abs_mean"] < 0.001]
        if len(low_impact) > 3:
            names = ", ".join(low_impact.index.tolist())
            suggestions.append(
                f"Ativos com contribuicao quase nula: {names}. "
                "Considere remover ou reduzir peso para simplificar o sistema."
            )

    # Sinais
    if signal_stats and signal_stats.get("total_signals", 0) > 0:
        counts = signal_stats.get("signal_counts", {})
        for sig_type, count in counts.items():
            if count > 20:
                suggestions.append(
                    f"Sinal '{sig_type}' gerado {count} vezes. Muito frequente. "
                    "Considere ajustar thresholds para ser mais seletivo."
                )

    if not suggestions:
        suggestions.append("Nenhuma otimizacao urgente identificada. Sistema parece bem calibrado.")

    return suggestions


def print_report(target_date: str = None):
    """Imprime relatório completo de análise."""
    print("\n" + "=" * 60)
    print("  ANALISE DE LOGS - MACRO SCORING WIN")
    print("=" * 60)

    # Carrega logs
    print(f"\n  Carregando logs...")
    logs = load_logs("logs", target_date)

    if not logs:
        print("\n  Nenhum log encontrado!")
        return

    # Análise de Score
    print("\n" + "-" * 60)
    print("  DISTRIBUICAO DO SCORE")
    print("-" * 60)

    score_df = logs.get("score")
    score_stats = analyze_score_distribution(score_df)
    if score_stats:
        print(f"  Total de leituras: {score_stats['total_reads']}")
        print(f"  Periodo: {score_stats.get('time_range', 'N/A')}")
        print(f"  Media: {score_stats['score_mean']} | Std: {score_stats['score_std']}")
        print(f"  Min: {score_stats['score_min']} | Max: {score_stats['score_max']}")
        print(f"\n  ZONAS:")
        print(f"    Forte Alta (>=60):        {score_stats.get('zona_forte_alta', 0):3d} ({score_stats.get('pct_forte_alta', 0):5.1f}%)")
        print(f"    Moderada Alta (30-60):    {score_stats.get('zona_moderada_alta', 0):3d} ({score_stats.get('pct_moderada_alta', 0):5.1f}%)")
        print(f"    Neutro (-30 a 30):        {score_stats.get('zona_neutro', 0):3d} ({score_stats.get('pct_neutro', 0):5.1f}%)")
        print(f"    Moderada Baixa (-60--30): {score_stats.get('zona_moderada_baixa', 0):3d} ({score_stats.get('pct_moderada_baixa', 0):5.1f}%)")
        print(f"    Forte Baixa (<=-60):      {score_stats.get('zona_forte_baixa', 0):3d} ({score_stats.get('pct_forte_baixa', 0):5.1f}%)")
        print(f"\n  CONFLUENCIA: {score_stats.get('confluence_count', 0)} ({score_stats.get('pct_confluence', 0):.1f}%)")
        print(f"  REVERSOES:   {score_stats.get('reversal_count', 0)} ({score_stats.get('pct_reversal', 0):.1f}%)")

    # Análise de Ativos
    print("\n" + "-" * 60)
    print("  CONTRIBUICAO DOS ATIVOS (top 10 por impacto)")
    print("-" * 60)

    asset_df = logs.get("asset")
    asset_stats = analyze_asset_contributions(asset_df)
    if asset_stats and "contributions" in asset_stats:
        top = asset_stats["contributions"].head(10)
        print(f"  {'Ativo':12s} {'Contrib Media':>13s} {'Contrib Abs':>11s} {'Var Media':>10s} {'Leituras':>9s}")
        for name, row in top.iterrows():
            print(f"  {name:12s} {row['contrib_mean']:+13.4f} {row['contrib_abs_mean']:11.4f} {row['change_mean']:+10.2f}% {int(row['reads']):9d}")

    # Análise de Sinais
    print("\n" + "-" * 60)
    print("  SINAIS DE ENTRADA")
    print("-" * 60)

    signal_df = logs.get("signal")
    signal_stats = analyze_signals(signal_df)
    if signal_stats:
        print(f"  Total de sinais: {signal_stats.get('total_signals', 0)}")
        if signal_stats.get("signal_counts"):
            for sig_type, count in signal_stats["signal_counts"].items():
                print(f"    {sig_type}: {count}")
        print(f"  Confluencia: {signal_stats.get('confluence_signals', 0)}")
        print(f"  Reversoes:   {signal_stats.get('reversal_signals', 0)}")

    # Análise de Delta
    print("\n" + "-" * 60)
    print("  PADROES DE DELTA")
    print("-" * 60)

    delta_stats = analyze_delta_patterns(score_df) if score_df is not None else {}
    if delta_stats:
        print(f"  Cruzamentos de zero: {delta_stats.get('delta_zero_crossings', 0)}")
        print(f"  Transicoes de zona:  {delta_stats.get('zone_transitions', 0)}")
        print(f"  Volatilidade delta:  {delta_stats.get('delta_volatility', 0)}")
        print(f"  Delta medio abs:     {delta_stats.get('avg_delta_magnitude', 0)}")
        print(f"  Max delta positivo:  {delta_stats.get('max_positive_delta', 0)}")
        print(f"  Max delta negativo:  {delta_stats.get('max_negative_delta', 0)}")

    # Sugestões
    print("\n" + "-" * 60)
    print("  SUGESTOES DE OTIMIZACAO")
    print("-" * 60)

    suggestions = suggest_optimizations(score_stats, asset_stats, signal_stats, delta_stats)
    for i, s in enumerate(suggestions, 1):
        print(f"\n  [{i}] {s}")

    print("\n" + "=" * 60)

    # Exporta análise para CSV
    if score_stats:
        report_path = os.path.join("logs", f"{target_date or date.today().strftime('%Y%m%d')}_analysis.txt")
        os.makedirs("logs", exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("ANALISE DE LOGS - MACRO SCORING WIN\n")
            f.write(f"Data: {target_date or date.today().strftime('%Y%m%d')}\n\n")
            f.write("DISTRIBUICAO DO SCORE\n")
            for k, v in score_stats.items():
                f.write(f"  {k}: {v}\n")
            f.write("\nSUGESTOES\n")
            for i, s in enumerate(suggestions, 1):
                f.write(f"  [{i}] {s}\n")
        print(f"  Relatorio salvo em: {report_path}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    print_report(target)
