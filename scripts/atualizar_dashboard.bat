@echo off
chcp 65001 >nul
title BTJ Foods — Devolutiva Pisciculturas
python -c "import urllib.request,os,time; t=str(int(time.time())); url='https://raw.githubusercontent.com/cezarusan/razec/claude/pisciculturas-dashboard-devolutiva-kfazaq/scripts/executar.py?t='+t; req=urllib.request.Request(url,headers={'Cache-Control':'no-cache','Pragma':'no-cache'}); f=os.path.join(os.environ['TEMP'],'devolutiva_run.py'); open(f,'wb').write(urllib.request.urlopen(req).read()); exec(open(f,encoding='utf-8').read())"
