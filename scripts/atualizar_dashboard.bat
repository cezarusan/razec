@echo off
chcp 65001 >nul
title BTJ Foods — Devolutiva Pisciculturas

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   BTJ Foods — Devolutiva Pisciculturas           ║
echo ║   Atualizacao automatica do dashboard            ║
echo ╚══════════════════════════════════════════════════╝
echo.

set URL=https://raw.githubusercontent.com/cezarusan/razec/claude/pisciculturas-dashboard-devolutiva-kfazaq

:: ── Baixa e executa tudo via Python (evita problemas com acentos no bat) ─────
python -c "
import urllib.request, os, subprocess, sys, glob

url  = '%URL%'
dest = None

# Acha a pasta correta (com ou sem acento)
for p in [r'P:\FOODS\PCP\31 - Origina\u00e7\u00e3o', r'P:\FOODS\PCP\31 - Originacao']:
    if os.path.isdir(p):
        dest = p
        break
if not dest:
    res = glob.glob(r'P:\FOODS\PCP\31*')
    dest = next((r for r in res if os.path.isdir(r)), None)
if not dest:
    print('ERRO: Pasta 31 - Originacao nao encontrada na rede P:')
    input('Pressione Enter para sair...')
    sys.exit(1)

scripts = os.path.join(dest, 'scripts')
os.makedirs(scripts, exist_ok=True)

# 1. Baixa arquivos
print('[1/3] Baixando arquivos atualizados...')
urllib.request.urlretrieve(url+'/scripts/coletar_devolutiva.py',   os.path.join(scripts, 'coletar_devolutiva.py'))
urllib.request.urlretrieve(url+'/scripts/preparar_dashboard.py',   os.path.join(scripts, 'preparar_dashboard.py'))
urllib.request.urlretrieve(url+'/dashboards/devolutiva-pisciculturas.html', os.path.join(dest, 'devolutiva-pisciculturas.html'))
print('   OK')

# 2. Coleta dados
print('[2/3] Coletando os 100 ultimos apontamentos...')
r = subprocess.run([sys.executable, os.path.join(scripts,'coletar_devolutiva.py'), '--simulacao','--exportar-json'])
if r.returncode != 0:
    print('ERRO ao coletar dados.')
    input('Pressione Enter para sair...')
    sys.exit(1)

# 3. Prepara e abre dashboard
print('[3/3] Abrindo dashboard...')
subprocess.run([sys.executable, os.path.join(scripts,'preparar_dashboard.py')])
"

echo.
pause
