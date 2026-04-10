Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ProjectDir ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$PipExe = Join-Path $VenvDir "Scripts\pip.exe"
$IncomingDir = Join-Path $ProjectDir "..\..\..\background\real_intel_samples\incoming"
$ProcessedDir = Join-Path $ProjectDir "..\..\..\background\real_intel_samples\processed"
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

Write-Section "Project bootstrap"
Write-Host "Project: $ProjectDir"

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    Fail "Python was not found in PATH. Please install Python 3.10+ first."
}

Write-Host "Python command: $($PythonCommand.Source)"

if (-not (Test-Path $VenvDir)) {
    Write-Section "Create virtual environment"
    & python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Fail "Failed to create .venv"
    }
} else {
    Write-Host "Virtual environment already exists: $VenvDir"
}

if (-not (Test-Path $PythonExe)) {
    Fail "Virtual environment Python was not found at $PythonExe"
}

Write-Section "Upgrade pip toolchain"
& $PythonExe -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    Fail "Failed to upgrade pip/setuptools/wheel"
}

$Packages = @(
    "streamlit",
    "anthropic",
    "pydantic",
    "pyyaml",
    "openai",
    "numpy",
    "faiss-cpu",
    "sentence-transformers",
    "torch",
    "fastapi",
    "uvicorn",
    "tqdm",
    "python-dotenv",
    "pytest",
    "pytest-asyncio",
    "requests"
)

Write-Section "Install project packages"
& $PythonExe -m pip install @Packages
if ($LASTEXITCODE -ne 0) {
    Fail "Package installation failed"
}

Write-Section "Prepare sample directories"
New-Item -ItemType Directory -Path $IncomingDir -Force | Out-Null
New-Item -ItemType Directory -Path $ProcessedDir -Force | Out-Null
Write-Host "Incoming:  $IncomingDir"
Write-Host "Processed: $ProcessedDir"

Write-Section "Check LLM config"
if (Test-Path $LocalConfigPath) {
    Write-Host "Using local config: $LocalConfigPath" -ForegroundColor Green
} elseif (Test-Path $TemplateConfigPath) {
    Write-Host "Local config not found. Template exists: $TemplateConfigPath" -ForegroundColor Yellow
    Write-Host "Please review llm_config.local.yaml or environment variables before running LLM-backed flows." -ForegroundColor Yellow
} else {
    Write-Host "No llm_config file found in project root." -ForegroundColor Yellow
}

Write-Section "Done"
Write-Host "Bootstrap completed successfully." -ForegroundColor Green
Write-Host "Next actions:"
Write-Host "- Double-click launch_dashboard.cmd to open the dashboard"
Write-Host "- Double-click run_e2e.cmd to run the end-to-end integration flow"
