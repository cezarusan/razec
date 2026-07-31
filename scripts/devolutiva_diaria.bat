@echo off
:: ─────────────────────────────────────────────────────────
:: BTJ Foods — Coleta Diária Devolutiva Pisciculturas
:: Agendado via Agendador de Tarefas do Windows
:: ─────────────────────────────────────────────────────────

:: Caminho do script Python (ajuste se necessário)
set SCRIPT="P:\FOODS\PCP\31 - Originação\scripts\coletar_devolutiva.py"

:: Conecta à rede se necessário (ajuste credenciais se exigido)
:: net use P: \\servidor\FOODS /user:DOMINIO\usuario senha

echo [%date% %time%] Iniciando coleta devolutiva pisciculturas...

:: Roda o script em modo automático (sem perguntas, grava direto)
python %SCRIPT% --automatico

if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Coleta concluida com sucesso.
) else (
    echo [%date% %time%] ERRO na coleta. Verifique o log em:
    echo P:\FOODS\PCP\31 - Originação\logs_devolutiva\
)
