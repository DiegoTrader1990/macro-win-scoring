@echo off
chcp 65001 >nul
title Macro Scoring WIN - Instalador Completo
color 0A

echo.
echo ============================================================
echo    SISTEMA DE MACRO SCORING - MINI INDICE (WIN)
echo    Instalador Automatico Completo
echo ============================================================
echo.

:: ============================================================
:: ETAPA 1: VERIFICAR PYTHON
:: ============================================================
echo [1/6] Verificando Python...
echo.

python --version 2>nul
if %errorlevel% neq 0 (
    echo [!] Python NAO encontrado no sistema.
    echo.
    echo Verificando instalacoes comuns do Python...
    
    :: Tenta py launcher (vem com instalador do Python)
    py --version 2>nul
    if %errorlevel% equ 0 (
        echo [OK] Python encontrado via 'py' launcher!
        echo.
        goto :python_found
    )
    
    :: Tenta caminhos comuns
    if exist "C:\Python312\python.exe" (
        set "PATH=C:\Python312;C:\Python312\Scripts;%PATH%"
        echo [OK] Python encontrado em C:\Python312
        goto :python_found
    )
    if exist "C:\Python311\python.exe" (
        set "PATH=C:\Python311;C:\Python311\Scripts;%PATH%"
        echo [OK] Python encontrado em C:\Python311
        goto :python_found
    )
    if exist "C:\Python310\python.exe" (
        set "PATH=C:\Python310;C:\Python310\Scripts;%PATH%"
        echo [OK] Python encontrado em C:\Python310
        goto :python_found
    )
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
        echo [OK] Python encontrado em %LOCALAPPDATA%\Programs\Python\Python312
        goto :python_found
    )
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
        echo [OK] Python encontrado em %LOCALAPPDATA%\Programs\Python\Python311
        goto :python_found
    )
    if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python310;%LOCALAPPDATA%\Programs\Python\Python310\Scripts;%PATH%"
        echo [OK] Python encontrado em %LOCALAPPDATA%\Programs\Python\Python310
        goto :python_found
    )
    
    :: Python nao encontrado - baixar e instalar automaticamente
    echo [!] Python NAO encontrado em nenhum lugar.
    echo.
    echo    Deseja baixar e instalar o Python automaticamente? (S/N)
    set /p install_python="    Digite S para sim, N para nao: "
    
    if /i "%install_python%"=="S" goto :install_python
    if /i "%install_python%"=="s" goto :install_python
    
    echo.
    echo [!] Sem Python o sistema nao funciona.
    echo     Baixe manualmente em: https://www.python.org/downloads/
    echo     IMPORTANTE: Marque "Add Python to PATH" na instalacao!
    echo     Depois rode este BAT novamente.
    echo.
    pause
    exit /b 1
    
    :install_python
    echo.
    echo Baixando Python 3.12...
    curl -L -o "%TEMP%\python-installer.exe" https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe 2>nul
    if %errorlevel% neq 0 (
        echo [ERRO] Nao conseguiu baixar o Python.
        echo        Baixe manualmente em: https://www.python.org/downloads/
        echo        Marque "Add Python to PATH" na instalacao!
        pause
        exit /b 1
    )
    echo Instalando Python (marque "Add Python to PATH")...
    "%TEMP%\python-installer.exe" /passive InstallAllUsers=0 PrependPath=1 Include_pip=1
    echo.
    echo [OK] Python instalado! Atualizando PATH...
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
    del "%TEMP%\python-installer.exe" 2>nul
    
    :: Verifica se instalou certo
    python --version 2>nul
    if %errorlevel% neq 0 (
        echo [ERRO] Python instalado mas nao esta no PATH.
        echo        Feche esta janela, abra um NOVO prompt e rode este BAT novamente.
        echo.
        pause
        exit /b 1
    )
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
    if %errorlevel% neq 0 (
        echo [ERRO] Nao conseguiu instalar o pip.
        echo        Tente manualmente: python -m ensurepip --upgrade
        pause
        exit /b 1
    )
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
        echo        Tente: python -m venv venv
        pause
        exit /b 1
    )
    echo [OK] Ambiente virtual criado!
) else (
    echo [OK] Ambiente virtual ja existe.
)

echo Ativando ambiente virtual...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao ativar ambiente virtual!
    pause
    exit /b 1
)
echo [OK] Ambiente virtual ativado!
echo.

:: ============================================================
:: ETAPA 4: INSTALAR DEPENDENCIAS
:: ============================================================
echo [4/6] Instalando dependencias (pode demorar na primeira vez)...
echo.

echo Atualizando pip...
pip install --upgrade pip 2>nul

echo Instalando yfinance...
pip install yfinance 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar yfinance!
    pause
    exit /b 1
)

echo Instalando streamlit...
pip install streamlit 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar streamlit!
    pause
    exit /b 1
)

echo Instalando plotly...
pip install plotly 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar plotly!
    pause
    exit /b 1
)

echo Instalando pandas...
pip install pandas 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar pandas!
    pause
    exit /b 1
)

echo Instalando requests...
pip install requests 2>nul

echo Tentando instalar MetaTrader5 (opcional)...
pip install MetaTrader5 2>nul
if %errorlevel% neq 0 (
    echo [AVISO] MetaTrader5 nao instalado - usando Yahoo Finance.
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
if %errorlevel% neq 0 echo "  yfinance: FALHOU!"

python -c "import streamlit; print('  streamlit: OK')" 2>nul
if %errorlevel% neq 0 echo "  streamlit: FALHOU!"

python -c "import plotly; print('  plotly: OK')" 2>nul
if %errorlevel% neq 0 echo "  plotly: FALHOU!"

python -c "import pandas; print('  pandas: OK')" 2>nul
if %errorlevel% neq 0 echo "  pandas: FALHOU!"

python -c "import MetaTrader5; print('  MetaTrader5: OK')" 2>nul
if %errorlevel% neq 0 echo "  MetaTrader5: NAO DISPONIVEL (usando Yahoo Finance)"

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
echo        Roda direto no prompt de comando
echo.
echo    [3] Sair
echo.
set /p choice="    Digite 1, 2 ou 3: "

if "%choice%"=="1" goto dashboard
if "%choice%"=="2" goto terminal
if "%choice%"=="3" goto fim
goto dashboard

:dashboard
echo.
echo ============================================================
echo    Iniciando Dashboard Web...
echo    Navegador: http://localhost:8501
echo    Para PARAR: Ctrl+C ou feche esta janela
echo ============================================================
echo.
streamlit run dashboard/app.py --server.headless true
echo.
echo Dashboard encerrado.
pause
goto fim

:terminal
echo.
echo ============================================================
echo    Iniciando modo terminal...
echo    Para PARAR: Ctrl+C
echo ============================================================
echo.
python main.py
echo.
echo Sistema encerrado.
pause
goto fim

:fim
echo.
echo Ate logo!
pause
