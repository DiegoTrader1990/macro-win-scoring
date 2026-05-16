"""
Fonte de Dados: Yahoo Finance
================================
Busca dados de ativos internacionais e macro que não estão no MT5.
Fallback para ativos B3 quando MT5 não está disponível.
"""

import logging
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YF_AVAILABLE = True
    logger.info("yfinance package encontrado")
except ImportError:
    YF_AVAILABLE = False
    logger.warning("yfinance NÃO encontrado. Instale com: pip install yfinance")


class YahooFinanceSource:
    """Fonte de dados via Yahoo Finance para ativos macro internacionais."""
    
    def __init__(self):
        self._cache = {}
        self._cache_timestamp = {}
        self.cache_duration = 30  # segundos
    
    def is_available(self) -> bool:
        """Verifica se Yahoo Finance está disponível."""
        return YF_AVAILABLE
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Obtém preço atual de um ativo via Yahoo Finance.
        
        Args:
            symbol: Ticker no Yahoo Finance (ex: "^GSPC", "DX-Y.NYB")
        
        Returns:
            Preço atual ou None
        """
        if not YF_AVAILABLE:
            return None
        
        try:
            ticker = yf.Ticker(symbol)
            # Usa fast_info para preço atual (mais rápido)
            try:
                price = ticker.fast_info.last_price
                if price and price > 0:
                    return float(price)
            except:
                pass
            
            # Fallback: busca histórico recente
            hist = ticker.history(period="1d")
            if hist is not None and not hist.empty:
                return float(hist['Close'].iloc[-1])
            
            return None
            
        except Exception as e:
            logger.debug(f"YF: Erro ao buscar preço de '{symbol}': {e}")
            return None
    
    def get_previous_close(self, symbol: str) -> Optional[float]:
        """
        Obtém o fechamento anterior via Yahoo Finance.
        
        Args:
            symbol: Ticker no Yahoo Finance
        
        Returns:
            Preço de fechamento anterior ou None
        """
        if not YF_AVAILABLE:
            return None
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Tenta fast_info primeiro
            try:
                prev = ticker.fast_info.previous_close
                if prev and prev > 0:
                    return float(prev)
            except:
                pass
            
            # Fallback: histórico de 5 dias
            hist = ticker.history(period="5d")
            if hist is not None and len(hist) >= 2:
                return float(hist['Close'].iloc[-2])
            
            return None
            
        except Exception as e:
            logger.debug(f"YF: Erro ao buscar fechamento anterior de '{symbol}': {e}")
            return None
    
    def get_daily_candles(self, symbol: str, days: int = 30) -> Optional[list]:
        """
        Obtém candles diários via Yahoo Finance.
        
        Args:
            symbol: Ticker no Yahoo Finance
            days: Número de dias
        
        Returns:
            Lista de dicts com dados OHLCV ou None
        """
        if not YF_AVAILABLE:
            return None
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=f"{days}d")
            
            if hist is None or hist.empty:
                return None
            
            candles = []
            for index, row in hist.iterrows():
                candles.append({
                    "date": index.to_pydatetime(),
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": int(row['Volume']),
                })
            return candles
            
        except Exception as e:
            logger.debug(f"YF: Erro ao buscar candles de '{symbol}': {e}")
            return None
    
    def get_asset_data(self, symbol: str) -> Optional[dict]:
        """
        Obtém dados completos de um ativo via Yahoo Finance.
        
        Args:
            symbol: Ticker no Yahoo Finance
        
        Returns:
            Dict com preço atual, variação, etc.
        """
        if not YF_AVAILABLE:
            return None
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Busca histórico de 5 dias (mais confiável que fast_info)
            hist = ticker.history(period="5d")
            
            if hist is None or hist.empty:
                return None
            
            current_price = float(hist['Close'].iloc[-1])
            
            result = {
                "source": "yahoo_finance",
                "symbol": symbol,
                "current_price": current_price,
                "timestamp": datetime.now(),
            }
            
            if len(hist) >= 2:
                prev_close = float(hist['Close'].iloc[-2])
                result["previous_close"] = prev_close
                result["change_pct"] = ((current_price - prev_close) / prev_close) * 100
                result["change_points"] = current_price - prev_close
            else:
                result["previous_close"] = None
                result["change_pct"] = None
                result["change_points"] = None
            
            return result
            
        except Exception as e:
            logger.debug(f"YF: Erro ao buscar dados de '{symbol}': {e}")
            return None
    
    def get_multi_asset_data(self, symbols: dict) -> Dict[str, dict]:
        """
        Busca dados de múltiplos ativos de forma eficiente.
        
        Args:
            symbols: Dict {nome_interno: ticker_yf}
        
        Returns:
            Dict {nome_interno: dados_do_ativo}
        """
        results = {}
        
        for name, yf_symbol in symbols.items():
            try:
                data = self.get_asset_data(yf_symbol)
                if data:
                    data["internal_name"] = name
                    results[name] = data
            except Exception as e:
                logger.warning(f"YF: Falha ao buscar '{name}' ({yf_symbol}): {e}")
        
        return results


class YahooFinanceBatch:
    """Busca em lote para múltiplos ativos (mais eficiente)."""
    
    @staticmethod
    def download_batch(symbols: dict, period: str = "5d") -> Dict[str, dict]:
        """
        Usa yf.download para buscar múltiplos ativos de uma vez.
        v8.0: Handles new yfinance MultiIndex columns format + timeout.
        
        Args:
            symbols: Dict {nome_interno: ticker_yf}
            period: Período (ex: "5d", "1mo")
        
        Returns:
            Dict {nome_interno: dados_do_ativo}
        """
        if not YF_AVAILABLE:
            return {}
        
        if not symbols:
            return {}
        
        try:
            tickers = list(symbols.values())
            names = list(symbols.keys())
            
            # Download em lote - with auto_adjust and timeout
            data = yf.download(tickers, period=period, group_by="ticker", 
                              threads=True, progress=False)
            
            if data is None or data.empty:
                logger.warning("YF Batch: No data returned")
                return {}
            
            # Handle both old and new yfinance column formats
            is_multi_ticker = len(tickers) > 1
            is_multiindex = isinstance(data.columns, pd.MultiIndex)
            
            results = {}
            for name, yf_symbol in symbols.items():
                try:
                    # Get Close column for this ticker
                    close_series = None
                    
                    if is_multiindex:
                        # New yfinance: columns are (Price, Ticker) or (Ticker, Price)
                        # Try (Close, ticker) format
                        try:
                            close_series = data[('Close', yf_symbol)].dropna()
                        except (KeyError, TypeError):
                            try:
                                close_series = data[(yf_symbol, 'Close')].dropna()
                            except (KeyError, TypeError):
                                # Try filtering
                                close_cols = [c for c in data.columns if c[0] == 'Close' and yf_symbol in str(c)]
                                if close_cols:
                                    close_series = data[close_cols[0]].dropna()
                    elif is_multi_ticker:
                        # Old format: data[ticker]['Close']
                        try:
                            ticker_data = data[yf_symbol]
                            close_series = ticker_data['Close'].dropna()
                        except (KeyError, TypeError):
                            pass
                    else:
                        # Single ticker: data['Close']
                        try:
                            close_series = data['Close'].dropna()
                        except (KeyError, TypeError):
                            pass
                    
                    if close_series is None or len(close_series) < 1:
                        continue
                    
                    current_price = float(close_series.iloc[-1])
                    
                    result = {
                        "source": "yahoo_finance_batch",
                        "symbol": yf_symbol,
                        "internal_name": name,
                        "current_price": current_price,
                        "timestamp": datetime.now(),
                    }
                    
                    if len(close_series) >= 2:
                        prev_close = float(close_series.iloc[-2])
                        result["previous_close"] = prev_close
                        result["change_pct"] = ((current_price - prev_close) / prev_close) * 100
                        result["change_points"] = current_price - prev_close
                    else:
                        result["previous_close"] = None
                        result["change_pct"] = None
                        result["change_points"] = None
                    
                    results[name] = result
                    
                except Exception as e:
                    logger.debug(f"YF Batch: Erro ao processar '{name}': {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"YF Batch: Erro no download: {e}")
            return {}
