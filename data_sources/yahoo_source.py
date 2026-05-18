"""
Fonte de Dados: Yahoo Finance
================================
Busca dados de ativos internacionais e macro que nao estao no MT5.
Fallback para ativos B3 quando MT5 nao esta disponivel.
v11.0: REESCRITO - fetch individual por padrao (mais robusto),
       batch apenas como otimizacao opcional,
       yfinance 1.3.0 MultiIndex compat, sem timeout invalido,
       retry agressivo com backoff.
"""

import logging
import time as _time
from datetime import datetime
import pandas as pd
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YF_AVAILABLE = True
    YF_VERSION = getattr(yf, '__version__', '0.0.0')
    logger.info(f"yfinance {YF_VERSION} encontrado")
except ImportError:
    YF_AVAILABLE = False
    YF_VERSION = '0.0.0'
    logger.warning("yfinance NAO encontrado. Instale com: pip install yfinance")

# v11.0: Constantes de timeout e retry
MAX_RETRIES = 2
RETRY_BACKOFF = 1.5  # segundos entre retries
COOLDOWN_SECONDS = 90  # cooldown para simbolos que falharam


class YahooFinanceSource:
    """Fonte de dados via Yahoo Finance para ativos macro internacionais."""

    def __init__(self):
        self._cache = {}
        self._cache_timestamp = {}
        self.cache_duration = 30  # segundos
        self._failed_symbols = {}  # Track failures to avoid hammering

    def is_available(self) -> bool:
        """Verifica se Yahoo Finance esta disponivel."""
        return YF_AVAILABLE

    def _is_symbol_failed(self, symbol: str) -> bool:
        """Checa se simbolo falhou recentemente (evita retry infinito)."""
        if symbol in self._failed_symbols:
            fail_time = self._failed_symbols[symbol]
            if (_time.time() - fail_time) < COOLDOWN_SECONDS:
                return True
            else:
                del self._failed_symbols[symbol]
        return False

    def _mark_symbol_failed(self, symbol: str):
        """Marca simbolo como falho para evitar retry imediato."""
        self._failed_symbols[symbol] = _time.time()

    def _clear_symbol_failed(self, symbol: str):
        """Limpa falha ao sucesso."""
        self._failed_symbols.pop(symbol, None)

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
            except Exception:
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
            except Exception:
                pass
            hist = ticker.history(period="5d")
            if hist is not None and len(hist) >= 2:
                return float(hist['Close'].iloc[-2])
            return None
        except Exception as e:
            logger.debug(f"YF: Erro ao buscar fechamento anterior de '{symbol}': {e}")
            return None

    def get_asset_data(self, symbol: str, retry_count: int = 0) -> Optional[dict]:
        """
        Obtem dados completos de um ativo via Yahoo Finance.
        Estrategia progressiva:
        1. Historico (5d -> 1mo)
        2. fast_info.previous_close
        3. info.previousClose
        4. fast_info.last_price
        """
        if not YF_AVAILABLE:
            return None

        if self._is_symbol_failed(symbol):
            logger.debug(f"YF: Pulando '{symbol}' - falhou recentemente")
            return None

        try:
            ticker = yf.Ticker(symbol)
            prev_close = None
            current_price = None

            # Estrategia 1: Historico progressivo (5d -> 1mo)
            for period in ["5d", "1mo"]:
                try:
                    hist = ticker.history(period=period)
                    if hist is not None and not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                        if len(hist) >= 2:
                            prev_close = float(hist['Close'].iloc[-2])
                            break
                        continue  # So 1 candle, tenta proximo periodo
                except Exception as e:
                    logger.debug(f"YF: history({period}) falhou para '{symbol}': {e}")
                    continue

            # Estrategia 2: fast_info para previous_close
            if prev_close is None and current_price is not None:
                try:
                    fi_prev = ticker.fast_info.previous_close
                    if fi_prev and fi_prev > 0:
                        prev_close = float(fi_prev)
                except Exception:
                    pass

            # Estrategia 3: .info para previousClose
            if prev_close is None and current_price is not None:
                try:
                    info = ticker.info
                    if info and info.get('previousClose'):
                        prev_close = float(info['previousClose'])
                except Exception:
                    pass

            # Estrategia 4: fast_info.last_price
            if current_price is None:
                try:
                    price = ticker.fast_info.last_price
                    if price and price > 0:
                        current_price = float(price)
                        try:
                            fi_prev = ticker.fast_info.previous_close
                            if fi_prev and fi_prev > 0:
                                prev_close = float(fi_prev)
                        except Exception:
                            pass
                except Exception:
                    pass

            if current_price is None:
                if retry_count < MAX_RETRIES:
                    logger.warning(f"YF: Sem dados para '{symbol}', retry ({retry_count+1}/{MAX_RETRIES})...")
                    _time.sleep(RETRY_BACKOFF * (retry_count + 1))
                    result = self.get_asset_data(symbol, retry_count + 1)
                    if result:
                        return result
                self._mark_symbol_failed(symbol)
                logger.warning(f"YF: Falha definitiva para '{symbol}'")
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

            self._clear_symbol_failed(symbol)
            return result

        except Exception as e:
            logger.warning(f"YF: Erro ao buscar dados de '{symbol}': {e}")
            self._mark_symbol_failed(symbol)
            if retry_count < MAX_RETRIES:
                _time.sleep(RETRY_BACKOFF * (retry_count + 1))
                return self.get_asset_data(symbol, retry_count + 1)
            return None


class YahooFinanceBatch:
    """Busca em lote para multiplos ativos (mais eficiente)."""

    @staticmethod
    def _extract_close_series(data, yf_symbol, is_multi_ticker):
        """
        Extrai a serie Close para um simbolo do DataFrame do yf.download.
        Compativel com yfinance 1.3.0 (MultiIndex (ticker, field))
        e versoes antigas (MultiIndex (field, ticker)).
        """
        if data is None or data.empty:
            return None

        is_multiindex = isinstance(data.columns, pd.MultiIndex)

        if is_multiindex:
            _first_col = data.columns[0]

            # Detectar formato pela primeira coluna
            if _first_col[0] in ('Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close'):
                # FORMATO ANTIGO: ('Close', 'SYMBOL')
                col_key = ('Close', yf_symbol)
                alt_key = (yf_symbol, 'Close')
            else:
                # FORMATO NOVO: ('SYMBOL', 'Close') - yfinance >= 1.3.0
                col_key = (yf_symbol, 'Close')
                alt_key = ('Close', yf_symbol)

            # Tentar formato principal
            try:
                series = data[col_key].dropna()
                if len(series) > 0:
                    return series
            except (KeyError, TypeError):
                pass

            # Tentar formato alternativo
            try:
                series = data[alt_key].dropna()
                if len(series) > 0:
                    return series
            except (KeyError, TypeError):
                pass

            # Busca exaustiva
            for col in data.columns:
                try:
                    if len(col) == 2:
                        if (col[1] == 'Close' and yf_symbol in str(col[0])) or \
                           (col[0] == 'Close' and yf_symbol in str(col[1])):
                            series = data[col].dropna()
                            if len(series) > 0:
                                return series
                except Exception:
                    continue

            return None

        elif is_multi_ticker:
            try:
                ticker_data = data[yf_symbol]
                if isinstance(ticker_data, pd.DataFrame):
                    return ticker_data['Close'].dropna()
                elif isinstance(ticker_data, pd.Series):
                    return ticker_data.dropna()
            except (KeyError, TypeError):
                pass
            try:
                series = data[(yf_symbol, 'Close')].dropna()
                if len(series) > 0:
                    return series
            except (KeyError, TypeError):
                pass
            return None

        else:
            # Single ticker
            try:
                return data['Close'].dropna()
            except (KeyError, TypeError):
                return None

    @staticmethod
    def download_batch(symbols: dict, period: str = "1mo") -> Dict[str, dict]:
        """
        Busca dados em lote. v11.0: SEM timeout invalido no yf.download,
        compativel com yfinance 1.3.0, fallback individual robusto.
        """
        if not YF_AVAILABLE or not symbols:
            return {}

        results = {}
        failed_symbols = []

        # Tentar batch download
        try:
            tickers = list(symbols.values())
            names = list(symbols.keys())
            logger.info(f"YF Batch: Baixando {len(tickers)} ativos...")

            # v11.0: NAO passar timeout para yf.download
            data = yf.download(
                tickers,
                period=period,
                group_by="ticker",
                threads=True,
                progress=False,
            )

            if data is not None and not data.empty:
                is_multi_ticker = len(tickers) > 1

                for name, yf_symbol in symbols.items():
                    try:
                        close_series = YahooFinanceBatch._extract_close_series(
                            data, yf_symbol, is_multi_ticker
                        )

                        if close_series is None or len(close_series) < 1:
                            failed_symbols.append(name)
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
                        failed_symbols.append(name)
                        continue
            else:
                logger.warning("YF Batch: Nenhum dado retornado")
                failed_symbols = list(symbols.keys())

        except Exception as e:
            logger.error(f"YF Batch: Erro no download: {e}")
            failed_symbols = list(symbols.keys())

        # FALLBACK INDIVIDUAL para simbolos que falharam no batch
        if failed_symbols:
            logger.info(f"YF Batch: {len(failed_symbols)} ativos falharam no batch, tentando individualmente...")
            yf_source = YahooFinanceSource()

            for name in failed_symbols:
                if name in results:
                    continue

                yf_symbol = symbols.get(name)
                if not yf_symbol:
                    continue

                try:
                    data = yf_source.get_asset_data(yf_symbol)
                    if data:
                        data["internal_name"] = name
                        data["source"] = "yahoo_finance_individual"
                        results[name] = data
                        logger.info(f"YF Individual: '{name}' ({yf_symbol}) OK")
                    else:
                        logger.warning(f"YF Individual: '{name}' ({yf_symbol}) sem dados")
                except Exception as e:
                    logger.warning(f"YF Individual: Erro em '{name}': {e}")

        # Log diagnostico
        total = len(symbols)
        success = len(results)
        still_missing = [n for n in symbols if n not in results]

        if success > 0:
            logger.info(f"YF: {success}/{total} ativos com dados")
        else:
            logger.error(f"YF: NENHUM dado obtido de {total} ativos!")

        if still_missing and len(still_missing) <= 10:
            logger.warning(f"YF: Ativos sem dados: {still_missing}")

        return results


class YahooFinanceIndividual:
    """
    v11.0: Fetch individual como alternativa ao batch.
    Mais lento mas MUITO mais robusto.
    Usa YahooFinanceSource.get_asset_data para cada simbolo.
    """

    @staticmethod
    def fetch_all(symbols: dict) -> Dict[str, dict]:
        """Busca dados de todos os simbolos individualmente."""
        if not YF_AVAILABLE or not symbols:
            return {}

        results = {}
        yf_source = YahooFinanceSource()

        for name, yf_symbol in symbols.items():
            try:
                data = yf_source.get_asset_data(yf_symbol)
                if data:
                    data["internal_name"] = name
                    results[name] = data
            except Exception as e:
                logger.debug(f"YF Individual: Erro em '{name}': {e}")

        logger.info(f"YF Individual: {len(results)}/{len(symbols)} ativos com dados")
        return results
