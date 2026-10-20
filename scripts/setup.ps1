$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Criando .venv ..."
    python -m venv .venv
}

$py = ".\.venv\Scripts\python.exe"
Write-Host "Atualizando pip ..."
& $py -m pip install --upgrade pip
Write-Host "PyTorch (CUDA 12.8) ..."
& $py -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
Write-Host "Dependencias da API ..."
& $py -m pip install -r requirements.txt

if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
    Write-Host "Criei .env a partir de .env.example — edite API_KEY antes do tunel."
}

Write-Host ""
Write-Host "Pronto. Suba a API com:  .\scripts\run_local.ps1"
Write-Host "Túnel (outra internet):   .\scripts\tunnel.ps1"
