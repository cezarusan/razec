# =============================================================================
# BTJ Foods — Configurar Agendamento e Atalho
# Devolutiva Pisciculturas
#
# Execute como Administrador:
#   Clique com botão direito → "Executar como administrador"
# =============================================================================

$ErrorActionPreference = "Stop"

# ── Caminhos ─────────────────────────────────────────────────────────────────
$PASTA_SCRIPTS  = "P:\FOODS\PCP\31 - Originação\scripts"
$SCRIPT_PY      = "$PASTA_SCRIPTS\coletar_devolutiva.py"
$ARQUIVO_BAT    = "$PASTA_SCRIPTS\devolutiva_diaria.bat"
$PASTA_LOG      = "P:\FOODS\PCP\31 - Originação\logs_devolutiva"

# Nome da tarefa no Agendador
$NOME_TAREFA    = "BTJFoods_Devolutiva_Pisciculturas"

# Horário de execução diária (ajuste se necessário)
$HORA_EXECUCAO  = "07:00"

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   BTJ Foods — Setup Devolutiva Pisciculturas     ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── 1. Verifica Python ───────────────────────────────────────────────────────
Write-Host "[1/4] Verificando Python..." -ForegroundColor Yellow
try {
    $pythonPath = (Get-Command python -ErrorAction Stop).Source
    $pythonVer  = python --version 2>&1
    Write-Host "      OK: $pythonVer ($pythonPath)" -ForegroundColor Green
} catch {
    Write-Host "      ERRO: Python não encontrado no PATH." -ForegroundColor Red
    Write-Host "      Instale em https://python.org e marque 'Add to PATH'." -ForegroundColor Red
    Read-Host "      Pressione Enter para sair"
    exit 1
}

# ── 2. Copia scripts para a pasta de rede ────────────────────────────────────
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
    Write-Host "      AVISO: Não foi possível copiar para a rede: $_" -ForegroundColor Yellow
    Write-Host "      Copie manualmente os arquivos para $PASTA_SCRIPTS" -ForegroundColor Yellow
}

# ── 3. Cria tarefa no Agendador de Tarefas ───────────────────────────────────
Write-Host ""
Write-Host "[3/4] Configurando Agendador de Tarefas..." -ForegroundColor Yellow
Write-Host "      Tarefa: $NOME_TAREFA" -ForegroundColor Gray
Write-Host "      Horário: todos os dias às $HORA_EXECUCAO" -ForegroundColor Gray

try {
    # Remove tarefa anterior se existir
    $tarefaExistente = Get-ScheduledTask -TaskName $NOME_TAREFA -ErrorAction SilentlyContinue
    if ($tarefaExistente) {
        Unregister-ScheduledTask -TaskName $NOME_TAREFA -Confirm:$false
        Write-Host "      Tarefa anterior removida." -ForegroundColor Gray
    }

    # Define a ação: rodar o .bat
    $acao = New-ScheduledTaskAction `
        -Execute "cmd.exe" `
        -Argument "/c `"$ARQUIVO_BAT`"" `
        -WorkingDirectory $PASTA_SCRIPTS

    # Gatilho: diário às 07:00 (dias úteis — seg a sex)
    $gatilho = New-ScheduledTaskTrigger `
        -Weekly `
        -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday `
        -At $HORA_EXECUCAO

    # Configurações: executar mesmo se usuário não estiver logado, com máxima prioridade
    $config = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
        -RestartCount 2 `
        -RestartInterval (New-TimeSpan -Minutes 5) `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable

    # Principal: executa com conta do sistema (não precisa estar logado)
    $principal = New-ScheduledTaskPrincipal `
        -UserId "SYSTEM" `
        -RunLevel Highest `
        -LogonType ServiceAccount

    Register-ScheduledTask `
        -TaskName $NOME_TAREFA `
        -Action $acao `
        -Trigger $gatilho `
        -Settings $config `
        -Principal $principal `
        -Description "Coleta automática de dados para Devolutiva Pisciculturas — BTJ Foods" `
        | Out-Null

    Write-Host "      OK: tarefa criada (seg–sex às $HORA_EXECUCAO)." -ForegroundColor Green
    Write-Host "      Você pode ajustar o horário no Agendador de Tarefas." -ForegroundColor Gray

} catch {
    Write-Host "      ERRO ao criar tarefa: $_" -ForegroundColor Red
    Write-Host "      Tente executar o PowerShell como Administrador." -ForegroundColor Yellow
}

# ── 4. Cria atalho na Área de Trabalho ───────────────────────────────────────
Write-Host ""
Write-Host "[4/4] Criando atalhos na Área de Trabalho..." -ForegroundColor Yellow

$desktop = [Environment]::GetFolderPath("Desktop")
$wsh     = New-Object -ComObject WScript.Shell

# Atalho 1: Simulação (seguro — só visualiza, não grava)
$atalhoSim = $wsh.CreateShortcut("$desktop\Devolutiva Pisciculturas - SIMULAR.lnk")
$atalhoSim.TargetPath       = "cmd.exe"
$atalhoSim.Arguments        = "/k python `"$SCRIPT_PY`" --simulacao"
$atalhoSim.WorkingDirectory = $PASTA_SCRIPTS
$atalhoSim.Description      = "Simula coleta (não grava dados)"
$atalhoSim.IconLocation     = "shell32.dll,21"   # ícone de lupa/pesquisa
$atalhoSim.Save()
Write-Host "      OK: Devolutiva Pisciculturas - SIMULAR" -ForegroundColor Green

# Atalho 2: Executar manualmente (pede confirmação antes de gravar)
$atalhoExec = $wsh.CreateShortcut("$desktop\Devolutiva Pisciculturas - EXECUTAR.lnk")
$atalhoExec.TargetPath       = "cmd.exe"
$atalhoExec.Arguments        = "/k python `"$SCRIPT_PY`""
$atalhoExec.WorkingDirectory = $PASTA_SCRIPTS
$atalhoExec.Description      = "Executa coleta (pede confirmação antes de gravar)"
$atalhoExec.IconLocation     = "shell32.dll,145"  # ícone de arquivo/planilha
$atalhoExec.Save()
Write-Host "      OK: Devolutiva Pisciculturas - EXECUTAR" -ForegroundColor Green

# Atalho 3: Inspecionar estrutura dos arquivos
$atalhoInsp = $wsh.CreateShortcut("$desktop\Devolutiva Pisciculturas - INSPECIONAR.lnk")
$atalhoInsp.TargetPath       = "cmd.exe"
$atalhoInsp.Arguments        = "/k python `"$SCRIPT_PY`" --inspecionar"
$atalhoInsp.WorkingDirectory = $PASTA_SCRIPTS
$atalhoInsp.Description      = "Inspeciona colunas dos arquivos fonte"
$atalhoInsp.IconLocation     = "shell32.dll,23"
$atalhoInsp.Save()
Write-Host "      OK: Devolutiva Pisciculturas - INSPECIONAR" -ForegroundColor Green

# ── Resumo ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  CONFIGURAÇÃO CONCLUÍDA" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Agendamento:" -ForegroundColor White
Write-Host "    Segunda a sexta às $HORA_EXECUCAO (automático, sem interação)" -ForegroundColor Gray
Write-Host "    Log diário em: $PASTA_LOG" -ForegroundColor Gray
Write-Host ""
Write-Host "  Atalhos criados na Área de Trabalho:" -ForegroundColor White
Write-Host "    🔍 SIMULAR    — visualiza resultado sem gravar" -ForegroundColor Gray
Write-Host "    ▶  EXECUTAR   — roda e pede confirmação antes de gravar" -ForegroundColor Gray
Write-Host "    🔎 INSPECIONAR — mostra estrutura dos arquivos fonte" -ForegroundColor Gray
Write-Host ""
Write-Host "  IMPORTANTE — antes de usar:" -ForegroundColor Yellow
Write-Host "    1. Preencha pm_previsto.xlsx com o PM de cada lote" -ForegroundColor Yellow
Write-Host "    2. Verifique codfor_unidades.xlsx (criado ao rodar INSPECIONAR)" -ForegroundColor Yellow
Write-Host ""

Read-Host "  Pressione Enter para fechar"
