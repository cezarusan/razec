# Cria atalho do Dashboard na area de trabalho
# Execute uma vez -- depois use o atalho diretamente

try {
    $WshShell  = New-Object -comObject WScript.Shell
    $desktop   = [System.Environment]::GetFolderPath('Desktop')
    $alvo      = Join-Path $PSScriptRoot "iniciar.ps1"
    $atalho    = Join-Path $desktop "Dashboard Apontamentos.lnk"

    $lnk = $WshShell.CreateShortcut($atalho)
    $lnk.TargetPath       = "powershell.exe"
    $lnk.Arguments        = "-ExecutionPolicy Bypass -NoProfile -File `"$alvo`""
    $lnk.WorkingDirectory = Split-Path -Parent $PSScriptRoot
    $lnk.WindowStyle      = 1
    $lnk.IconLocation     = "powershell.exe,0"
    $lnk.Description      = "Abre o Dashboard de Apontamentos"
    $lnk.Save()

    Write-Host ""
    Write-Host "  Atalho criado na area de trabalho!" -ForegroundColor Green
    Write-Host "  Arquivo: $atalho" -ForegroundColor DarkGray
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "  [ERRO] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
}

Read-Host "  Pressione Enter para fechar"
