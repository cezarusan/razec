@echo off
chcp 65001 >nul
title BTJ Foods — Devolutiva Pisciculturas

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   BTJ Foods — Devolutiva Pisciculturas           ║
echo ║   Atualizacao automatica do dashboard            ║
echo ╚══════════════════════════════════════════════════╝
echo.

set PASTA=P:\FOODS\PCP\31 - Originacao\scripts
set SCRIPT=%PASTA%\coletar_devolutiva.py
set DASHBOARD=P:\FOODS\PCP\31 - Originacao\devolutiva-pisciculturas.html
set JSON=P:\FOODS\PCP\31 - Originacao\devolutiva_dados.json
set URL_BASE=https://raw.githubusercontent.com/cezarusan/razec/claude/pisciculturas-dashboard-devolutiva-kfazaq

:: ── 1. Cria pasta se não existir ─────────────────────────────────────────────
if not exist "%PASTA%" (
    echo [1/4] Criando pasta %PASTA%...
    mkdir "%PASTA%"
) else (
    echo [1/4] Pasta OK: %PASTA%
)

:: ── 2. Baixa versao mais recente do script ───────────────────────────────────
echo.
echo [2/4] Baixando script atualizado do GitHub...
python -c "import urllib.request; urllib.request.urlretrieve('%URL_BASE%/scripts/coletar_devolutiva.py', r'%SCRIPT%'); print('   OK: coletar_devolutiva.py')"
if errorlevel 1 (
    echo    ERRO ao baixar o script. Verifique sua conexao com a internet.
    pause
    exit /b 1
)

:: ── 3. Baixa versao mais recente do dashboard ────────────────────────────────
echo.
echo [3/4] Baixando dashboard atualizado do GitHub...
python -c "import urllib.request; urllib.request.urlretrieve('%URL_BASE%/dashboards/devolutiva-pisciculturas.html', r'%DASHBOARD%'); print('   OK: devolutiva-pisciculturas.html')"
if errorlevel 1 (
    echo    ERRO ao baixar o dashboard. Verifique sua conexao com a internet.
    pause
    exit /b 1
)

:: ── 4. Executa o script e exporta JSON ──────────────────────────────────────
echo.
echo [4/4] Coletando dados (ultimos 100 apontamentos) e gerando JSON...
echo.
python "%SCRIPT%" --simulacao --exportar-json
if errorlevel 1 (
    echo.
    echo    ERRO ao executar o script. Verifique se os arquivos de rede estao acessiveis.
    pause
    exit /b 1
)

:: ── 5. Abre o dashboard no navegador ─────────────────────────────────────────
echo.
echo ══════════════════════════════════════════════════════
echo   Abrindo dashboard no navegador...
echo   Clique em "Carregar JSON" e selecione o arquivo:
echo   %JSON%
echo ══════════════════════════════════════════════════════
echo.
start "" "%DASHBOARD%"

echo   Pronto! Pressione qualquer tecla para fechar.
pause >nul
