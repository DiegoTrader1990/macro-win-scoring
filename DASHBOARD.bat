@echo off
chcp 65001 >nul
title Macro Scoring WIN - Dashboard Web
color 0A

echo.
echo ============================================================
echo    Macro Scoring WIN - Dashboard Web
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

:: Verifica streamlit
python -c "import streamlit" 2>nul
if %errorlevel% neq 0 (
    echo [!] Streamlit nao encontrado. Reinstalando...
    pip install streamlit
)

echo.
echo Iniciando Dashboard Web...
echo Navegador: http://localhost:8501
echo Para PARAR: Ctrl+C ou feche esta janela
echo.
streamlit run dashboard/app.py --server.headless true
echo.
pause
