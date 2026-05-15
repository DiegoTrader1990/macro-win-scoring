@echo off
chcp 65001 >nul
title Macro WIN - Analisar Logs
color 0B

echo.
echo ============================================================
echo    Macro Scoring WIN - Analise de Logs
echo ============================================================
echo.

if not exist "venv\" (
    echo [!] Sistema nao instalado! Rode o INICIAR.bat primeiro.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

python -c "import pandas" 2>nul
if %errorlevel% neq 0 (
    echo [!] Pandas nao encontrado. Instalando...
    pip install pandas numpy
)

echo Analisando logs...
echo.

if not exist "logs\" (
    echo [!] Nenhum log encontrado!
    echo     Rode o sistema primeiro para gerar logs.
    echo.
    pause
    exit /b 1
)

python analyze_logs.py %1

echo.
pause
