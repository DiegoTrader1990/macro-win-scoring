"""
Fonte de Dados: MetaTrader 5 (Corretora Rico)
================================================
Conecta ao MT5 e busca dados em tempo real dos ativos B3.
O MT5 DEVE estar aberto e logado na Rico para funcionar.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Tentativa de importar MetaTrader5 (só funciona no Windows com MT5 instalado)
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
    logger.info("MetaTrader5 package encontrado")
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 package NÃO encontrado. Instale com: pip install MetaTrader5")


class MT5Source:
    """Fonte de dados via MetaTrader 5 (Corretora Rico)."""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.connected = False
        self._symbol_info_cache = {}
    
    def connect(self) -> bool:
        """
        Conecta ao MT5. Requer MT5 aberto e logado na Rico.
        
        Returns:
            bool: True se conectou com sucesso
        """
        if not MT5_AVAILABLE:
            logger.error("MetaTrader5 não está instalado. pip install MetaTrader5")
            return False
        
        # Inicializa MT5
        path = self.config.get("path")
        login = self.config.get("login")
        password = self.config.get("password")
        server = self.config.get("server", "Rico")
        
        kwargs = {}
        if path:
            kwargs["path"] = path
        if login and password:
            kwargs["login"] = int(login)
            kwargs["password"] = password
            kwargs["server"] = server
        
        try:
            if not mt5.initialize(**kwargs):
                error = mt5.last_error()
                logger.error(f"MT5 initialize falhou: {error}")
                return False
            
            # Verifica se está conectado à Rico
            account_info = mt5.account_info()
            if account_info is None:
                logger.error("MT5: Não foi possível obter info da conta")
                return False
            
            logger.info(f"MT5 conectado: {account_info.server} | Conta: {account_info.login}")
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Erro ao conectar MT5: {e}")
            return False
    
    def disconnect(self):
        """Desconecta do MT5."""
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("MT5 desconectado")
    
    def is_available(self) -> bool:
        """Verifica se o MT5 está disponível e conectado."""
        if not self.connected:
            return False
        try:
            info = mt5.account_info()
            return info is not None
        except:
            return False
    
    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """
        Obtém informações de um símbolo no MT5.
        
        Args:
            symbol: Ticker no MT5 (ex: "WINN25", "VALE3")
        
        Returns:
            Dict com info do símbolo ou None se não encontrado
        """
        if not self.connected:
            return None
        
        if symbol in self._symbol_info_cache:
            return self._symbol_info_cache[symbol]
        
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                logger.debug(f"MT5: Símbolo '{symbol}' não encontrado")
                return None
            
            # Habilita o símbolo no Market Watch se necessário
            if not info.visible:
                if mt5.symbol_select(symbol, True):
                    logger.info(f"MT5: Símbolo '{symbol}' adicionado ao Market Watch")
                else:
                    logger.warning(f"MT5: Não foi possível adicionar '{symbol}' ao Market Watch")
            
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
        """
        Obtém preço atual de um ativo via MT5.
        
        Args:
            symbol: Ticker no MT5
        
        Returns:
            Preço atual ou None se não disponível
        """
        if not self.connected:
            return None
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            
            # Para ativos com spread, usa mid-price
            if tick.last > 0:
                return tick.last
            elif tick.bid > 0 and tick.ask > 0:
                return (tick.bid + tick.ask) / 2
            elif tick.bid > 0:
                return tick.bid
            
            return None
            
        except Exception as e:
            logger.debug(f"MT5: Erro ao buscar preço de '{symbol}': {e}")
            return None
    
    def get_previous_close(self, symbol: str) -> Optional[float]:
        """
        Obtém o fechamento do pregão anterior.
        
        Args:
            symbol: Ticker no MT5
        
        Returns:
            Preço de fechamento anterior ou None
        """
        if not self.connected:
            return None
        
        try:
            # Busca o último candle diário completo
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 1, 2)
            if rates is None or len(rates) < 2:
                return None
            
            # O penúltimo candle é o fechamento anterior
            prev_close = rates[0]['close']
            return float(prev_close)
            
        except Exception as e:
            logger.debug(f"MT5: Erro ao buscar fechamento anterior de '{symbol}': {e}")
            return None
    
    def get_daily_candles(self, symbol: str, days: int = 30) -> Optional[list]:
        """
        Obtém candles diários de um ativo.
        
        Args:
            symbol: Ticker no MT5
            days: Número de candles/dias
        
        Returns:
            Lista de dicts com dados OHLCV ou None
        """
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
    
    def get_intraday_data(self, symbol: str, minutes: int = 60) -> Optional[list]:
        """
        Obtém dados intraday de um ativo.
        
        Args:
            symbol: Ticker no MT5
            minutes: Minutos retroativos
        
        Returns:
            Lista de dicts com dados intraday ou None
        """
        if not self.connected:
            return None
        
        try:
            now = datetime.now()
            rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M5, now - timedelta(minutes=minutes), minutes // 5)
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
            logger.debug(f"MT5: Erro ao buscar intraday de '{symbol}': {e}")
            return None
    
    def get_asset_data(self, symbol: str) -> Optional[dict]:
        """
        Obtém dados completos de um ativo para o scoring.
        
        Args:
            symbol: Ticker no MT5
        
        Returns:
            Dict com preço atual, variação, fechamento anterior, etc.
        """
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
            
            # Calcula variação do dia
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
        """
        Testa a conexão com o MT5 e retorna status detalhado.
        
        Returns:
            Tuple (sucesso: bool, mensagem: str)
        """
        if not MT5_AVAILABLE:
            return False, "MetaTrader5 package não instalado. Execute: pip install MetaTrader5"
        
        try:
            if not mt5.initialize():
                error = mt5.last_error()
                return False, f"MT5 não inicializou. Erro: {error}. Verifique se o MT5 está aberto."
            
            info = mt5.account_info()
            if info is None:
                mt5.shutdown()
                return False, "MT5 inicializou mas não encontrou conta. Faça login no MT5 primeiro."
            
            msg = f"Conectado ao servidor: {info.server} | Conta: {info.login} | Nome: {info.name}"
            mt5.shutdown()
            return True, msg
            
        except Exception as e:
            return False, f"Erro de conexão: {e}"
