$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:PYTHONPATH = "src"

$py = ".\.venv\Scripts\python.exe"
$tccPy = Join-Path (Split-Path (Get-Location)) "TCGTradeSegmentacao\.venv\Scripts\python.exe"
if (Test-Path $tccPy) {
    $py = $tccPy
} elseif (-not (Test-Path $py)) {
    Write-Host "Rode primeiro:  .\scripts\setup.ps1"
    exit 1
}

$hostName = "127.0.0.1"
$port = "8000"
if (Test-Path ".\.env") {
    Get-Content ".\.env" | ForEach-Object {
        if ($_ -match '^\s*HOST\s*=\s*(.+)\s*$') { $hostName = $Matches[1].Trim() }
        if ($_ -match '^\s*PORT\s*=\s*(.+)\s*$') { $port = $Matches[1].Trim() }
    }
}

Write-Host "API local: http://${hostName}:${port}/docs"
& $py -m uvicorn app.main:app --host $hostName --port $port
