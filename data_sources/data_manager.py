"""
Gerenciador de Dados - MT5 (Primário) + Yahoo Finance (Fallback)
=================================================================
Tenta buscar dados primeiro no MT5 (Rico), e se não conseguir,
usa Yahoo Finance como fallback automaticamente.
Inclui tracking do preço WIN para detecção de divergência.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from .mt5_source import MT5Source
from .yahoo_source import YahooFinanceSource, YahooFinanceBatch

logger = logging.getLogger(__name__)


class DataManager:
    """
    Gerenciador de dados que coordena MT5 e Yahoo Finance.
    
    Fluxo:
    1. Para ativos B3: tenta MT5 primeiro, depois Yahoo Finance
    2. Para ativos macro internacionais: vai direto ao Yahoo Finance
    3. Para WIN: busca separadamente para divergência
    4. Combina todos os dados para alimentar o scoring
    """
    
    def __init__(self, mt5_config: dict = None, dual_source: dict = None,
                 yf_only: dict = None, mt5_only: dict = None, win_tracking: dict = None):
        self.mt5 = MT5Source(mt5_config or {})
        self.yf = YahooFinanceSource()
        self.yf_batch = YahooFinanceBatch()
        
        self.dual_source = dual_source or {}
        self.yf_only = yf_only or {}
        self.mt5_only = mt5_only or {}
        self.win_tracking = win_tracking or {}
        
        self._mt5_connected = False
        self._last_data = {}
        self._last_update = None
    
    def connect_mt5(self) -> tuple:
        """Tenta conectar ao MT5. Returns: Tuple (sucesso, mensagem)."""
        success = self.mt5.connect()
        self._mt5_connected = success
        
        if success:
            return True, "MT5 conectado com sucesso!"
        else:
            return False, "MT5 nao disponivel. Usando Yahoo Finance como fallback."
    
    def disconnect_mt5(self):
        """Desconecta do MT5."""
        self.mt5.disconnect()
        self._mt5_connected = False
    
    def is_mt5_connected(self) -> bool:
        """Verifica se MT5 está conectado."""
        return self._mt5_connected and self.mt5.is_available()
    
    def get_win_data(self) -> Optional[dict]:
        """
        Busca dados do WIN para detecção de divergência.
        Tenta MT5 primeiro, depois Yahoo Finance (proxy).
        
        Returns:
            Dict com dados do WIN ou None
        """
        if not self.win_tracking.get("enabled", True):
            return None

        # Tenta MT5 primeiro
        mt5_symbol = self.win_tracking.get("mt5_symbol", "WINN25")
        if self.is_mt5_connected():
            data = self.mt5.get_asset_data(mt5_symbol)
            if data:
                data["internal_name"] = "WIN"
                data["source_primary"] = "mt5"
                return data

        # Fallback: usa proxy (EWZ ou IBOV)
        yf_proxy = self.win_tracking.get("yf_symbol", "EWZ")
        data = self.yf.get_asset_data(yf_proxy)
        if data:
            data["internal_name"] = "WIN_PROXY"
            data["source_primary"] = "yahoo_finance"
            data["proxy_for"] = "WIN"
            data["proxy_symbol"] = yf_proxy
            return data

        return None

    def get_all_data(self) -> Dict[str, dict]:
        """
        Busca dados de TODOS os ativos configurados + WIN.
        
        Returns:
            Dict {nome_interno: dados_do_ativo}
        """
        all_data = {}
        errors = []
        
        # ---- 1. Ativos Dual Source (MT5 → YF fallback) ----
        for name, sources in self.dual_source.items():
            data = self._get_dual_source_data(name, sources)
            if data:
                all_data[name] = data
            else:
                errors.append(name)
        
        # ---- 2. Ativos só no Yahoo Finance (macro internacional) ----
        yf_results = self.yf_batch.download_batch(self.yf_only)
        all_data.update(yf_results)
        
        for name in self.yf_only:
            if name not in yf_results:
                try:
                    data = self.yf.get_asset_data(self.yf_only[name])
                    if data:
                        data["internal_name"] = name
                        all_data[name] = data
                    else:
                        errors.append(name)
                except:
                    errors.append(name)
        
        # ---- 3. Ativos só no MT5 ----
        for name, mt5_symbol in self.mt5_only.items():
            if self.is_mt5_connected():
                data = self.mt5.get_asset_data(mt5_symbol)
                if data:
                    data["internal_name"] = name
                    all_data[name] = data
                else:
                    errors.append(name)
            else:
                errors.append(name)

        # ---- 4. WIN para divergência ----
        win_data = self.get_win_data()
        if win_data:
            # Usa "WIN" como chave, mas pode ser proxy
            name = "WIN" if win_data.get("internal_name") == "WIN" else "EWZ"
            if name not in all_data:
                all_data[name] = win_data
        
        self._last_data = all_data
        self._last_update = datetime.now()
        
        if errors:
            logger.warning(f"Ativos sem dados: {errors}")
        
        return all_data
    
    def _get_dual_source_data(self, name: str, sources: dict) -> Optional[dict]:
        """Busca dados de um ativo dual source: MT5 primeiro, YF como fallback."""
        mt5_symbol = sources.get("mt5")
        yf_symbol = sources.get("yf")
        
        if mt5_symbol and self.is_mt5_connected():
            data = self.mt5.get_asset_data(mt5_symbol)
            if data:
                data["internal_name"] = name
                data["source_primary"] = "mt5"
                return data
        
        if yf_symbol:
            data = self.yf.get_asset_data(yf_symbol)
            if data:
                data["internal_name"] = name
                data["source_primary"] = "yahoo_finance"
                return data
        
        return None
    
    def get_summary(self) -> dict:
        """Retorna resumo do status das fontes de dados."""
        return {
            "mt5_connected": self.is_mt5_connected(),
            "yf_available": self.yf.is_available(),
            "last_update": self._last_update,
            "assets_with_data": len(self._last_data),
            "total_assets_configured": (
                len(self.dual_source) + len(self.yf_only) + len(self.mt5_only)
            ),
        }
