# MT5 Distributed Worker Manager Startup Script for PowerShell
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       MT5 Distributed Worker Manager Node             " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".env")) {
    Write-Host "[!] .env not found. Creating from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.9+ 64-bit and try again." -ForegroundColor Yellow
    exit 1
}

# Check virtual environment (optional)
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "[+] Activating local virtual environment (.venv)..." -ForegroundColor Green
    & ".venv\Scripts\Activate.ps1"
}

Write-Host "[+] Launching Worker Manager Daemon..." -ForegroundColor Green
python worker_manager.py
