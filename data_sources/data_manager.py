"""
Gerenciador de Dados - MT5 (Primario) + Yahoo Finance (Fallback)
=================================================================
Tenta buscar dados primeiro no MT5 (Rico), e se nao conseguir,
usa Yahoo Finance como fallback automaticamente.
Inclui tracking do preco WIN para deteccao de divergencia.
v10.2: Diagnostico de conexao + fallback individual robusto + nunca retorna vazio
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
    3. Para WIN: busca separadamente para divergencia
    4. Combina todos os dados para alimentar o scoring
    
    v10.2: NUNCA retorna dicionario vazio sem log detalhado.
           Sempre tenta pelo menos obter dados parciais.
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
        self._diagnostic = {}  # v10.2: Status de diagnostico
        
        # v10.2: Log da configuracao
        logger.info(f"DataManager: {len(self.dual_source)} dual, {len(self.yf_only)} YF, {len(self.mt5_only)} MT5")
    
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
        """Verifica se MT5 esta conectado."""
        return self._mt5_connected and self.mt5.is_available()
    
    def get_win_data(self) -> Optional[dict]:
        """
        Busca dados do WIN para deteccao de divergencia.
        Tenta MT5 primeiro, depois Yahoo Finance (proxy).
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
        
        # v10.2: Tenta BVSP como ultimo recurso
        yf_direct = self.win_tracking.get("yf_direct", "^BVSP")
        if yf_direct != yf_proxy:
            data = self.yf.get_asset_data(yf_direct)
            if data:
                data["internal_name"] = "WIN_PROXY"
                data["source_primary"] = "yahoo_finance"
                data["proxy_for"] = "WIN"
                data["proxy_symbol"] = yf_direct
                return data

        return None

    def get_all_data(self) -> Dict[str, dict]:
        """
        Busca dados de TODOS os ativos configurados + WIN.
        
        v10.2: Nunca desiste completamente. Se batch falhar, tenta individual.
        Se individual falhar, retorna o que tiver com diagnostico.
        
        Returns:
            Dict {nome_interno: dados_do_ativo}
        """
        all_data = {}
        errors = []
        self._diagnostic = {
            "start_time": datetime.now(),
            "mt5_connected": self.is_mt5_connected(),
            "yf_available": self.yf.is_available(),
        }
        
        # ---- 1. Ativos Dual Source (MT5 -> YF fallback) ----
        for name, sources in self.dual_source.items():
            data = self._get_dual_source_data(name, sources)
            if data:
                all_data[name] = data
            else:
                errors.append(name)
        
        # ---- 2. Ativos so no Yahoo Finance (macro internacional) ----
        # v10.2: O batch agora tem fallback individual integrado
        yf_results = self.yf_batch.download_batch(self.yf_only)
        all_data.update(yf_results)
        
        # v10.2: Se batch+individual falhou completamente, tenta um a um com retry
        missing_yf = [n for n in self.yf_only if n not in yf_results]
        if missing_yf and len(yf_results) == 0:
            logger.warning(f"YF Batch falhou completamente. Tentando {len(missing_yf)} ativos individualmente...")
            for name in missing_yf:
                try:
                    data = self.yf.get_asset_data(self.yf_only[name])
                    if data:
                        data["internal_name"] = name
                        data["source"] = "yahoo_finance_emergency"
                        all_data[name] = data
                except Exception:
                    pass
        
        for name in self.yf_only:
            if name not in all_data:
                errors.append(name)
        
        # ---- 3. Ativos so no MT5 ----
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

        # ---- 4. WIN para divergencia ----
        win_data = self.get_win_data()
        if win_data:
            # Usa "WIN" como chave, mas pode ser proxy
            name = "WIN" if win_data.get("internal_name") == "WIN" else "EWZ"
            if name not in all_data:
                all_data[name] = win_data
        
        self._last_data = all_data
        self._last_update = datetime.now()
        
        # v10.2: Diagnostico detalhado
        total_configured = len(self.dual_source) + len(self.yf_only) + len(self.mt5_only)
        self._diagnostic["end_time"] = datetime.now()
        self._diagnostic["total_configured"] = total_configured
        self._diagnostic["assets_with_data"] = len(all_data)
        self._diagnostic["assets_missing"] = len(errors)
        self._diagnostic["missing_list"] = errors[:10]
        self._diagnostic["success_rate"] = f"{len(all_data)}/{total_configured}"
        
        if errors:
            logger.warning(f"Ativos sem dados ({len(errors)}): {errors[:10]}")
        
        if len(all_data) == 0:
            logger.error("DataManager: NENHUM dado obtido! Verifique conexao internet e Yahoo Finance.")
        elif len(all_data) < total_configured * 0.5:
            logger.warning(f"DataManager: Dados parciais - apenas {len(all_data)}/{total_configured} ativos")
        else:
            logger.info(f"DataManager: {len(all_data)}/{total_configured} ativos com dados")
        
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
        summary = {
            "mt5_connected": self.is_mt5_connected(),
            "yf_available": self.yf.is_available(),
            "last_update": self._last_update,
            "assets_with_data": len(self._last_data),
            "total_assets_configured": (
                len(self.dual_source) + len(self.yf_only) + len(self.mt5_only)
            ),
        }
        # v10.2: Inclui diagnostico
        if self._diagnostic:
            summary["diagnostic"] = self._diagnostic
        return summary
    
    def get_diagnostic(self) -> dict:
        """v10.2: Retorna diagnostico detalhado da ultima busca."""
        return self._diagnostic
