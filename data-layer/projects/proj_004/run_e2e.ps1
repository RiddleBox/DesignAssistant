Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$LocalConfigPath = Join-Path $ProjectDir "llm_config.local.yaml"
$TemplateConfigPath = Join-Path $ProjectDir "llm_config.yaml"

function Write-Section([string]$Message) {
    Write-Host ""
    Write-Host "=== $Message ===" -ForegroundColor Cyan
}

function Fail([string]$Message) {
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

Write-Section "Run end-to-end integration"
Write-Host "Project: $ProjectDir"

if (-not (Test-Path $PythonExe)) {
    Fail "Missing .venv. Please run initiate.cmd first."
}

if (Test-Path $LocalConfigPath) {
    Write-Host "Using local config: $LocalConfigPath"
} elseif (Test-Path $TemplateConfigPath) {
    Write-Host "Local config not found. Falling back to template config: $TemplateConfigPath" -ForegroundColor Yellow
    Write-Host "Make sure API keys are available via config or environment variables." -ForegroundColor Yellow
} else {
    Write-Host "No llm_config file found in project root." -ForegroundColor Yellow
}

Push-Location $ProjectDir
try {
    & $PythonExe integration_test_e2e.py
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
