# 📊 Sistema de Macro Scoring - Mini Índice (WIN)

Sistema de monitoramento macro em tempo real para day trade do Mini Índice (WIN) na B3.

## 🎯 O que o sistema faz

- Monitora **20+ ativos macro** em tempo real (índices globais, moedas, commodities, juros, ADRs, ETFs setoriais)
- Calcula um **Score Macro** de -100 a +100 baseado nas correlações validadas com dados reais
- Identifica **sinais de entrada** usando Score + Delta (variação do score)
- Fonte de dados: **MT5 (Rico)** como primário, **Yahoo Finance** como fallback automático

## 📋 Pré-requisitos

1. **Python 3.9+** instalado
2. **MetaTrader 5** instalado (opcional, mas recomendado para dados em tempo real)
3. Conta na **Rico** (se quiser usar MT5)

## 🚀 Instalação

### Passo 1: Baixar o projeto
Baixe e extraia o arquivo ZIP em uma pasta de sua preferência.

### Passo 2: Criar ambiente virtual (recomendado)
```bash
cd macro_win_system
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate
```

### Passo 3: Instalar dependências
```bash
pip install -r requirements.txt
```

### Passo 4 (Opcional): Instalar MetaTrader5 para Python
Se estiver no Windows e quiser usar dados do MT5:
```bash
pip install MetaTrader5
```

### Passo 5 (Opcional): Configurar MT5
Copie o arquivo `.env.example` para `.env` e preencha com seu login da Rico:
```bash
copy .env.example .env
# Edite o .env com seu login e senha
```

## 🖥️ Como Rodar

### Opção 1: Dashboard Web (Recomendado)
```bash
streamlit run dashboard/app.py
```
O dashboard abre automaticamente no navegador em `http://localhost:8501`

### Opção 2: Terminal
```bash
python main.py
```
Roda o sistema no terminal com atualização automática a cada 30 segundos.

## 📊 Ativos Monitorados

### Yahoo Finance (Macro Internacional)
| Ativo | Ticker | Correlação | Direção |
|-------|--------|-----------|---------|
| EWZ (iShares Brazil) | EWZ | +0.96 | Direta |
| VALE ADR | VALE | +0.75 | Direta |
| VIX | ^VIX | -0.63 | Inversa |
| DXY (Dólar Index) | DX-Y.NYB | -0.57 | Inversa |
| ES Futures (S&P 500) | ES=F | +0.57 | Direta |
| Euro Stoxx 50 | ^STOXX50E | +0.53 | Direta |
| IMAB11 | IMAB11.SA | +0.56 | Direta |
| DAX | ^GDAXI | +0.49 | Direta |
| US 10Y Yield | ^TNX | -0.48 | Inversa |
| WTI Crude | CL=F | -0.50 | Inversa |
| S&P 500 | ^GSPC | +0.45 | Direta |
| Cobre | HG=F | +0.44 | Direta |
| Bitcoin | BTC-USD | +0.41 | Direta |
| Nikkei 225 | ^N225 | +0.35 | Direta |
| Brent | BZ=F | -0.30 | Inversa |

### MT5 + Yahoo Finance (Dual Source)
| Ativo | MT5 | Yahoo Finance |
|-------|-----|---------------|
| VALE3 | VALE3 | VALE3.SA |
| PETR4 | PETR4 | PETR4.SA |
| IFNC | IFNC | IFNC.SA |
| IMAT | IMAT | IMAT.SA |
| ICON | ICON | ICON.SA |
| IMAB11 | IMAB11 | IMAB11.SA |
| BOVA11 | BOVA11 | BOVA11.SA |

## 🔢 Como Funciona o Scoring

### Score Macro (-100 a +100)
Cada ativo contribui proporcionalmente ao seu **peso** (baseado na correlação validada) e à sua **variação intraday**:

1. Variação do ativo → sinal normalizado (-1 a +1)
2. Sinal × direção da correlação (+1 direta, -1 inversa)
3. Sinal × peso do ativo → contribuição
4. Soma de todas as contribuições → Score normalizado

### Interpretação do Score
| Score | Sinal | Ação |
|-------|-------|------|
| +60 a +100 | 🟢🟢🟢 FORTE ALTA | Busca COMPRAS |
| +30 a +60 | 🟢🟢 MODERADA ALTA | Prefira COMPRAS |
| -30 a +30 | 🟡 NEUTRO | Zona de cautela |
| -60 a -30 | 🔴🔴 MODERADA BAIXA | Prefira VENDAS |
| -100 a -60 | 🔴🔴🔴 FORTE BAIXA | Busca VENDAS |

### Delta (Timing de Entrada)
- **Delta > 0**: Score melhorando → momentum de alta
- **Delta < 0**: Score piorando → momentum de baixa
- **Confluence**: Score e Delta na mesma direção = sinal mais forte
- **Reversal**: Delta muda de sinal = possível ponto de reversão

## ⚙️ Configuração

Edite o arquivo `config.py` para:
- Ajustar o contrato do WIN/WDO (vencimento)
- Modificar pesos dos ativos
- Alterar thresholds de sinais
- Configurar horários de trading

## ⚠️ Avisos Importantes

1. **MT5 no Windows**: O MetaTrader5 para Python só funciona no Windows com o MT5 instalado
2. **Yahoo Finance**: Pode ter atraso de 15 minutos em alguns ativos
3. **Este não é um sistema de recomendação**: Use como ferramenta de análise, não como sinal automático
4. **Sempre use stops**: O score macro indica viés, não garante direção
5. **Backtesting**: Sempre valide os sinais com backtesting antes de operar com capital real

## 📁 Estrutura do Projeto

```
macro_win_system/
├── main.py                 # Entry point terminal
├── config.py               # Configuração (ativos, pesos, thresholds)
├── requirements.txt        # Dependências Python
├── .env.example           # Template de variáveis de ambiente
├── data_sources/
│   ├── mt5_source.py      # Fonte MT5 (Rico)
│   ├── yahoo_source.py    # Fonte Yahoo Finance
│   └── data_manager.py    # Coordena MT5 → YF fallback
├── scoring/
│   ├── macro_score.py     # Motor de scoring macro
│   └── delta.py           # Análise de delta e timing
├── dashboard/
│   └── app.py             # Dashboard Streamlit
└── utils/
    └── helpers.py          # Funções auxiliares
```

## 📞 Suporte

Para dúvidas sobre o sistema, consulte o estudo completo em PDF:
- `estudo_completo_macro_win.pdf` - Estudo completo com validação de correlações
