@echo off
:: Dashboard de Apontamentos Geral — Inicializacao automatica (Windows)
:: Coloque um atalho deste arquivo na pasta Inicializacao do Windows para
:: que o dashboard suba automaticamente com o sistema.
::   Win+R  ->  shell:startup  ->  copiar atalho de iniciar.bat

setlocal
cd /d "%~dp0.."

:: verifica se Python esta instalado
where python >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale em https://python.org
    pause
    exit /b 1
)

echo.
echo  Dashboard de Apontamentos Geral
echo  Iniciando proxy em http://localhost:5002
echo.

:: abre o browser apos 2 segundos (em paralelo)
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5002"

:: inicia o proxy (fica rodando em foreground)
python scripts\proxy.py

pause
