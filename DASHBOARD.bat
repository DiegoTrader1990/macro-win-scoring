@echo off
chcp 65001 >nul
title Macro WIN v12.0 - Dashboard
color 0A

echo.
echo ============================================================
echo    Macro Scoring WIN v12.0 - Dashboard
echo    MT5 Rico (primario) + Yahoo Finance (fallback)
echo ============================================================
echo.

:: Verifica se venv existe
if not exist "venv\" (
    echo [!] Sistema nao instalado! Rode o INICIAR.bat primeiro.
    echo.
    pause
    exit /b 1
)

:: Ativa venv
call venv\Scripts\activate.bat

:: Verifica streamlit
python -c "import streamlit" 2>nul
if %errorlevel% neq 0 (
    echo [!] Streamlit nao encontrado. Instalando...
    pip install streamlit yfinance pandas plotly requests numpy
)

:: Verifica MetaTrader5 (opcional)
python -c "import MetaTrader5" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] MetaTrader5 nao disponivel - usando Yahoo Finance
    echo        Para MT5 Rico: pip install MetaTrader5
    echo.
) else (
    echo [OK] MetaTrader5 disponivel - tentando conectar ao Rico
    echo.
)

echo Iniciando Dashboard...
echo.
echo   URL: http://localhost:8501
echo   Para PARAR: Ctrl+C ou feche esta janela
echo.
echo   DICA: Redimensione para 600px de largura e posicione
echo         ao lado da sua plataforma de operacao
echo.

streamlit run dashboard/app.py --server.headless true --browser.gatherUsageStats false --server.runOnSave true

echo.
echo Dashboard encerrado.
pause
