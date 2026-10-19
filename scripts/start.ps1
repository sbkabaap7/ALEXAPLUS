param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create the project virtual environment first; see README.md.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\dist\index.html'))) { throw 'Build the frontend first: pnpm --dir frontend build' }
$ollamaPath = Join-Path $projectRoot 'tools\ollama\ollama.exe'
if (Test-Path -LiteralPath $ollamaPath) {
    $env:OLLAMA_MODELS = Join-Path $projectRoot 'models\ollama'
    $env:OLLAMA_HOST = '127.0.0.1:11434'
    New-Item -ItemType Directory -Force -Path $env:OLLAMA_MODELS | Out-Null
    $ollamaListening = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue
    if (-not $ollamaListening) {
        Start-Process -FilePath $ollamaPath -ArgumentList 'serve' -WorkingDirectory (Split-Path -Parent $ollamaPath) -WindowStyle Hidden
    }
}
$env:GUESTGUARD_BASE_URL = "http://127.0.0.1:$Port"
& $pythonPath -m uvicorn backend.app.main:app --host 127.0.0.1 --port $Port --no-access-log
