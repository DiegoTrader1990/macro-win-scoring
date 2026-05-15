"""
Sistema de Logs para Análise e Otimização
==========================================
Grava todos os dados de scoring, delta, sinais e preços em arquivos
CSV/JSONL para análise posterior e ajuste de gatilhos.

Logs gerados:
- score_log.csv: Score, delta, momentum, sinal por leitura
- asset_log.csv: Preço e variação de cada ativo por leitura
- signal_log.csv: Gatilhos de entrada detectados
- session_log.jsonl: Eventos da sessão (conexão, erros, etc.)
"""

import os
import csv
import json
import logging
from datetime import datetime, date
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class MacroLogger:
    """
    Logger dedicado para o sistema de macro scoring.
    
    Grava dados em CSV para facilitar análise em Excel/Pandas
    e JSONL para eventos estruturados.
    """

    def __init__(self, config: dict = None, base_dir: str = None):
        """
        Args:
            config: Dict com configurações de log (do config.LOG_CONFIG)
            base_dir: Diretório base do projeto (onde fica a pasta logs/)
        """
        self.config = config or {}
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = os.path.join(self.base_dir, self.config.get("log_dir", "logs"))

        # Cria diretório de logs se não existe
        os.makedirs(self.log_dir, exist_ok=True)

        # Contador de leituras para log_every_n_reads
        self._read_count = 0
        self._session_start = datetime.now()
        self._session_id = self._session_start.strftime("%Y%m%d_%H%M%S")

        # Arquivos CSV - com data no nome para organização
        today = date.today().strftime("%Y%m%d")
        self.score_log_path = os.path.join(
            self.log_dir, f"{today}_{self.config.get('score_log_file', 'score_log.csv')}"
        )
        self.asset_log_path = os.path.join(
            self.log_dir, f"{today}_{self.config.get('asset_log_file', 'asset_log.csv')}"
        )
        self.signal_log_path = os.path.join(
            self.log_dir, f"{today}_{self.config.get('signal_log_file', 'signal_log.csv')}"
        )
        self.session_log_path = os.path.join(
            self.log_dir, f"{today}_{self.config.get('session_log_file', 'session_log.jsonl')}"
        )

        # Inicializa headers dos CSVs se arquivos não existem
        self._init_csv_files()

        # Log de sessão
        self._log_session_event("SESSION_START", {"session_id": self._session_id})

        # Limpa logs antigos
        self._cleanup_old_logs()

    def _init_csv_files(self):
        """Cria arquivos CSV com headers se não existem."""
        # Score log
        if not os.path.exists(self.score_log_path):
            with open(self.score_log_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'date', 'time', 'session_id',
                    'score', 'signal_type', 'signal_label', 'confidence',
                    'delta', 'momentum', 'entry_type', 'entry_label',
                    'confluence_aligned', 'reversal_detected',
                    'assets_available', 'assets_total',
                    'raw_score', 'total_weight_used',
                ])

        # Asset log
        if not os.path.exists(self.asset_log_path):
            with open(self.asset_log_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'date', 'time', 'session_id',
                    'asset', 'category', 'source',
                    'price', 'prev_close', 'change_pct',
                    'direction', 'correlation', 'weight',
                    'signal', 'contribution',
                ])

        # Signal log
        if not os.path.exists(self.signal_log_path):
            with open(self.signal_log_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'date', 'time', 'session_id',
                    'signal_type', 'entry_label', 'confidence',
                    'score', 'delta', 'momentum',
                    'confluence_aligned', 'reversal_detected',
                    'suggested_side', 'action',
                ])

    def log_score(self, score_result: dict, delta_result: dict = None):
        """
        Registra uma leitura completa do score.

        Args:
            score_result: Resultado do MacroScorer.calculate_score()
            delta_result: Resultado do DeltaAnalyzer.get_entry_signal()
        """
        if not self.config.get("enable_score_log", True):
            return

        self._read_count += 1
        log_every = self.config.get("log_every_n_reads", 1)
        if self._read_count % log_every != 0:
            return

        now = datetime.now()
        delta_info = delta_result or {}
        entry = delta_info.get("entry_signal", {})
        confluence = delta_info.get("confluence", {})

        try:
            with open(self.score_log_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    now.isoformat(),
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M:%S"),
                    self._session_id,
                    score_result.get("score", 0),
                    score_result.get("signal", {}).get("type", ""),
                    score_result.get("signal", {}).get("label", ""),
                    score_result.get("signal", {}).get("confidence", ""),
                    delta_info.get("delta", 0),
                    delta_info.get("momentum", 0),
                    entry.get("type", ""),
                    entry.get("label", ""),
                    confluence.get("score_delta_aligned", False),
                    confluence.get("reversal_detected", False),
                    score_result.get("assets_available", 0),
                    score_result.get("assets_total", 0),
                    score_result.get("raw_score", 0),
                    score_result.get("total_weight_used", 0),
                ])
        except Exception as e:
            logger.error(f"Erro ao gravar score_log: {e}")

    def log_assets(self, score_result: dict, all_data: dict = None):
        """
        Registra dados de cada ativo individual.

        Args:
            score_result: Resultado do MacroScorer.calculate_score()
            all_data: Dados brutos do DataManager (com preços e prev_close)
        """
        if not self.config.get("enable_asset_log", True):
            return

        now = datetime.now()
        asset_signals = score_result.get("asset_signals", {})

        try:
            with open(self.asset_log_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for asset_name, data in asset_signals.items():
                    # Busca dados brutos se disponíveis
                    raw = (all_data or {}).get(asset_name, {})

                    writer.writerow([
                        now.isoformat(),
                        now.strftime("%Y-%m-%d"),
                        now.strftime("%H:%M:%S"),
                        self._session_id,
                        asset_name,
                        data.get("category", ""),
                        data.get("source", ""),
                        data.get("current_price", ""),
                        raw.get("previous_close", ""),
                        data.get("change_pct", ""),
                        "DIRETA" if data.get("direction", 1) > 0 else "INVERSA",
                        data.get("correlation", 0),
                        data.get("weight", 0),
                        data.get("signal", 0),
                        data.get("contribution", 0),
                    ])
        except Exception as e:
            logger.error(f"Erro ao gravar asset_log: {e}")

    def log_signal(self, delta_result: dict, score_result: dict):
        """
        Registra apenas quando há sinal de entrada (não registra NEUTRO).

        Args:
            delta_result: Resultado do DeltaAnalyzer.get_entry_signal()
            score_result: Resultado do MacroScorer.calculate_score()
        """
        if not self.config.get("enable_signal_log", True):
            return

        entry = delta_result.get("entry_signal", {})
        # Só loga sinais que não são NEUTRO
        if entry.get("type", "NEUTRO") == "NEUTRO":
            return

        now = datetime.now()
        confluence = delta_result.get("confluence", {})

        try:
            with open(self.signal_log_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    now.isoformat(),
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M:%S"),
                    self._session_id,
                    entry.get("type", ""),
                    entry.get("label", ""),
                    entry.get("confidence", ""),
                    score_result.get("score", 0),
                    delta_result.get("delta", 0),
                    delta_result.get("momentum", 0),
                    confluence.get("score_delta_aligned", False),
                    confluence.get("reversal_detected", False),
                    entry.get("suggested_side", ""),
                    entry.get("action", ""),
                ])
        except Exception as e:
            logger.error(f"Erro ao gravar signal_log: {e}")

    def _log_session_event(self, event_type: str, data: dict = None):
        """Registra evento de sessão em JSONL."""
        if not self.config.get("enable_session_log", True):
            return

        now = datetime.now()
        event = {
            "timestamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "session_id": self._session_id,
            "event_type": event_type,
            "data": data or {},
        }

        try:
            with open(self.session_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Erro ao gravar session_log: {e}")

    def log_mt5_event(self, success: bool, message: str):
        """Registra evento de conexão MT5."""
        self._log_session_event("MT5_CONNECTION", {
            "success": success,
            "message": message,
        })

    def log_error(self, error_type: str, message: str, details: dict = None):
        """Registra erro."""
        self._log_session_event("ERROR", {
            "error_type": error_type,
            "message": message,
            "details": details or {},
        })

    def log_data_fetch(self, assets_ok: int, assets_total: int, missing: list):
        """Registra resultado de busca de dados."""
        self._log_session_event("DATA_FETCH", {
            "assets_ok": assets_ok,
            "assets_total": assets_total,
            "missing_assets": missing,
            "success_rate": round(assets_ok / max(assets_total, 1) * 100, 1),
        })

    def log_full_cycle(self, score_result: dict, delta_result: dict, all_data: dict):
        """
        Registra ciclo completo: score + ativos + sinal.
        Chamada única que grava todos os logs de uma vez.
        """
        self.log_score(score_result, delta_result)
        self.log_assets(score_result, all_data)
        self.log_signal(delta_result, score_result)

        # Log de fetch
        missing = score_result.get("missing_assets", [])
        available = score_result.get("assets_available", 0)
        total = score_result.get("assets_total", 0)
        self.log_data_fetch(available, total, missing)

    def close_session(self):
        """Fecha a sessão de logs."""
        duration = (datetime.now() - self._session_start).total_seconds()
        self._log_session_event("SESSION_END", {
            "session_id": self._session_id,
            "duration_seconds": round(duration, 1),
            "total_reads": self._read_count,
        })

    def _cleanup_old_logs(self):
        """Remove logs mais antigos que retention_days."""
        retention = self.config.get("retention_days", 90)
        if retention <= 0:
            return

        cutoff = datetime.now().timestamp() - (retention * 86400)

        try:
            for filename in os.listdir(self.log_dir):
                filepath = os.path.join(self.log_dir, filename)
                if os.path.isfile(filepath):
                    file_mtime = os.path.getmtime(filepath)
                    if file_mtime < cutoff:
                        os.remove(filepath)
                        logger.info(f"Log antigo removido: {filename}")
        except Exception as e:
            logger.error(f"Erro ao limpar logs antigos: {e}")

    def get_log_summary(self) -> dict:
        """Retorna resumo dos logs existentes."""
        files = {}
        total_size = 0

        try:
            for filename in os.listdir(self.log_dir):
                filepath = os.path.join(self.log_dir, filename)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath)
                    total_size += size
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    files[filename] = {
                        "size_kb": round(size / 1024, 1),
                        "last_modified": mtime.strftime("%Y-%m-%d %H:%M"),
                    }
        except:
            pass

        return {
            "log_dir": self.log_dir,
            "total_files": len(files),
            "total_size_kb": round(total_size / 1024, 1),
            "files": files,
            "session_id": self._session_id,
            "reads_this_session": self._read_count,
        }
