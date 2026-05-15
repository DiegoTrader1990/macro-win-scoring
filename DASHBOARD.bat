@echo off
chcp 65001 >nul
title Macro WIN - Painel 600x1000
color 0A

echo.
echo ============================================================
echo    Macro Scoring WIN - Painel Compacto (600x1000)
echo ============================================================
echo.

if not exist "venv\" (
    echo [!] Sistema nao instalado! Rode o INICIAR.bat primeiro.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

python -c "import streamlit" 2>nul
if %errorlevel% neq 0 (
    echo [!] Streamlit nao encontrado. Reinstalando...
    pip install streamlit
)

echo.
echo Iniciando Painel Compacto (600x1000)...
echo Navegador: http://localhost:8501
echo Para PARAR: Ctrl+C ou feche esta janela
echo.
echo DICA: Redimensione a janela do navegador para 600px de largura
echo        e posicione ao lado da sua plataforma de operacao.
echo.

streamlit run dashboard/app.py --server.headless true --browser.gatherUsageStats false
echo.
pause
