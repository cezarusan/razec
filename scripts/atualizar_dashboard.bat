@echo off
chcp 65001 >nul
title BTJ Foods — Devolutiva Pisciculturas
python -c "import urllib.request,os,sys; f=os.path.join(os.environ['TEMP'],'devolutiva_run.py'); urllib.request.urlretrieve('https://raw.githubusercontent.com/cezarusan/razec/claude/pisciculturas-dashboard-devolutiva-kfazaq/scripts/executar.py',f); exec(open(f,encoding='utf-8').read())"
