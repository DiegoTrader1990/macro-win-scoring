"""
Dashboard Streamlit - Sistema de Macro Scoring para Mini Índice (WIN)
======================================================================
Dashboard web interativo com visualização em tempo real do score macro,
delta, sinais de entrada e breakdown por categoria/atiro.

Para rodar: streamlit run dashboard/app.py
"""

import sys
import os
import time
import logging
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import (
    MT5_CONFIG, DUAL_SOURCE_ASSETS, YF_SYMBOLS, MACRO_WEIGHTS,
    SIGNAL_CONFIG, CATEGORIES
)
from data_sources.data_manager import DataManager
from scoring.macro_score import MacroScorer
from scoring.delta import DeltaAnalyzer
from utils.helpers import format_change, format_price, get_change_color, get_score_color

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Macro Scoring - WIN",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a2e;
        text-align: center;
        padding: 1rem 0;
    }
    .score-big {
        font-size: 4rem;
        font-weight: 800;
        text-align: center;
        padding: 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
    }
    .signal-box {
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        font-size: 1.2rem;
        font-weight: 600;
    }
    .asset-card {
        padding: 0.5rem;
        border-radius: 8px;
        margin: 0.2rem 0;
        border-left: 4px solid;
    }
    .category-header {
        font-size: 1.1rem;
        font-weight: 700;
        padding: 0.5rem 0;
        margin-top: 1rem;
        border-bottom: 2px solid #e0e0e0;
    }
    .delta-positive { color: #00C853; }
    .delta-negative { color: #D50000; }
    .delta-neutral { color: #FFC107; }
    .stMetric > div > div > div {
        font-size: 1.5rem;
    }
    .refresh-info {
        text-align: center;
        color: #666;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# INICIALIZAÇÃO DO SESSION STATE
# ============================================================
def init_session_state():
    """Inicializa variáveis do session state."""
    if "data_manager" not in st.session_state:
        dm = DataManager(
            mt5_config=MT5_CONFIG,
            dual_source=DUAL_SOURCE_ASSETS,
            yf_only=YF_SYMBOLS,
        )
        st.session_state.data_manager = dm
        st.session_state.scorer = MacroScorer(MACRO_WEIGHTS, SIGNAL_CONFIG)
        st.session_state.delta_analyzer = DeltaAnalyzer(SIGNAL_CONFIG)
        st.session_state.score_history = []
        st.session_state.last_data = {}
        st.session_state.mt5_status = None
        st.session_state.auto_refresh = True
        st.session_state.refresh_count = 0


init_session_state()


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def refresh_data():
    """Busca dados atualizados e recalcula score."""
    dm = st.session_state.data_manager
    
    # Busca dados de todas as fontes
    all_data = dm.get_all_data()
    st.session_state.last_data = all_data
    
    # Calcula score
    scorer = st.session_state.scorer
    score_result = scorer.calculate_score(all_data)
    st.session_state.score_result = score_result
    
    # Atualiza delta
    delta_analyzer = st.session_state.delta_analyzer
    delta_analyzer.update(score_result["score"])
    
    # Salva no histórico
    st.session_state.score_history.append({
        "timestamp": datetime.now(),
        "score": score_result["score"],
        "signal_type": score_result["signal"]["type"],
    })
    
    # Limita histórico
    if len(st.session_state.score_history) > 500:
        st.session_state.score_history = st.session_state.score_history[-500:]
    
    st.session_state.refresh_count += 1
    st.session_state.last_refresh = datetime.now()
    
    return score_result


def connect_mt5():
    """Tenta conectar ao MT5."""
    dm = st.session_state.data_manager
    success, msg = dm.connect_mt5()
    st.session_state.mt5_status = {"success": success, "message": msg}
    return success


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## ⚙️ Configurações")
    
    # MT5 Connection
    st.markdown("### 🖥️ MetaTrader 5")
    mt5_connect = st.button("🔌 Conectar MT5 (Rico)", use_container_width=True)
    
    if mt5_connect:
        with st.spinner("Conectando ao MT5..."):
            success = connect_mt5()
            if success:
                st.success("MT5 conectado!")
            else:
                st.warning("MT5 não disponível. Usando Yahoo Finance como fallback.")
    
    # Status MT5
    if st.session_state.mt5_status:
        status = st.session_state.mt5_status
        if status["success"]:
            st.info(f"✅ {status['message']}")
        else:
            st.warning(f"⚠️ {status['message']}")
    else:
        dm = st.session_state.data_manager
        if dm.is_mt5_connected():
            st.info("✅ MT5 Conectado")
        else:
            st.warning("⚠️ MT5 Desconectado - Usando Yahoo Finance")
    
    st.divider()
    
    # Auto-refresh
    st.markdown("### 🔄 Atualização")
    auto_refresh = st.checkbox("Auto-refresh", value=st.session_state.auto_refresh)
    st.session_state.auto_refresh = auto_refresh
    
    if auto_refresh:
        interval = st.selectbox("Intervalo (segundos)", [15, 30, 60, 120], index=1)
    else:
        interval = 30
    
    # Manual refresh
    if st.button("🔄 Atualizar Agora", use_container_width=True):
        with st.spinner("Buscando dados..."):
            refresh_data()
    
    st.divider()
    
    # Ativos monitorados
    st.markdown("### 📊 Ativos Monitorados")
    st.caption(f"MT5 + YF: {len(DUAL_SOURCE_ASSETS)} ativos")
    st.caption(f"Yahoo Finance: {len(YF_SYMBOLS)} ativos")
    st.caption(f"Total: {len(DUAL_SOURCE_ASSETS) + len(YF_SYMBOLS)} ativos")
    
    st.divider()
    
    # Informações
    st.markdown("### ℹ️ Sobre")
    st.caption("Sistema de Macro Scoring para Mini Índice (WIN)")
    st.caption("Pesos baseados em correlações validadas com dados reais")
    st.caption("v1.0 - Maio 2025")


# ============================================================
# CONTEÚDO PRINCIPAL
# ============================================================

# Header
st.markdown('<div class="main-header">📊 Macro Scoring - Mini Índice (WIN)</div>', unsafe_allow_html=True)

# Busca dados iniciais se necessário
if not st.session_state.get("score_result"):
    with st.spinner("Carregando dados iniciais..."):
        refresh_data()

score_result = st.session_state.get("score_result", {})

if not score_result:
    st.error("Não foi possível carregar dados. Verifique sua conexão com a internet.")
    st.stop()

# ---- SCORE PRINCIPAL ----
score = score_result.get("score", 0)
signal = score_result.get("signal", {})
score_color = get_score_color(score)

col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    # Score grande
    st.markdown(f"""
    <div class="score-big" style="background-color: {score_color}22; border: 3px solid {score_color}; color: {score_color};">
        {score:+.1f}
    </div>
    <div class="signal-box" style="background-color: {score_color}22; color: {score_color};">
        {signal.get('emoji', '⚪')} {signal.get('label', 'N/A')}
    </div>
    """, unsafe_allow_html=True)

with col2:
    # Delta
    delta_info = st.session_state.delta_analyzer.get_entry_signal(score_result)
    delta_val = delta_info.get("delta", 0)
    entry = delta_info.get("entry_signal", {})
    
    if delta_val > 0:
        delta_class = "delta-positive"
        delta_sign = "+"
    elif delta_val < 0:
        delta_class = "delta-negative"
        delta_sign = ""
    else:
        delta_class = "delta-neutral"
        delta_sign = ""
    
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem;">
        <div style="font-size: 0.9rem; color: #666;">Delta</div>
        <div style="font-size: 2.5rem; font-weight: 700;" class="{delta_class}">
            {delta_sign}{delta_val:.1f}
        </div>
        <div style="font-size: 0.9rem; color: #666;">Momentum</div>
        <div style="font-size: 1.5rem; font-weight: 600;" class="{'delta-positive' if delta_info.get('momentum', 0) > 0 else 'delta-negative'}">
            {delta_info.get('momentum', 0):+.1f}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    # Sinal de entrada
    entry_emoji = entry.get("emoji", "⚪")
    entry_label = entry.get("label", "N/A")
    entry_color = "#666"
    if "COMPRA" in entry.get("type", ""):
        entry_color = "#00C853"
    elif "VENDA" in entry.get("type", ""):
        entry_color = "#D50000"
    elif "REVERSAO" in entry.get("type", ""):
        entry_color = "#FF9800"
    
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem;">
        <div style="font-size: 0.9rem; color: #666;">Sinal de Entrada</div>
        <div style="font-size: 1.8rem; font-weight: 700; color: {entry_color};">
            {entry_emoji}
        </div>
        <div style="font-size: 1rem; font-weight: 600; color: {entry_color};">
            {entry_label}
        </div>
        <div style="font-size: 0.8rem; color: #666; margin-top: 0.5rem;">
            Confiança: {entry.get('confidence', 'N/A')}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    # Ação recomendada
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem;">
        <div style="font-size: 0.9rem; color: #666;">Ação Recomendada</div>
        <div style="font-size: 0.95rem; font-weight: 500; margin-top: 0.5rem; line-height: 1.4;">
            {signal.get('action', 'N/A')}
        </div>
        <div style="margin-top: 1rem;">
            <div style="font-size: 0.85rem; color: #666;">Ativos com dados</div>
            <div style="font-size: 1.5rem; font-weight: 700;">
                {score_result.get('assets_available', 0)}/{score_result.get('assets_total', 0)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ---- Última atualização ----
last_refresh = st.session_state.get("last_refresh", datetime.now())
st.markdown(f'<div class="refresh-info">Última atualização: {last_refresh.strftime("%H:%M:%S")} | Refresh #{st.session_state.refresh_count}</div>', unsafe_allow_html=True)

st.divider()

# ---- BREAKDOWN POR CATEGORIA ----
st.markdown("### 📊 Breakdown por Categoria")

category_scores = score_result.get("category_scores", {})
cat_cols = st.columns(len(category_scores))

for i, (cat_name, cat_data) in enumerate(category_scores.items()):
    with cat_cols[i % len(cat_cols)]:
        cat_score = cat_data.get("normalized", 0)
        cat_color = get_score_color(cat_score)
        
        # Encontra ícone da categoria
        cat_icon = "📊"
        for cname, cinfo in CATEGORIES.items():
            if cname == cat_name:
                cat_icon = cinfo.get("icon", "📊")
                break
        
        st.markdown(f"""
        <div style="text-align: center; padding: 0.8rem; border-radius: 10px; 
                    background-color: {cat_color}11; border: 1px solid {cat_color}44;">
            <div style="font-size: 1.5rem;">{cat_icon}</div>
            <div style="font-size: 0.85rem; font-weight: 600; color: #333;">{cat_name}</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: {cat_color};">
                {cat_score:+.0f}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ---- DETALHES POR ATIVO ----
st.markdown("### 📋 Detalhes por Ativo")

asset_signals = score_result.get("asset_signals", {})

# Organiza por categoria
for cat_name, cat_info in CATEGORIES.items():
    cat_assets = cat_info.get("assets", [])
    cat_icon = cat_info.get("icon", "📊")
    cat_color = cat_info.get("color", "#666")
    
    # Filtra ativos desta categoria que temos dados
    available = [a for a in cat_assets if a in asset_signals]
    if not available:
        continue
    
    st.markdown(f"""
    <div class="category-header">
        {cat_icon} {cat_name}
    </div>
    """, unsafe_allow_html=True)
    
    cols = st.columns(min(len(available), 5))
    
    for j, asset_name in enumerate(available):
        data = asset_signals[asset_name]
        with cols[j % len(cols)]:
            change = data.get("change_pct")
            price = data.get("current_price")
            contribution = data.get("contribution", 0)
            direction = data.get("direction", 1)
            source = data.get("source", "unknown")
            
            if change is not None:
                change_str = format_change(change)
                change_color = get_change_color(change)
            else:
                change_str = "N/A"
                change_color = "#666"
            
            # Cor da borda baseada na contribuição
            if contribution > 0:
                border_color = "#00C853"
            elif contribution < 0:
                border_color = "#D50000"
            else:
                border_color = "#FFC107"
            
            source_icon = "🖥️" if "mt5" in source else "🌐"
            
            st.markdown(f"""
            <div class="asset-card" style="border-left-color: {border_color}; background-color: {border_color}08;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #333;">
                    {asset_name} <span style="font-size: 0.65rem;">{source_icon}</span>
                </div>
                <div style="font-size: 0.75rem; color: #666;">
                    {format_price(price) if price else 'N/A'}
                </div>
                <div style="font-size: 0.9rem; font-weight: 600; color: {change_color};">
                    {change_str}
                </div>
                <div style="font-size: 0.7rem; color: #888;">
                    Contrib: {contribution:+.3f} | Dir: {'↑' if direction > 0 else '↓'}
                </div>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# ---- GRÁFICO DE HISTÓRICO DO SCORE ----
st.markdown("### 📈 Histórico do Score")

history = st.session_state.score_history
if len(history) >= 2:
    timestamps = [h["timestamp"] for h in history]
    scores = [h["score"] for h in history]
    
    fig = go.Figure()
    
    # Área do score
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=scores,
        mode='lines+markers',
        name='Score Macro',
        line=dict(color='#2196F3', width=2),
        marker=dict(size=4),
        fill='tozeroy',
        fillcolor='rgba(33, 150, 243, 0.1)',
    ))
    
    # Linhas de referência
    fig.add_hline(y=60, line_dash="dash", line_color="#00C853", annotation_text="Forte Alta (+60)")
    fig.add_hline(y=30, line_dash="dot", line_color="#4CAF50", annotation_text="Moderada Alta (+30)")
    fig.add_hline(y=0, line_dash="solid", line_color="#666", annotation_text="Neutro")
    fig.add_hline(y=-30, line_dash="dot", line_color="#FF5722", annotation_text="Moderada Baixa (-30)")
    fig.add_hline(y=-60, line_dash="dash", line_color="#D50000", annotation_text="Forte Baixa (-60)")
    
    # Zonas coloridas
    fig.add_hrect(y0=60, y1=100, fillcolor="rgba(0, 200, 83, 0.05)")
    fig.add_hrect(y0=-100, y1=-60, fillcolor="rgba(213, 0, 0, 0.05)")
    
    fig.update_layout(
        height=350,
        yaxis=dict(range=[-100, 100], title="Score"),
        xaxis=dict(title="Hora"),
        showlegend=False,
        margin=dict(l=20, r=20, t=30, b=30),
        template="plotly_white",
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aguardando mais leituras para exibir o gráfico de histórico...")

# ---- TABELA DE DADOS COMPLETA ----
st.divider()
st.markdown("### 📊 Tabela de Dados")

table_data = []
for name, data in asset_signals.items():
    table_data.append({
        "Ativo": name,
        "Preço": format_price(data.get("current_price")),
        "Variação": format_change(data.get("change_pct")),
        "Direção": "↑ Direta" if data.get("direction", 1) > 0 else "↓ Inversa",
        "Correlação": f"{data.get('correlation', 0):.2f}",
        "Peso": f"{data.get('weight', 0):.2f}",
        "Contribuição": f"{data.get('contribution', 0):+.4f}",
        "Fonte": "MT5" if "mt5" in data.get("source", "") else "YF",
    })

if table_data:
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

# ---- TOP CONTRIBUTORS ----
st.divider()
st.markdown("### 🏆 Maiores Contribuidores")

scorer = st.session_state.scorer
contributors = scorer.get_top_contributors(score_result, top_n=5)

col_pos, col_neg = st.columns(2)

with col_pos:
    st.markdown("#### 🟢 Contribuição Positiva")
    for name, data in contributors.get("top_positives", []):
        change_str = format_change(data.get("change_pct"))
        st.markdown(f"""
        - **{name}**: {change_str} → Contribuição: {data.get('contribution', 0):+.4f}
        """)

with col_neg:
    st.markdown("#### 🔴 Contribuição Negativa")
    for name, data in contributors.get("top_negatives", []):
        change_str = format_change(data.get("change_pct"))
        st.markdown(f"""
        - **{name}**: {change_str} → Contribuição: {data.get('contribution', 0):+.4f}
        """)

# ---- ATIVOS SEM DADOS ----
missing = score_result.get("missing_assets", [])
if missing:
    st.divider()
    st.markdown("### ⚠️ Ativos Sem Dados")
    st.warning(f"Os seguintes ativos não retornaram dados: {', '.join(missing)}")

# ---- AUTO REFRESH ----
if st.session_state.auto_refresh:
    # Countdown e refresh automático
    refresh_seconds = interval if 'interval' in dir() else 30
    time.sleep(0.1)  # Pequena pausa para a UI renderizar
    st.rerun() if st.session_state.get("_auto_refresh_enabled", True) else None
    
    # Usa st.empty para mostrar countdown
    # Nota: Streamlit rerun é necessário para atualizar dados
    # A cada N segundos, o dashboard recarrega automaticamente
    st.markdown(f"""
    <script>
        setTimeout(function() {{
            window.location.reload();
        }}, {refresh_seconds * 1000});
    </script>
    <div class="refresh-info">Próxima atualização automática em ~{refresh_seconds}s</div>
    """, unsafe_allow_html=True)
