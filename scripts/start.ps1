$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
Set-Location (Split-Path -Parent $here)

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Rode primeiro:  .\scripts\setup.ps1"
    exit 1
}

Write-Host "Abrindo a API em outra janela ..."
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $here "run_local.ps1")
)

Write-Host "Esperando a API subir ..."
Start-Sleep -Seconds 12
& (Join-Path $here "tunnel.ps1")
