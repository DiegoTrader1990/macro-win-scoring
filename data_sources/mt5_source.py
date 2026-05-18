"""
Fonte de Dados: MetaTrader 5 (Corretora Rico)
================================================
Conecta ao MT5 e busca dados em tempo real dos ativos B3.
O MT5 DEVE estar aberto e logado na Rico para funcionar.
v11.0: Reconexao automatica, melhor tratamento de erros,
       suporte a caminho customizado do terminal Rico.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Tentativa de importar MetaTrader5 (so funciona no Windows com MT5 instalado)
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
    logger.info("MetaTrader5 package encontrado")
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 package NAO encontrado. Instale com: pip install MetaTrader5")

# Caminhos comuns do MT5 Rico no Windows
RICO_PATHS = [
    r"C:\Program Files\Rico\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\Rico\MetaTrader 5\terminal64.exe",
    r"C:\Rico\MetaTrader 5\terminal64.exe",
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
]


class MT5Source:
    """Fonte de dados via MetaTrader 5 (Corretora Rico)."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.connected = False
        self._symbol_info_cache = {}
        self._last_connect_attempt = 0
        self._connect_cooldown = 30  # segundos entre tentativas de conexao

    def _find_rico_path(self) -> Optional[str]:
        """Tenta encontrar o caminho do terminal Rico."""
        import os
        # Primeiro, verifica se o config tem path
        if self.config.get("path"):
            return self.config["path"]
        # Tenta caminhos comuns
        for path in RICO_PATHS:
            if os.path.isfile(path):
                return path
        return None

    def connect(self) -> bool:
        """
        Conecta ao MT5. Requer MT5 aberto e logado na Rico.

        Returns:
            bool: True se conectou com sucesso
        """
        if not MT5_AVAILABLE:
            logger.error("MetaTrader5 nao esta instalado. pip install MetaTrader5")
            return False

        # Cooldown entre tentativas
        import time
        now = time.time()
        if now - self._last_connect_attempt < self._connect_cooldown:
            return False
        self._last_connect_attempt = now

        # Prepara argumentos
        kwargs = {}
        path = self._find_rico_path()
        if path:
            kwargs["path"] = path

        login = self.config.get("login")
        password = self.config.get("password")
        server = self.config.get("server", "Rico")

        if login and password:
            kwargs["login"] = int(login)
            kwargs["password"] = password
            kwargs["server"] = server

        try:
            # Shutdown anterior se existir
            try:
                mt5.shutdown()
            except Exception:
                pass

            if not mt5.initialize(**kwargs):
                error = mt5.last_error()
                logger.error(f"MT5 initialize falhou: {error}")
                self.connected = False
                return False

            # Verifica se esta conectado
            account_info = mt5.account_info()
            if account_info is None:
                logger.error("MT5: Nao foi possivel obter info da conta")
                self.connected = False
                return False

            logger.info(f"MT5 conectado: {account_info.server} | Conta: {account_info.login}")
            self.connected = True
            return True

        except Exception as e:
            logger.error(f"Erro ao conectar MT5: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Desconecta do MT5."""
        if MT5_AVAILABLE and self.connected:
            try:
                mt5.shutdown()
            except Exception:
                pass
            self.connected = False
            logger.info("MT5 desconectado")

    def is_available(self) -> bool:
        """Verifica se o MT5 esta disponivel e conectado."""
        if not self.connected:
            return False
        try:
            info = mt5.account_info()
            return info is not None
        except Exception:
            self.connected = False
            return False

    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Obtem informacoes de um simbolo no MT5."""
        if not self.connected:
            return None

        if symbol in self._symbol_info_cache:
            return self._symbol_info_cache[symbol]

        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                logger.debug(f"MT5: Simbolo '{symbol}' nao encontrado")
                return None

            # Habilita no Market Watch se necessario
            if not info.visible:
                if mt5.symbol_select(symbol, True):
                    logger.info(f"MT5: Simbolo '{symbol}' adicionado ao Market Watch")

            result = {
                "name": info.name,
                "bid": info.bid,
                "ask": info.ask,
                "last": info.last,
                "volume": info.volume,
                "trade_mode": info.trade_mode,
                "point": info.point,
                "digits": info.digits,
                "spread": info.spread,
            }
            self._symbol_info_cache[symbol] = result
            return result

        except Exception as e:
            logger.error(f"Erro ao buscar info de '{symbol}': {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Obtem preco atual de um ativo via MT5."""
        if not self.connected:
            return None
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            if tick.last > 0:
                return tick.last
            elif tick.bid > 0 and tick.ask > 0:
                return (tick.bid + tick.ask) / 2
            elif tick.bid > 0:
                return tick.bid
            return None
        except Exception as e:
            logger.debug(f"MT5: Erro ao buscar preco de '{symbol}': {e}")
            return None

    def get_previous_close(self, symbol: str) -> Optional[float]:
        """Obtem o fechamento do pregao anterior."""
        if not self.connected:
            return None
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 1, 2)
            if rates is None or len(rates) < 2:
                return None
            return float(rates[0]['close'])
        except Exception as e:
            logger.debug(f"MT5: Erro ao buscar fechamento anterior de '{symbol}': {e}")
            return None

    def get_daily_candles(self, symbol: str, days: int = 30) -> Optional[list]:
        """Obtem candles diarios de um ativo."""
        if not self.connected:
            return None
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, days)
            if rates is None:
                return None
            candles = []
            for r in rates:
                candles.append({
                    "date": datetime.fromtimestamp(r['time']),
                    "open": float(r['open']),
                    "high": float(r['high']),
                    "low": float(r['low']),
                    "close": float(r['close']),
                    "volume": int(r['tick_volume']),
                })
            return candles
        except Exception as e:
            logger.debug(f"MT5: Erro ao buscar candles de '{symbol}': {e}")
            return None

    def get_asset_data(self, symbol: str) -> Optional[dict]:
        """Obtem dados completos de um ativo para o scoring."""
        if not self.connected:
            return None
        try:
            current_price = self.get_current_price(symbol)
            prev_close = self.get_previous_close(symbol)

            if current_price is None:
                return None

            result = {
                "source": "mt5",
                "symbol": symbol,
                "current_price": current_price,
                "previous_close": prev_close,
                "timestamp": datetime.now(),
            }

            if prev_close and prev_close > 0:
                result["change_pct"] = ((current_price - prev_close) / prev_close) * 100
                result["change_points"] = current_price - prev_close
            else:
                result["change_pct"] = None
                result["change_points"] = None

            return result

        except Exception as e:
            logger.debug(f"MT5: Erro ao buscar dados de '{symbol}': {e}")
            return None

    def test_connection(self) -> Tuple[bool, str]:
        """Testa a conexao com o MT5 e retorna status detalhado."""
        if not MT5_AVAILABLE:
            return False, "MetaTrader5 package nao instalado. Execute: pip install MetaTrader5"
        try:
            if not mt5.initialize():
                error = mt5.last_error()
                return False, f"MT5 nao inicializou. Erro: {error}. Verifique se o MT5 esta aberto."

            info = mt5.account_info()
            if info is None:
                mt5.shutdown()
                return False, "MT5 inicializou mas nao encontrou conta. Faca login no MT5 primeiro."

            msg = f"Conectado ao servidor: {info.server} | Conta: {info.login} | Nome: {info.name}"
            mt5.shutdown()
            return True, msg
        except Exception as e:
            return False, f"Erro de conexao: {e}"
