"""
Sistema de Macro Scoring para Mini Índice (WIN) - Entry Point
===============================================================
Versão terminal (sem dashboard web). Para o dashboard interativo,
use: streamlit run dashboard/app.py

Este script roda o sistema no terminal com atualização automática.
"""

import sys
import os
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import MT5_CONFIG, DUAL_SOURCE_ASSETS, YF_SYMBOLS, MACRO_WEIGHTS, SIGNAL_CONFIG, LOG_CONFIG
from data_sources.data_manager import DataManager
from scoring.macro_score import MacroScorer
from scoring.delta import DeltaAnalyzer
from utils.helpers import format_change, format_price, get_score_color, get_score_bar
from utils.macro_logger import MacroLogger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def print_header():
    print("\n" + "=" * 70)
    print("  SISTEMA DE MACRO SCORING - MINI INDICE (WIN)")
    print("  MT5 (Rico) -> Yahoo Finance Fallback")
    print("=" * 70)


def print_score(score_result: dict, delta_result: dict = None):
    score = score_result.get("score", 0)
    signal = score_result.get("signal", {})
    
    print(f"\n  {'─' * 66}")
    print(f"  SCORE MACRO: {score:+.1f} {get_score_bar(score)}")
    print(f"  SINAL: {signal.get('emoji', '⚪')} {signal.get('label', 'N/A')}")
    print(f"  ACAO: {signal.get('action', 'N/A')}")
    
    if delta_result:
        entry = delta_result.get("entry_signal", {})
        delta = delta_result.get("delta", 0)
        momentum = delta_result.get("momentum", 0)
        
        print(f"  DELTA: {delta:+.1f} | MOMENTUM: {momentum:+.1f}")
        print(f"  ENTRADA: {entry.get('emoji', '⚪')} {entry.get('label', 'N/A')}")
        print(f"  CONFIANCA: {entry.get('confidence', 'N/A')}")
    
    print(f"  {'─' * 66}")


def print_categories(score_result: dict):
    category_scores = score_result.get("category_scores", {})
    
    print(f"\n  BREAKDOWN POR CATEGORIA:")
    for cat_name, cat_data in category_scores.items():
        normalized = cat_data.get("normalized", 0)
        bar = get_score_bar(normalized, width=15)
        print(f"    {cat_name:20s} {normalized:+6.1f} {bar}")


def print_assets(score_result: dict):
    asset_signals = score_result.get("asset_signals", {})
    
    print(f"\n  ATIVOS:")
    print(f"    {'Ativo':15s} {'Preco':>12s} {'Variacao':>10s} {'Direcao':>10s} {'Contrib':>10s} {'Fonte':>6s}")
    print(f"    {'─' * 65}")
    
    sorted_assets = sorted(
        asset_signals.items(),
        key=lambda x: abs(x[1].get("contribution", 0)),
        reverse=True
    )
    
    for name, data in sorted_assets:
        price = format_price(data.get("current_price"))
        change = format_change(data.get("change_pct"))
        direction = "↑" if data.get("direction", 1) > 0 else "↓"
        contribution = f"{data.get('contribution', 0):+.4f}"
        source = "MT5" if "mt5" in data.get("source", "") else "YF"
        
        print(f"    {name:15s} {price:>12s} {change:>10s} {direction:>10s} {contribution:>10s} {source:>6s}")


def main():
    print_header()
    
    # Inicializa componentes
    dm = DataManager(
        mt5_config=MT5_CONFIG,
        dual_source=DUAL_SOURCE_ASSETS,
        yf_only=YF_SYMBOLS,
    )
    
    scorer = MacroScorer(MACRO_WEIGHTS, SIGNAL_CONFIG)
    delta_analyzer = DeltaAnalyzer(SIGNAL_CONFIG)
    macro_logger = MacroLogger(LOG_CONFIG)
    
    # Tenta conectar MT5
    print("\n  Conectando ao MT5 (Rico)...")
    success, msg = dm.connect_mt5()
    macro_logger.log_mt5_event(success, msg)
    if success:
        print(f"  OK - {msg}")
    else:
        print(f"  AVISO - {msg}")
        print(f"  Usando Yahoo Finance como fonte principal.")
    
    # Loop principal
    refresh_count = 0
    interval = 30
    
    print(f"\n  Atualizacao automatica a cada {interval}s. Ctrl+C para sair.")
    print(f"  Logs salvos em: {macro_logger.log_dir}\n")
    
    try:
        while True:
            refresh_count += 1
            
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] Buscando dados... (#{refresh_count})")
            all_data = dm.get_all_data()
            
            score_result = scorer.calculate_score(all_data)
            
            delta_analyzer.update(score_result["score"])
            delta_result = delta_analyzer.get_entry_signal(score_result)
            
            # GRAVA LOGS
            macro_logger.log_full_cycle(score_result, delta_result, all_data)
            
            print_score(score_result, delta_result)
            print_categories(score_result)
            print_assets(score_result)
            
            missing = score_result.get("missing_assets", [])
            if missing:
                print(f"\n  Sem dados: {', '.join(missing)}")
            
            print(f"\n  Proxima atualizacao em {interval}s...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n\n  Sistema encerrado pelo usuario.")
        macro_logger.close_session()
        dm.disconnect_mt5()


if __name__ == "__main__":
    main()
