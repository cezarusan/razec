# Verificacao de pre-requisitos -- Dashboard de Apontamentos Geral
# Clique direito -> "Executar com PowerShell"

$ok  = "[OK]"
$err = "[FALTA]"
$warn= "[AVISO]"
$tudo_ok = $true

Write-Host ""
Write-Host "  Verificando pre-requisitos..." -ForegroundColor Cyan
Write-Host "  -----------------------------------------" -ForegroundColor DarkGray
Write-Host ""

# 1. Python
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    $ver = python --version 2>&1
    Write-Host "  $ok  Python instalado: $ver" -ForegroundColor Green
} else {
    Write-Host "  $err Python NAO encontrado" -ForegroundColor Red
    Write-Host "       Baixe em: https://python.org  (marque 'Add to PATH')" -ForegroundColor Yellow
    $tudo_ok = $false
}

# 2. Conexao com o Grafana
Write-Host ""
Write-Host "  Testando conexao com Grafana (172.16.0.27:3000)..." -ForegroundColor DarkGray
try {
    $resp = Invoke-WebRequest -Uri "http://172.16.0.27:3000/api/health" `
                              -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  $ok  Grafana acessivel: $($resp.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  $err Grafana NAO acessivel em 172.16.0.27:3000" -ForegroundColor Red
    Write-Host "       Verifique se esta na rede da empresa/VPN" -ForegroundColor Yellow
    $tudo_ok = $false
}

# 3. Porta 5002 livre
$porta = Get-NetTCPConnection -LocalPort 5002 -ErrorAction SilentlyContinue
if ($porta) {
    Write-Host "  $warn Porta 5002 ja em uso (proxy pode ja estar rodando)" -ForegroundColor Yellow
} else {
    Write-Host "  $ok  Porta 5002 disponivel" -ForegroundColor Green
}

# 4. Arquivo proxy.py existe
$proxy = Join-Path $PSScriptRoot "proxy.py"
if (Test-Path $proxy) {
    Write-Host "  $ok  proxy.py encontrado" -ForegroundColor Green
} else {
    Write-Host "  $err proxy.py nao encontrado -- baixe o repositorio completo" -ForegroundColor Red
    $tudo_ok = $false
}

# Resultado final
Write-Host ""
Write-Host "  -----------------------------------------" -ForegroundColor DarkGray
if ($tudo_ok) {
    Write-Host "  Tudo pronto! Execute iniciar.ps1 para abrir o dashboard." -ForegroundColor Green
} else {
    Write-Host "  Corrija os itens marcados com [FALTA] e rode novamente." -ForegroundColor Yellow
}
Write-Host ""
Read-Host "  Pressione Enter para fechar"
