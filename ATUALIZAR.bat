@echo off
chcp 65001 >nul
title Macro Scoring WIN - Atualizar
color 0B

echo.
echo ============================================================
echo    Macro Scoring WIN - Atualizar Dependencias
echo ============================================================
echo.

if not exist "venv\" (
    echo [!] Sistema nao instalado! Rode o INICIAR.bat primeiro.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Atualizando pip...
pip install --upgrade pip

echo.
echo Reinstalando dependencias...
pip install --force-reinstall yfinance streamlit plotly pandas requests

echo.
echo Tentando MetaTrader5...
pip install MetaTrader5 2>nul

echo.
echo [OK] Dependencias atualizadas!
echo.
pause
