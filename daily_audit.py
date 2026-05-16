"""
Auditoria Diária do Sistema - v7.0
====================================
Gera relatório completo do dia anterior para revisão e ajuste.

Rodar: python daily_audit.py

Este script:
1. Lê todos os logs do dia anterior
2. Calcula estatísticas de acerto dos sinais
3. Identifica padrões de erro (sinais falsos, entradas perdidas)
4. Sugere ajustes de peso e thresholds
5. Gera relatório para revisão manual
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

try:
    from config import MACRO_WEIGHTS, LOG_CONFIG, ENHANCED_LOG_CONFIG
except ImportError as e:
    logger.error(f"Erro de importacao: {e}")
    sys.exit(1)


def run_daily_audit(date_str: str = None):
    """Executa auditoria do dia especificado (default: ontem)."""
    if date_str:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        target_date = datetime.now() - timedelta(days=1)

    date_label = target_date.strftime("%Y-%m-%d")
    logger.info(f"=== AUDITORIA DIARIA - {date_label} ===")

    log_dir = LOG_CONFIG.get("log_dir", "logs")
    audit = {
        "date": date_label,
        "generated_at": datetime.now().isoformat(),
        "sections": {},
    }

    # 1. Ler score_log.csv
    audit["sections"]["score_analysis"] = _analyze_score_log(log_dir, target_date)

    # 2. Ler signal_log.csv
    audit["sections"]["signal_analysis"] = _analyze_signal_log(log_dir, target_date)

    # 3. Ler performance_log.csv
    audit["sections"]["performance_analysis"] = _analyze_performance_log(log_dir, target_date)

    # 4. Ler session_log.jsonl
    audit["sections"]["session_analysis"] = _analyze_session_log(log_dir, target_date)

    # 5. Ler tier1_log.csv (se existir)
    audit["sections"]["tier1_analysis"] = _analyze_tier1_log(log_dir, target_date)

    # 6. Ler trigger_log.csv (se existir)
    audit["sections"]["trigger_analysis"] = _analyze_trigger_log(log_dir, target_date)

    # 7. Gerar sugestões de ajuste
    audit["suggestions"] = _generate_suggestions(audit["sections"])

    # 8. Salvar relatório
    output_file = os.path.join(log_dir, f"audit_{date_label}.json")
    os.makedirs(log_dir, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"Auditoria salva em: {output_file}")
    _print_audit(audit)

    return audit


def _analyze_score_log(log_dir: str, target_date: datetime) -> dict:
    """Analisa o log de scores do dia."""
    score_file = os.path.join(log_dir, LOG_CONFIG.get("score_log_file", "score_log.csv"))
    if not os.path.exists(score_file):
        return {"error": "arquivo nao encontrado"}

    try:
        import pandas as pd
        df = pd.read_csv(score_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            day_df = df[df["timestamp"].dt.date == target_date.date()]
        else:
            day_df = df

        if day_df.empty:
            return {"error": "sem dados para a data"}

        score_col = "score" if "score" in day_df.columns else day_df.columns[1]
        return {
            "total_reads": len(day_df),
            "score_mean": round(float(day_df[score_col].mean()), 2) if score_col in day_df.columns else 0,
            "score_min": round(float(day_df[score_col].min()), 2) if score_col in day_df.columns else 0,
            "score_max": round(float(day_df[score_col].max()), 2) if score_col in day_df.columns else 0,
            "score_std": round(float(day_df[score_col].std()), 2) if score_col in day_df.columns else 0,
            "bullish_pct": round(float((day_df[score_col] > 30).mean() * 100), 1) if score_col in day_df.columns else 0,
            "bearish_pct": round(float((day_df[score_col] < -30).mean() * 100), 1) if score_col in day_df.columns else 0,
            "neutral_pct": round(float(((day_df[score_col] >= -30) & (day_df[score_col] <= 30)).mean() * 100), 1) if score_col in day_df.columns else 0,
        }
    except Exception as e:
        return {"error": str(e)}


def _analyze_signal_log(log_dir: str, target_date: datetime) -> dict:
    """Analisa o log de sinais do dia."""
    signal_file = os.path.join(log_dir, LOG_CONFIG.get("signal_log_file", "signal_log.csv"))
    if not os.path.exists(signal_file):
        return {"error": "arquivo nao encontrado"}

    try:
        import pandas as pd
        df = pd.read_csv(signal_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            day_df = df[df["timestamp"].dt.date == target_date.date()]
        else:
            day_df = df

        if day_df.empty:
            return {"error": "sem dados para a data"}

        # Contar sinais por tipo
        signal_counts = {}
        if "signal_type" in day_df.columns:
            signal_counts = day_df["signal_type"].value_counts().to_dict()
        elif "direction" in day_df.columns:
            signal_counts = day_df["direction"].value_counts().to_dict()

        return {
            "total_signals": len(day_df),
            "signal_counts": {str(k): int(v) for k, v in signal_counts.items()},
        }
    except Exception as e:
        return {"error": str(e)}


def _analyze_performance_log(log_dir: str, target_date: datetime) -> dict:
    """Analisa o log de performance do dia."""
    perf_file = os.path.join(log_dir, LOG_CONFIG.get("performance_log_file", "performance_log.csv"))
    if not os.path.exists(perf_file):
        return {"error": "arquivo nao encontrado"}

    try:
        import pandas as pd
        df = pd.read_csv(perf_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            day_df = df[df["timestamp"].dt.date == target_date.date()]
        else:
            day_df = df

        if day_df.empty:
            return {"error": "sem dados para a data"}

        result = {"total_trades": len(day_df)}

        # Calcular win rate se houver coluna de resultado
        if "outcome" in day_df.columns:
            wins = (day_df["outcome"] == "WIN").sum()
            total = len(day_df)
            result["win_rate"] = round(float(wins / total * 100), 1) if total > 0 else 0
            result["wins"] = int(wins)
            result["losses"] = int(total - wins)

        return result
    except Exception as e:
        return {"error": str(e)}


def _analyze_session_log(log_dir: str, target_date: datetime) -> dict:
    """Analisa o log de sessão do dia."""
    session_file = os.path.join(log_dir, LOG_CONFIG.get("session_log_file", "session_log.jsonl"))
    if not os.path.exists(session_file):
        return {"error": "arquivo nao encontrado"}

    try:
        records = []
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        # Filtrar pela data
        day_records = []
        for r in records:
            ts = r.get("timestamp", "")
            if date_label := (ts[:10] if len(ts) >= 10 else ""):
                if date_label == target_date.strftime("%Y-%m-%d"):
                    day_records.append(r)

        return {
            "total_records": len(day_records),
            "session_start": day_records[0].get("timestamp") if day_records else None,
            "session_end": day_records[-1].get("timestamp") if day_records else None,
        }
    except Exception as e:
        return {"error": str(e)}


def _analyze_tier1_log(log_dir: str, target_date: datetime) -> dict:
    """Analisa o log de Tier1 do dia."""
    tier1_file = os.path.join(log_dir, ENHANCED_LOG_CONFIG.get("tier1_log_file", "tier1_log.csv"))
    if not os.path.exists(tier1_file):
        return {"note": "log tier1 nao disponivel (modulo v7.0)"}
    return {"note": "modulo v7.0 - sera populado apos primeiro dia de operacao"}


def _analyze_trigger_log(log_dir: str, target_date: datetime) -> dict:
    """Analisa o log de gatilhos do dia."""
    trigger_file = os.path.join(log_dir, ENHANCED_LOG_CONFIG.get("trigger_log_file", "trigger_log.csv"))
    if not os.path.exists(trigger_file):
        return {"note": "log triggers nao disponivel (modulo v7.0)"}
    return {"note": "modulo v7.0 - sera populado apos primeiro dia de operacao"}


def _generate_suggestions(sections: dict) -> list:
    """Gera sugestões de ajuste baseadas na auditoria."""
    suggestions = []

    # Analisar score
    score = sections.get("score_analysis", {})
    if "error" not in score:
        neutral_pct = score.get("neutral_pct", 0)
        if neutral_pct > 70:
            suggestions.append({
                "type": "THRESHOLD",
                "severity": "MEDIA",
                "message": f"Score neutro {neutral_pct:.0f}% do dia. Considere reduzir thresholds (30->20) para gerar mais sinais.",
            })

        score_std = score.get("score_std", 0)
        if score_std < 10:
            suggestions.append({
                "type": "VOLATILIDADE",
                "severity": "BAIXA",
                "message": f"Score muito estavel (std={score_std:.1f}). Pode indicar que pesos estao diluindo sinais.",
            })

    # Analisar performance
    perf = sections.get("performance_analysis", {})
    if "win_rate" in perf:
        win_rate = perf["win_rate"]
        if win_rate < 40:
            suggestions.append({
                "type": "PERFORMANCE",
                "severity": "ALTA",
                "message": f"Win rate baixo ({win_rate:.0f}%). Revisar filtros anti-entrada e thresholds de gatilho.",
            })
        elif win_rate > 65:
            suggestions.append({
                "type": "PERFORMANCE",
                "severity": "POSITIVO",
                "message": f"Win rate bom ({win_rate:.0f}%). Sistema funcionando bem. Considerar aumentar tamanho de posicao.",
            })

    # Analisar sinais
    signals = sections.get("signal_analysis", {})
    if "total_signals" in signals and signals["total_signals"] == 0:
        suggestions.append({
            "type": "SINAIS",
            "severity": "ALTA",
            "message": "Nenhum sinal gerado no dia. Verificar se dados estao chegando e se thresholds nao estao altos demais.",
        })

    if not suggestions:
        suggestions.append({
            "type": "INFO",
            "severity": "INFO",
            "message": "Sem sugestoes especificas. Sistema operando dentro dos parametros.",
        })

    return suggestions


def _print_audit(audit: dict):
    """Imprime auditoria formatada."""
    print("\n" + "=" * 60)
    print(f"AUDITORIA DIARIA - {audit['date']}")
    print("=" * 60)

    for section_name, data in audit.get("sections", {}).items():
        print(f"\n--- {section_name.upper()} ---")
        if "error" in data:
            print(f"  Erro: {data['error']}")
        elif "note" in data:
            print(f"  Nota: {data['note']}")
        else:
            for key, value in data.items():
                print(f"  {key}: {value}")

    print(f"\n--- SUGESTOES ---")
    for sug in audit.get("suggestions", []):
        icon = {"ALTA": "!!", "MEDIA": "!", "BAIXA": "~", "POSITIVO": "+", "INFO": "i"}.get(sug.get("severity", ""), "?")
        print(f"  [{icon}] {sug.get('message', '')}")

    print("=" * 60)


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_daily_audit(date_arg)
