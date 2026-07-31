# =============================================================================
# BTJ Foods - Configurar Agendamento e Atalho
# Devolutiva Pisciculturas
#
# Execute como Administrador:
#   Clique com botao direito -> "Executar como administrador"
# =============================================================================

$ErrorActionPreference = "Stop"

# Caminhos
$PASTA_SCRIPTS  = "P:\FOODS\PCP\31 - Originacao\scripts"
$SCRIPT_PY      = "$PASTA_SCRIPTS\coletar_devolutiva.py"
$ARQUIVO_BAT    = "$PASTA_SCRIPTS\devolutiva_diaria.bat"
$PASTA_LOG      = "P:\FOODS\PCP\31 - Originacao\logs_devolutiva"

# Nome da tarefa no Agendador
$NOME_TAREFA    = "BTJFoods_Devolutiva_Pisciculturas"

# Horarios de execucao diaria
$HORA_MANHA = "10:00"
$HORA_TARDE = "14:00"

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  BTJ Foods - Setup Devolutiva Pisciculturas" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verifica Python
Write-Host "[1/4] Verificando Python..." -ForegroundColor Yellow
try {
    $pythonPath = (Get-Command python -ErrorAction Stop).Source
    $pythonVer  = python --version 2>&1
    Write-Host "      OK: $pythonVer ($pythonPath)" -ForegroundColor Green
} catch {
    Write-Host "      ERRO: Python nao encontrado no PATH." -ForegroundColor Red
    Write-Host "      Instale em https://python.org e marque 'Add to PATH'." -ForegroundColor Red
    Read-Host "      Pressione Enter para sair"
    exit 1
}

# 2. Copia scripts para a pasta de rede
Write-Host ""
Write-Host "[2/4] Copiando scripts para $PASTA_SCRIPTS ..." -ForegroundColor Yellow

$origem = Split-Path -Parent $MyInvocation.MyCommand.Path

try {
    if (-not (Test-Path $PASTA_SCRIPTS)) {
        New-Item -ItemType Directory -Path $PASTA_SCRIPTS -Force | Out-Null
        Write-Host "      Pasta criada: $PASTA_SCRIPTS" -ForegroundColor Green
    }
    Copy-Item "$origem\coletar_devolutiva.py" $SCRIPT_PY -Force
    Copy-Item "$origem\devolutiva_diaria.bat" $ARQUIVO_BAT -Force
    Write-Host "      OK: scripts copiados." -ForegroundColor Green
} catch {
    Write-Host "      AVISO: Nao foi possivel copiar para a rede: $_" -ForegroundColor Yellow
    Write-Host "      Copie manualmente os arquivos para $PASTA_SCRIPTS" -ForegroundColor Yellow
}

# 3. Cria tarefa no Agendador de Tarefas
Write-Host ""
Write-Host "[3/4] Configurando Agendador de Tarefas..." -ForegroundColor Yellow
Write-Host "      Tarefa: $NOME_TAREFA" -ForegroundColor Gray
Write-Host "      Horarios: seg a sex as $HORA_MANHA e as $HORA_TARDE" -ForegroundColor Gray

try {
    $tarefaExistente = Get-ScheduledTask -TaskName $NOME_TAREFA -ErrorAction SilentlyContinue
    if ($tarefaExistente) {
        Unregister-ScheduledTask -TaskName $NOME_TAREFA -Confirm:$false
        Write-Host "      Tarefa anterior removida." -ForegroundColor Gray
    }

    $acao = New-ScheduledTaskAction `
        -Execute "cmd.exe" `
        -Argument "/c `"$ARQUIVO_BAT`"" `
        -WorkingDirectory $PASTA_SCRIPTS

    $gatilhoManha = New-ScheduledTaskTrigger `
        -Weekly `
        -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday `
        -At $HORA_MANHA

    $gatilhoTarde = New-ScheduledTaskTrigger `
        -Weekly `
        -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday `
        -At $HORA_TARDE

    $config = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
        -RestartCount 2 `
        -RestartInterval (New-TimeSpan -Minutes 5) `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable

    $principal = New-ScheduledTaskPrincipal `
        -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
        -RunLevel Limited `
        -LogonType InteractiveToken

    Register-ScheduledTask `
        -TaskName $NOME_TAREFA `
        -Action $acao `
        -Trigger @($gatilhoManha, $gatilhoTarde) `
        -Settings $config `
        -Principal $principal `
        -Description "Coleta automatica de dados para Devolutiva Pisciculturas - BTJ Foods" `
        | Out-Null

    Write-Host "      OK: tarefa criada (seg a sex as $HORA_MANHA e as $HORA_TARDE)." -ForegroundColor Green

} catch {
    Write-Host "      ERRO ao criar tarefa: $_" -ForegroundColor Red
}

# 4. Cria atalhos na Area de Trabalho
Write-Host ""
Write-Host "[4/4] Criando atalhos na Area de Trabalho..." -ForegroundColor Yellow

$desktop = [Environment]::GetFolderPath("Desktop")
$wsh     = New-Object -ComObject WScript.Shell

$atalhoSim = $wsh.CreateShortcut("$desktop\Devolutiva Pisciculturas - SIMULAR.lnk")
$atalhoSim.TargetPath       = "cmd.exe"
$atalhoSim.Arguments        = "/k python `"$SCRIPT_PY`" --simulacao"
$atalhoSim.WorkingDirectory = $PASTA_SCRIPTS
$atalhoSim.Description      = "Simula coleta (nao grava dados)"
$atalhoSim.IconLocation     = "shell32.dll,21"
$atalhoSim.Save()
Write-Host "      OK: Devolutiva Pisciculturas - SIMULAR" -ForegroundColor Green

$atalhoExec = $wsh.CreateShortcut("$desktop\Devolutiva Pisciculturas - EXECUTAR.lnk")
$atalhoExec.TargetPath       = "cmd.exe"
$atalhoExec.Arguments        = "/k python `"$SCRIPT_PY`""
$atalhoExec.WorkingDirectory = $PASTA_SCRIPTS
$atalhoExec.Description      = "Executa coleta (pede confirmacao antes de gravar)"
$atalhoExec.IconLocation     = "shell32.dll,145"
$atalhoExec.Save()
Write-Host "      OK: Devolutiva Pisciculturas - EXECUTAR" -ForegroundColor Green

$atalhoInsp = $wsh.CreateShortcut("$desktop\Devolutiva Pisciculturas - INSPECIONAR.lnk")
$atalhoInsp.TargetPath       = "cmd.exe"
$atalhoInsp.Arguments        = "/k python `"$SCRIPT_PY`" --inspecionar"
$atalhoInsp.WorkingDirectory = $PASTA_SCRIPTS
$atalhoInsp.Description      = "Inspeciona colunas dos arquivos fonte"
$atalhoInsp.IconLocation     = "shell32.dll,23"
$atalhoInsp.Save()
Write-Host "      OK: Devolutiva Pisciculturas - INSPECIONAR" -ForegroundColor Green

# Resumo
Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  CONFIGURACAO CONCLUIDA" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Agendamento:" -ForegroundColor White
Write-Host "    Seg a sex as $HORA_MANHA e as $HORA_TARDE (automatico)" -ForegroundColor Gray
Write-Host "    Log em: $PASTA_LOG" -ForegroundColor Gray
Write-Host ""
Write-Host "  Atalhos criados na Area de Trabalho:" -ForegroundColor White
Write-Host "    SIMULAR    - visualiza resultado sem gravar" -ForegroundColor Gray
Write-Host "    EXECUTAR   - roda e pede confirmacao antes de gravar" -ForegroundColor Gray
Write-Host "    INSPECIONAR - mostra estrutura dos arquivos fonte" -ForegroundColor Gray
Write-Host ""
Write-Host "  IMPORTANTE - antes de usar:" -ForegroundColor Yellow
Write-Host "    1. Preencha pm_previsto.xlsx com o PM de cada lote" -ForegroundColor Yellow
Write-Host "    2. Verifique codfor_unidades.xlsx (criado ao rodar INSPECIONAR)" -ForegroundColor Yellow
Write-Host ""

Read-Host "  Pressione Enter para fechar"
