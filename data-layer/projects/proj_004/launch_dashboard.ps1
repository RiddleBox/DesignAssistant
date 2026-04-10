Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DashboardDir = Join-Path $ProjectDir "dashboard"
$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$IncomingDir = Join-Path $ProjectDir "..\..\..\background\real_intel_samples\incoming"

function Write-Section([string]$Message) {
    Write-Host ""
    Write-Host "=== $Message ===" -ForegroundColor Cyan
}

function Fail([string]$Message) {
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

Write-Section "Launch dashboard"
Write-Host "Project:   $ProjectDir"
Write-Host "Dashboard: $DashboardDir"

if (-not (Test-Path $PythonExe)) {
    Fail "Missing .venv. Please run initiate.cmd first."
}

if (-not (Test-Path $DashboardDir)) {
    Fail "Dashboard directory not found: $DashboardDir"
}

New-Item -ItemType Directory -Path $IncomingDir -Force | Out-Null
Write-Host "Incoming sample dir: $IncomingDir"
Write-Host "If the pipeline says incoming is empty, put JSON samples there first." -ForegroundColor Yellow

Push-Location $DashboardDir
try {
    & $PythonExe -m streamlit run app.py
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
