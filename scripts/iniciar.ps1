# Dashboard de Apontamentos Geral -- Inicializacao via PowerShell
# Uso: clique direito -> "Executar com PowerShell"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "  Dashboard de Apontamentos Geral" -ForegroundColor Cyan
Write-Host "  http://localhost:5002" -ForegroundColor Green
Write-Host ""

# verifica Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "  [ERRO] Python nao encontrado." -ForegroundColor Red
    Write-Host "  Instale em https://python.org e marque 'Add to PATH'" -ForegroundColor Yellow
    Read-Host "  Pressione Enter para sair"
    exit 1
}

# abre o browser depois de 2 segundos em background
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:5002"
} | Out-Null

# inicia o proxy
Write-Host "  Proxy iniciado. Pressione Ctrl+C para parar." -ForegroundColor DarkGray
Write-Host ""
Set-Location $repo
python scripts\proxy.py
