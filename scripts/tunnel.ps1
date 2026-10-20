$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$port = "8000"
if (Test-Path ".\.env") {
    Get-Content ".\.env" | ForEach-Object {
        if ($_ -match '^\s*PORT\s*=\s*(.+)\s*$') { $port = $Matches[1].Trim() }
    }
}

$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
    Write-Host "cloudflared nao esta no PATH."
    Write-Host "Instale:  winget install Cloudflare.cloudflared"
    Write-Host "Depois feche e abra o terminal e rode este script de novo."
    exit 1
}

Write-Host "A API precisa estar rodando em http://127.0.0.1:$port"
Write-Host "Quando aparecer https://....trycloudflare.com  — esse e o URL para o outro PC."
Write-Host "Ctrl+C fecha o tunel (o URL temporario deixa de valer)."
Write-Host ""
& cloudflared tunnel --url "http://127.0.0.1:$port"
