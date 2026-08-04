@echo off
chcp 65001 >nul
title BTJ Foods — Devolutiva Pisciculturas

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   BTJ Foods — Devolutiva Pisciculturas           ║
echo ║   Atualizacao automatica do dashboard            ║
echo ╚══════════════════════════════════════════════════╝
echo.

set PASTA=P:\FOODS\PCP\31 - Originacao
set SCRIPTS=%PASTA%\scripts
set SCRIPT=%SCRIPTS%\coletar_devolutiva.py
set PREPARAR=%SCRIPTS%\preparar_dashboard.py
set DASHBOARD=%PASTA%\devolutiva-pisciculturas.html
set JSON=%PASTA%\devolutiva_dados.json
set HTML_FINAL=%PASTA%\devolutiva_dashboard_atual.html
set URL_BASE=https://raw.githubusercontent.com/cezarusan/razec/claude/pisciculturas-dashboard-devolutiva-kfazaq

:: ── 1. Cria pasta se nao existir ─────────────────────────────────────────────
if not exist "%SCRIPTS%" mkdir "%SCRIPTS%"

:: ── 2. Baixa versoes mais recentes do GitHub ──────────────────────────────────
echo [1/4] Baixando arquivos atualizados do GitHub...
python -c "import urllib.request as r; r.urlretrieve('%URL_BASE%/scripts/coletar_devolutiva.py', r'%SCRIPT%'); r.urlretrieve('%URL_BASE%/scripts/preparar_dashboard.py', r'%PREPARAR%'); r.urlretrieve('%URL_BASE%/dashboards/devolutiva-pisciculturas.html', r'%DASHBOARD%'); print('   OK')"
if errorlevel 1 (
    echo    ERRO ao baixar arquivos. Verifique a conexao com a internet.
    pause
    exit /b 1
)

:: ── 3. Coleta dados e exporta JSON ────────────────────────────────────────────
echo.
echo [2/4] Coletando os 100 ultimos apontamentos...
echo.
python "%SCRIPT%" --simulacao --exportar-json
if errorlevel 1 (
    echo.
    echo    ERRO ao executar o script. Verifique se a rede P:\ esta acessivel.
    pause
    exit /b 1
)

:: ── 4. Injeta dados no HTML ────────────────────────────────────────────────────
echo.
echo [3/4] Preparando dashboard com dados atualizados...
python "%PREPARAR%"
if errorlevel 1 (
    echo    ERRO ao preparar dashboard.
    pause
    exit /b 1
)

:: ── 5. Abre o dashboard no navegador ─────────────────────────────────────────
echo.
echo [4/4] Abrindo dashboard no navegador...
start "" "%HTML_FINAL%"

echo.
echo ══════════════════════════════════════════════════════
echo   Dashboard aberto com dados carregados automaticamente!
echo ══════════════════════════════════════════════════════
echo.
timeout /t 3 >nul
