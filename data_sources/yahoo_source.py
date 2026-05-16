"""
Fonte de Dados: Yahoo Finance
================================
Busca dados de ativos internacionais e macro que nao estao no MT5.
Fallback para ativos B3 quando MT5 nao esta disponivel.
v9.1: Corrigido para ETFs brasileiros (IFNC/IMAT/ICON) que retornam
      apenas 1 candle com period="5d". Agora usa estrategia progressiva:
      5d -> 1mo -> fast_info.previous_close -> info.previousClose
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
    logger.warning("yfinance NAO encontrado. Instale com: pip install yfinance")


class YahooFinanceSource:
    """Fonte de dados via Yahoo Finance para ativos macro internacionais."""
    
    def __init__(self):
        self._cache = {}
        self._cache_timestamp = {}
        self.cache_duration = 30  # segundos
    
    def is_available(self) -> bool:
        """Verifica se Yahoo Finance esta disponivel."""
        return YF_AVAILABLE
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Obtem preco atual de um ativo via Yahoo Finance."""
        if not YF_AVAILABLE:
            return None
        
        try:
            ticker = yf.Ticker(symbol)
            try:
                price = ticker.fast_info.last_price
                if price and price > 0:
                    return float(price)
            except:
                pass
            
            hist = ticker.history(period="1d")
            if hist is not None and not hist.empty:
                return float(hist['Close'].iloc[-1])
            
            return None
            
        except Exception as e:
            logger.debug(f"YF: Erro ao buscar preco de '{symbol}': {e}")
            return None
    
    def get_previous_close(self, symbol: str) -> Optional[float]:
        """Obtem o fechamento anterior via Yahoo Finance."""
        if not YF_AVAILABLE:
            return None
        
        try:
            ticker = yf.Ticker(symbol)
            
            try:
                prev = ticker.fast_info.previous_close
                if prev and prev > 0:
                    return float(prev)
            except:
                pass
            
            hist = ticker.history(period="5d")
            if hist is not None and len(hist) >= 2:
                return float(hist['Close'].iloc[-2])
            
            return None
            
        except Exception as e:
            logger.debug(f"YF: Erro ao buscar fechamento anterior de '{symbol}': {e}")
            return None
    
    def get_daily_candles(self, symbol: str, days: int = 30) -> Optional[list]:
        """Obtem candles diarios via Yahoo Finance."""
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
        Obtem dados completos de um ativo via Yahoo Finance.
        v9.1: Corrigido para ETFs brasileiros (IFNC/IMAT/ICON) que retornam
        apenas 1 candle com period="5d". Agora tenta:
        1. Historico progressivo (5d -> 1mo)
        2. fast_info.previous_close (para ETFs com historico limitado)
        3. info.previousClose (ultimo recurso)
        """
        if not YF_AVAILABLE:
            return None
        
        try:
            ticker = yf.Ticker(symbol)
            prev_close = None
            current_price = None
            
            # Estrategia 1: Historico progressivo (5d -> 1mo)
            for period in ["5d", "1mo"]:
                hist = ticker.history(period=period)
                if hist is not None and not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    if len(hist) >= 2:
                        prev_close = float(hist['Close'].iloc[-2])
                        break
                    # Se so tem 1 candle, tenta proximo periodo
                    continue
            
            # Estrategia 2: fast_info para previous_close (ETFs com historico curto)
            if prev_close is None and current_price is not None:
                try:
                    fi_prev = ticker.fast_info.previous_close
                    if fi_prev and fi_prev > 0:
                        prev_close = float(fi_prev)
                except Exception:
                    pass
            
            # Estrategia 3: Tenta .info para previousClose
            if prev_close is None and current_price is not None:
                try:
                    info = ticker.info
                    if info and info.get('previousClose'):
                        prev_close = float(info['previousClose'])
                except Exception:
                    pass
            
            if current_price is None:
                return None
            
            result = {
                "source": "yahoo_finance",
                "symbol": symbol,
                "current_price": current_price,
                "timestamp": datetime.now(),
            }
            
            if prev_close is not None and prev_close > 0:
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
        """Busca dados de multiplos ativos de forma eficiente."""
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
    """Busca em lote para multiplos ativos (mais eficiente)."""
    
    @staticmethod
    def download_batch(symbols: dict, period: str = "1mo") -> Dict[str, dict]:
        """
        Usa yf.download para buscar multiplos ativos de uma vez.
        v9.1: Periodo padrao alterado para "1mo" para ETFs brasileiros.
        Handles new yfinance MultiIndex columns format + timeout.
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
                    close_series = None
                    
                    if is_multiindex:
                        try:
                            close_series = data[('Close', yf_symbol)].dropna()
                        except (KeyError, TypeError):
                            try:
                                close_series = data[(yf_symbol, 'Close')].dropna()
                            except (KeyError, TypeError):
                                close_cols = [c for c in data.columns if c[0] == 'Close' and yf_symbol in str(c)]
                                if close_cols:
                                    close_series = data[close_cols[0]].dropna()
                    elif is_multi_ticker:
                        try:
                            ticker_data = data[yf_symbol]
                            close_series = ticker_data['Close'].dropna()
                        except (KeyError, TypeError):
                            pass
                    else:
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
                        # v9.1: Para ETFs com 1 candle, tenta fast_info
                        try:
                            t = yf.Ticker(yf_symbol)
                            fi_prev = t.fast_info.previous_close
                            if fi_prev and fi_prev > 0:
                                result["previous_close"] = float(fi_prev)
                                result["change_pct"] = ((current_price - float(fi_prev)) / float(fi_prev)) * 100
                                result["change_points"] = current_price - float(fi_prev)
                            else:
                                result["previous_close"] = None
                                result["change_pct"] = None
                                result["change_points"] = None
                        except Exception:
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
