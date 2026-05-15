"""
Fonte de Dados por Setor - Multi-Timeframe
============================================
Busca dados de ativos agrupados por setor com variacoes
em multiplos timeframes (5m, 15m, dia) para o painel principal.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False


class SectorDataManager:
    """
    Gerenciador de dados por setor com suporte a multi-timeframe.

    Busca variacoes de 5min, 15min e dia para cada ativo dentro
    de um grupo de setor. Usa cache para evitar requests excessivos.
    """

    def __init__(self, sector_groups: dict, config: dict = None):
        self.sector_groups = sector_groups
        self.config = config or {}
        self.cache_duration = self.config.get("cache_duration", 30)
        self._cache = {}
        self._cache_ts = {}

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache_ts:
            return False
        elapsed = (datetime.now() - self._cache_ts[key]).total_seconds()
        return elapsed < self.cache_duration

    def _get_variation(self, symbol: str, interval: str, period: str) -> Optional[float]:
        """
        Busca variacao percentual para um simbolo em determinado timeframe.

        Args:
            symbol: Ticker Yahoo Finance
            interval: Intervalo dos candles ("5m", "15m", "1d")
            period: Periodo de busca ("1d", "5d")

        Returns:
            Variacao percentual ou None
        """
        if not YF_AVAILABLE:
            return None

        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist is None or hist.empty or len(hist) < 2:
                return None

            close = hist['Close'].dropna()
            if len(close) < 2:
                return None

            first = float(close.iloc[0])
            last = float(close.iloc[-1])

            if first == 0:
                return None

            return ((last - first) / first) * 100

        except Exception as e:
            logger.debug(f"SectorData: erro {symbol} {interval}: {e}")
            return None

    def _get_asset_full_data(self, symbol: str) -> Optional[dict]:
        """
        Busca dados completos de um ativo: preco, variacao dia,
        variacao 5m e 15m.
        """
        if not YF_AVAILABLE:
            return None

        result = {
            "source": "sector_data",
            "timestamp": datetime.now(),
        }

        # Dados do dia (preco atual + variacao intraday)
        try:
            ticker = yf.Ticker(symbol)
            hist_5d = ticker.history(period="5d", interval="1d")

            if hist_5d is not None and not hist_5d.empty:
                close_5d = hist_5d['Close'].dropna()
                if len(close_5d) >= 1:
                    result["current_price"] = float(close_5d.iloc[-1])

                if len(close_5d) >= 2:
                    prev_close = float(close_5d.iloc[-2])
                    curr = float(close_5d.iloc[-1])
                    result["change_pct"] = ((curr - prev_close) / prev_close) * 100
                    result["previous_close"] = prev_close
                else:
                    result["change_pct"] = 0.0
                    result["previous_close"] = None
        except Exception as e:
            logger.debug(f"SectorData: erro dia {symbol}: {e}")
            result["current_price"] = None
            result["change_pct"] = None
            result["previous_close"] = None

        # Variacao 5min
        var_5m = self._get_variation(symbol, "5m", "1d")
        result["change_5m"] = var_5m

        # Variacao 15min
        var_15m = self._get_variation(symbol, "15m", "5d")
        result["change_15m"] = var_15m

        return result

    def get_sector_data(self, sector_name: str) -> Optional[dict]:
        """
        Busca dados de todos os ativos de um setor.

        Returns:
            Dict com dados do setor e seus ativos
        """
        cache_key = f"sector_{sector_name}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        sector_config = self.sector_groups.get(sector_name)
        if not sector_config:
            return None

        assets_data = {}
        sector_changes = []

        for asset_name, asset_info in sector_config["assets"].items():
            yf_symbol = asset_info["yf"]
            display = asset_info.get("display", asset_name)

            data = self._get_asset_full_data(yf_symbol)
            if data:
                data["display_name"] = display
                data["asset_key"] = asset_name
                assets_data[asset_name] = data

                # Acumula variacao para media do setor
                if data.get("change_pct") is not None:
                    sector_changes.append(data["change_pct"])

        # Score do setor (media das variacoes normalizada)
        sector_score = 0.0
        if sector_changes:
            avg = sum(sector_changes) / len(sector_changes)
            # Normaliza: >2% = forte, >0.5% = moderado
            sector_score = max(-100, min(100, avg * 50))

        result = {
            "name": sector_name,
            "icon": sector_config["icon"],
            "color": sector_config["color"],
            "description": sector_config.get("description", ""),
            "assets": assets_data,
            "sector_score": round(sector_score, 1),
            "sector_avg_change": round(sum(sector_changes) / len(sector_changes), 2) if sector_changes else 0,
        }

        self._cache[cache_key] = result
        self._cache_ts[cache_key] = datetime.now()
        return result

    def get_all_sectors(self) -> Dict[str, dict]:
        """Busca dados de todos os setores configurados."""
        results = {}
        for sector_name in self.sector_groups:
            data = self.get_sector_data(sector_name)
            if data:
                results[sector_name] = data
        return results

    def get_market_feeling(self, sectors_data: dict) -> dict:
        """
        Calcula o feeling geral do mercado baseado nos setores.

        Returns:
            Dict com feeling, direcao, forca
        """
        if not sectors_data:
            return {
                "feeling": "INDEFINIDO",
                "direction": 0,
                "strength": 0,
                "bullish_sectors": 0,
                "bearish_sectors": 0,
                "total_sectors": 0,
            }

        scores = []
        bullish = 0
        bearish = 0

        for sector_name, data in sectors_data.items():
            score = data.get("sector_score", 0)
            scores.append(score)
            if score > 10:
                bullish += 1
            elif score < -10:
                bearish += 1

        avg_score = sum(scores) / len(scores) if scores else 0

        if avg_score > 30:
            feeling = "FORTE ALTA"
        elif avg_score > 10:
            feeling = "ALTA MODERADA"
        elif avg_score > -10:
            feeling = "NEUTRO"
        elif avg_score > -30:
            feeling = "BAIXA MODERADA"
        else:
            feeling = "FORTE BAIXA"

        return {
            "feeling": feeling,
            "direction": round(avg_score, 1),
            "strength": round(abs(avg_score), 1),
            "bullish_sectors": bullish,
            "bearish_sectors": bearish,
            "total_sectors": len(sectors_data),
        }
