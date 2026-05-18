@echo off
chcp 65001 >nul
title Macro Scoring WIN v12.0 - Instalador
color 0A

echo.
echo ============================================================
echo    SISTEMA DE MACRO SCORING v12.0 - MINI INDICE (WIN)
echo    MT5 Rico (primario) + Yahoo Finance (fallback)
echo ============================================================
echo.

:: ============================================================
:: ETAPA 1: VERIFICAR PYTHON
:: ============================================================
echo [1/6] Verificando Python...
echo.

python --version 2>nul
if %errorlevel% neq 0 (
    echo [!] Python NAO encontrado.
    echo.
    echo Verificando instalacoes comuns...
    
    py --version 2>nul
    if %errorlevel% equ 0 (
        echo [OK] Python encontrado via 'py' launcher!
        goto :python_found
    )
    
    for %%V in (313 312 311 310) do (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
            set "PATH=%LOCALAPPDATA%\Programs\Python\Python%%V;%LOCALAPPDATA%\Programs\Python\Python%%V\Scripts;%PATH%"
            echo [OK] Python encontrado em Python%%V
            goto :python_found
        )
    )
    
    echo [!] Python NAO encontrado.
    echo     Baixe em: https://www.python.org/downloads/
    echo     IMPORTANTE: Marque "Add Python to PATH" na instalacao!
    echo.
    pause
    exit /b 1
)

:python_found
echo.
python --version
echo [OK] Python encontrado!
echo.

:: ============================================================
:: ETAPA 2: VERIFICAR PIP
:: ============================================================
echo [2/6] Verificando pip...
pip --version 2>nul
if %errorlevel% neq 0 (
    echo [!] pip nao encontrado. Instalando...
    python -m ensurepip --upgrade 2>nul
)
pip --version
echo [OK] pip encontrado!
echo.

:: ============================================================
:: ETAPA 3: CRIAR AMBIENTE VIRTUAL
:: ============================================================
echo [3/6] Configurando ambiente virtual...
echo.

if not exist "venv\" (
    echo Criando ambiente virtual...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual!
        pause
        exit /b 1
    )
    echo [OK] Ambiente virtual criado!
) else (
    echo [OK] Ambiente virtual ja existe.
)

echo Ativando ambiente virtual...
call venv\Scripts\activate.bat
echo [OK] Ambiente virtual ativado!
echo.

:: ============================================================
:: ETAPA 4: INSTALAR DEPENDENCIAS
:: ============================================================
echo [4/6] Instalando dependencias...
echo.

echo Atualizando pip...
pip install --upgrade pip 2>nul

echo Instalando pacotes...
pip install yfinance streamlit plotly pandas numpy requests 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias!
    pause
    exit /b 1
)

echo Tentando instalar MetaTrader5 (opcional)...
pip install MetaTrader5 2>nul
if %errorlevel% neq 0 (
    echo [AVISO] MetaTrader5 nao instalado - usando Yahoo Finance.
    echo         Para usar MT5 Rico: pip install MetaTrader5
) else (
    echo [OK] MetaTrader5 instalado!
)

echo.
echo [OK] Todas as dependencias instaladas!
echo.

:: ============================================================
:: ETAPA 5: VERIFICACAO FINAL
:: ============================================================
echo [5/6] Verificacao final...
echo.

python -c "import yfinance; print('  yfinance: OK')" 2>nul
python -c "import streamlit; print('  streamlit: OK')" 2>nul
python -c "import plotly; print('  plotly: OK')" 2>nul
python -c "import pandas; print('  pandas: OK')" 2>nul
python -c "import MetaTrader5; print('  MetaTrader5: OK')" 2>nul || echo "  MetaTrader5: NAO DISPONIVEL"

echo.

:: ============================================================
:: ETAPA 6: MENU
:: ============================================================
echo [6/6] Tudo pronto!
echo.
echo ============================================================
echo    INSTALACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo.
echo    Como deseja rodar o sistema?
echo.
echo    [1] Dashboard Web (RECOMENDADO)
echo        Abre no navegador em http://localhost:8501
echo.
echo    [2] Terminal
echo.
echo    [3] Sair
echo.
set /p choice="    Digite 1, 2 ou 3: "

if "%choice%"=="1" goto dashboard
if "%choice%"=="2" goto terminal
goto fim

:dashboard
echo.
echo ============================================================
echo    Iniciando Dashboard Web...
echo    Navegador: http://localhost:8501
echo    Para PARAR: Ctrl+C ou feche esta janela
echo ============================================================
echo.
streamlit run dashboard/app.py --server.headless true --server.runOnSave true
echo.
pause
goto fim

:terminal
echo.
python main.py
echo.
pause

:fim
