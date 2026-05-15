@echo off
chcp 65001 >nul
title Macro Scoring WIN - Terminal
color 0A

echo.
echo ============================================================
echo    Macro Scoring WIN - Modo Terminal
echo ============================================================
echo.

:: Verifica se instalou
if not exist "venv\" (
    echo [!] Sistema nao instalado! Rode o INICIAR.bat primeiro.
    echo.
    pause
    exit /b 1
)

:: Ativa venv
call venv\Scripts\activate.bat

echo.
echo Iniciando modo terminal...
echo Para PARAR: Ctrl+C
echo.
python main.py
echo.
pause
