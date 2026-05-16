import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
Aba de Análise de Logs - Dashboard Profissional
==================================================
Carrega e visualiza os dados de log para otimização do sistema.
Gráficos interativos com Plotly para análise de score, ativos e sinais.
"""

import os
import json
import glob
from datetime import date, datetime

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def load_log_data(log_dir: str = "logs", target_date: str = None) -> dict:
    """Carrega arquivos de log para uma data específica."""
    if target_date is None:
        target_date = date.today().strftime("%Y%m%d")

    result = {}
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_dir = os.path.join(base, log_dir)

    # Score log
    files = glob.glob(os.path.join(full_dir, f"{target_date}_score_log.csv"))
    if files:
        try:
            result["score"] = pd.read_csv(files[0])
        except:
            pass

    # Asset log
    files = glob.glob(os.path.join(full_dir, f"{target_date}_asset_log.csv"))
    if files:
        try:
            result["asset"] = pd.read_csv(files[0])
        except:
            pass

    # Signal log
    files = glob.glob(os.path.join(full_dir, f"{target_date}_signal_log.csv"))
    if files:
        try:
            result["signal"] = pd.read_csv(files[0])
        except:
            pass

    # Available dates
    try:
        all_files = glob.glob(os.path.join(full_dir, "*_score_log.csv"))
        dates = sorted(set(
            os.path.basename(f).split("_")[0]
            for f in all_files
            if len(os.path.basename(f).split("_")) > 1
        ), reverse=True)
        result["available_dates"] = dates
    except:
        result["available_dates"] = []

    return result


def render_score_distribution_chart(score_df: pd.DataFrame) -> go.Figure:
    """Gráfico de distribuição do score."""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Distribuição do Score", "Score ao Longo do Dia",
                        "Delta ao Longo do Dia", "Zonas do Score"),
        vertical_spacing=0.15,
        horizontal_spacing=0.12,
    )

    # Histogram
    fig.add_trace(go.Histogram(
        x=score_df["score"],
        nbinsx=30,
        marker_color="#2196F3",
        marker_line_color="#1565C0",
        marker_line_width=0.5,
        name="Score",
    ), row=1, col=1)

    # Score timeline
    fig.add_trace(go.Scatter(
        x=score_df.get("time", range(len(score_df))),
        y=score_df["score"],
        mode="lines",
        line=dict(color="#2196F3", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(33,150,243,0.1)",
        name="Score",
    ), row=1, col=2)
    fig.add_hline(y=60, line_dash="dash", line_color="#00E67640", row=1, col=2)
    fig.add_hline(y=-60, line_dash="dash", line_color="#FF174440", row=1, col=2)
    fig.add_hline(y=0, line_color="#ffffff20", row=1, col=2)

    # Delta timeline
    if "delta" in score_df.columns:
        colors = ["#00E676" if d >= 0 else "#FF1744" for d in score_df["delta"].fillna(0)]
        fig.add_trace(go.Bar(
            x=score_df.get("time", range(len(score_df))),
            y=score_df["delta"],
            marker_color=colors,
            name="Delta",
        ), row=2, col=1)

    # Zona pie
    zones = {
        "Forte Alta": len(score_df[score_df["score"] >= 60]),
        "Mod. Alta": len(score_df[(score_df["score"] >= 30) & (score_df["score"] < 60)]),
        "Neutro": len(score_df[(score_df["score"] > -30) & (score_df["score"] < 30)]),
        "Mod. Baixa": len(score_df[(score_df["score"] <= -30) & (score_df["score"] > -60)]),
        "Forte Baixa": len(score_df[score_df["score"] <= -60]),
    }
    zone_colors = ["#00E676", "#66BB6A", "#FFD600", "#FF7043", "#FF1744"]
    fig.add_trace(go.Pie(
        labels=list(zones.keys()),
        values=list(zones.values()),
        marker_colors=zone_colors,
        textinfo="label+percent",
        hole=0.4,
    ), row=2, col=2)

    fig.update_layout(
        height=500, margin=dict(l=30, r=15, t=35, b=20),
        template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        showlegend=False,
        font=dict(size=10, color="#b0b0b0"),
    )
    return fig


def render_asset_contribution_chart(asset_df: pd.DataFrame) -> go.Figure:
    """Gráfico de contribuição dos ativos."""
    if asset_df is None or asset_df.empty:
        return None

    contrib = asset_df.groupby("asset").agg(
        contrib_mean=("contribution", "mean"),
        contrib_abs=("contribution", lambda x: x.abs().mean()),
    ).sort_values("contrib_abs", ascending=True).tail(15)

    colors = ["#00E676" if v >= 0 else "#FF1744" for v in contrib["contrib_mean"]]

    fig = go.Figure(go.Bar(
        x=contrib["contrib_mean"],
        y=contrib.index,
        orientation="h",
        marker_color=colors,
        marker_line_width=0,
    ))

    fig.update_layout(
        height=350, margin=dict(l=80, r=15, t=30, b=20),
        template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        title=dict(text="Contribuição Média por Ativo", font=dict(size=12, color="#b0b0b0")),
        xaxis=dict(title="Contribuição", gridcolor="#1a1a2e", tickfont=dict(size=9)),
        yaxis=dict(tickfont=dict(size=9)),
        showlegend=False,
    )
    return fig


def render_signal_analysis_chart(signal_df: pd.DataFrame, score_df: pd.DataFrame = None) -> go.Figure:
    """Gráfico de análise de sinais."""
    if signal_df is None or signal_df.empty:
        return None

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Sinais por Tipo", "Score nos Momentos de Sinal"),
    )

    # Signal counts
    counts = signal_df["signal_type"].value_counts()
    sig_colors = []
    for stype in counts.index:
        if "COMPRA" in stype:
            sig_colors.append("#00E676")
        elif "VENDA" in stype:
            sig_colors.append("#FF1744")
        elif "REVERSAO" in stype:
            sig_colors.append("#FFD600")
        else:
            sig_colors.append("#78909C")

    fig.add_trace(go.Bar(
        x=counts.index,
        y=counts.values,
        marker_color=sig_colors,
        name="Quantidade",
    ), row=1, col=1)

    # Score distribution at signal times
    fig.add_trace(go.Box(
        y=signal_df["score"],
        x=signal_df["signal_type"],
        marker_color="#2196F3",
        name="Score",
    ), row=1, col=2)

    fig.update_layout(
        height=300, margin=dict(l=30, r=15, t=35, b=60),
        template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        showlegend=False,
        font=dict(size=9, color="#b0b0b0"),
        xaxis=dict(tickangle=-35, tickfont=dict(size=8)),
        xaxis2=dict(tickangle=-35, tickfont=dict(size=8)),
    )
    return fig


def render_hourly_heatmap(score_df: pd.DataFrame) -> go.Figure:
    """Heatmap de score por hora."""
    if score_df is None or score_df.empty or "time" not in score_df.columns:
        return None

    try:
        hours = pd.to_datetime(score_df["time"], format="%H:%M:%S").dt.hour
        score_by_hour = score_df.groupby(hours)["score"].agg(["mean", "std", "count"])

        fig = go.Figure(go.Bar(
            x=[f"{h:02d}h" for h in score_by_hour.index],
            y=score_by_hour["mean"],
            error_y=dict(type="data", array=score_by_hour["std"].fillna(0)),
            marker_color=[
                "#00E676" if v >= 30 else "#FF1744" if v <= -30 else "#FFD600"
                for v in score_by_hour["mean"]
            ],
        ))

        fig.update_layout(
            height=250, margin=dict(l=30, r=15, t=30, b=30),
            template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            title=dict(text="Score Médio por Hora", font=dict(size=12, color="#b0b0b0")),
            yaxis=dict(title="Score", gridcolor="#1a1a2e"),
            xaxis=dict(title="Hora", gridcolor="#1a1a2e"),
            showlegend=False,
        )
        return fig
    except:
        return None


def generate_suggestions(score_df, asset_df, signal_df) -> list:
    """Gera sugestões de otimização baseadas nos logs."""
    suggestions = []

    if score_df is None or score_df.empty:
        return ["Nenhum dado de score disponível para análise."]

    # Neutro demais
    pct_neutro = len(score_df[(score_df["score"] > -30) & (score_df["score"] < 30)]) / len(score_df) * 100
    if pct_neutro > 70:
        suggestions.append(
            f"[ALTO] {pct_neutro:.0f}% das leituras na zona NEUTRA. "
            "Reduza thresholds (moderate_bullish: 30→20) ou aumente pesos dos ativos mais impactantes."
        )

    # Score volátil
    std = score_df["score"].std()
    if std > 40:
        suggestions.append(
            f"[MÉDIO] Score volátil (std={std:.0f}). Implemente média móvel de 3 períodos "
            "antes de gerar sinal de entrada."
        )

    # Delta reversões
    if "delta" in score_df.columns:
        deltas = score_df["delta"].dropna().values
        crossings = sum(1 for i in range(1, len(deltas)) if deltas[i-1] * deltas[i] < 0)
        if crossings > 10:
            suggestions.append(
                f"[MÉDIO] Delta cruzou zero {crossings}x. Aumente threshold de delta (5→10) "
                "para reduzir falsas reversões."
            )

    # Confluência baixa
    if "confluence_aligned" in score_df.columns:
        pct_conf = score_df["confluence_aligned"].sum() / len(score_df) * 100
        if pct_conf < 10:
            suggestions.append(
                f"[MÉDIO] Apenas {pct_conf:.0f}% de confluência Score+Delta. "
                "Ajuste delta_bullish/bearish para capturar mais alinhamentos."
            )

    # Ativos com baixa contribuição
    if asset_df is not None and not asset_df.empty:
        contrib = asset_df.groupby("asset")["contribution"].apply(lambda x: x.abs().mean())
        low = contrib[contrib < 0.001]
        if len(low) > 3:
            suggestions.append(
                f"[BAIXO] Ativos com contribuição nula: {', '.join(low.index[:5])}. "
                "Considere remover para simplificar o sistema."
            )

    # Sinais muito frequentes
    if signal_df is not None and not signal_df.empty:
        counts = signal_df["signal_type"].value_counts()
        for sig, count in counts.items():
            if count > 20:
                suggestions.append(
                    f"[BAIXO] '{sig}' gerado {count}x. Muito frequente. "
                    "Ajuste thresholds para ser mais seletivo."
                )

    if not suggestions:
        suggestions.append("Sistema parece bem calibrado. Nenhuma otimização urgente identificada.")

    return suggestions


def render_analysis_tab():
    """Renderiza a aba de análise completa."""
    st.markdown('<div class="section-header">ANALISE DE LOGS</div>', unsafe_allow_html=True)

    # Seletor de data
    logs = load_log_data()
    available_dates = logs.get("available_dates", [])

    col1, col2 = st.columns([2, 1])
    with col1:
        if available_dates:
            selected_date = st.selectbox(
                "Data", available_dates,
                format_func=lambda x: f"{x[:4]}-{x[4:6]}-{x[6:8]}",
                label_visibility="collapsed",
            )
        else:
            selected_date = date.today().strftime("%Y%m%d")
            st.info("Nenhum log encontrado. Rode o sistema primeiro.")

    with col2:
        if st.button("Carregar", use_container_width=True):
            logs = load_log_data(target_date=selected_date)

    # Carrega dados da data selecionada
    if selected_date != date.today().strftime("%Y%m%d") or "score" not in logs:
        logs = load_log_data(target_date=selected_date)

    score_df = logs.get("score")
    asset_df = logs.get("asset")
    signal_df = logs.get("signal")

    if score_df is None or score_df.empty:
        st.markdown("""
        <div style="text-align:center; padding:3rem; color:#555;">
            <div style="font-size:1.5rem; margin-bottom:0.5rem;">SEM DADOS</div>
            <div style="font-size:0.8rem;">Rode o sistema para gerar logs.<br>
            Os logs sao salvos automaticamente na pasta logs/</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Estatísticas rápidas
    total_reads = len(score_df)
    score_mean = score_df["score"].mean()
    score_std = score_df["score"].std()
    delta_mean = score_df["delta"].mean() if "delta" in score_df.columns else 0

    cols = st.columns(4)
    stats = [
        ("Leituras", f"{total_reads}", "#2196F3"),
        ("Score Medio", f"{score_mean:+.1f}", "#00E676" if score_mean > 0 else "#FF1744"),
        ("Volatilidade", f"{score_std:.1f}", "#FFD600"),
        ("Delta Medio", f"{delta_mean:+.1f}", "#00E676" if delta_mean > 0 else "#FF1744"),
    ]
    for col, (label, value, color) in zip(cols, stats):
        col.markdown(f"""
        <div class="stat-card">
            <div class="stat-value" style="color:{color}">{value}</div>
            <div class="stat-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="thin-divider"></div>', unsafe_allow_html=True)

    # Gráficos
    fig_score = render_score_distribution_chart(score_df)
    if fig_score:
        st.plotly_chart(fig_score, use_container_width=True)

    fig_asset = render_asset_contribution_chart(asset_df)
    if fig_asset:
        st.plotly_chart(fig_asset, use_container_width=True)

    fig_signal = render_signal_analysis_chart(signal_df, score_df)
    if fig_signal:
        st.plotly_chart(fig_signal, use_container_width=True)

    fig_hourly = render_hourly_heatmap(score_df)
    if fig_hourly:
        st.plotly_chart(fig_hourly, use_container_width=True)

    st.markdown('<div class="thin-divider"></div>', unsafe_allow_html=True)

    # Sugestões
    st.markdown('<div class="section-header" style="margin-top:0.3rem;">SUGESTOES DE OTIMIZACAO</div>', unsafe_allow_html=True)
    suggestions = generate_suggestions(score_df, asset_df, signal_df)
    for i, s in enumerate(suggestions, 1):
        severity = "high" if "[ALTO]" in s else "medium" if "[MÉDIO]" in s else "low"
        sev_color = {"high": "#FF1744", "medium": "#FFD600", "low": "#78909C"}[severity]
        st.markdown(f"""
        <div class="suggestion-item">
            <span style="color:{sev_color};font-weight:700;font-size:0.7rem;">{i}</span>
            <span style="font-size:0.72rem;color:#ccc;">{s.replace(f'[{severity.upper()}] ', '')}</span>
        </div>
        """, unsafe_allow_html=True)
