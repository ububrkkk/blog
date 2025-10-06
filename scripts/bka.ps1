param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)

$ErrorActionPreference = 'Stop'

# Ensure UTF-8 console
try { chcp 65001 | Out-Null } catch {}
$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

function Ensure-Venv($root) {
  $venvPy = Join-Path $root ".venv/Scripts/python.exe"
  if (-not (Test-Path $venvPy)) {
    Write-Host "[i] Creating venv..."
    python -m venv (Join-Path $root ".venv")
    & (Join-Path $root ".venv/Scripts/pip.exe") install -r (Join-Path $root "requirements.txt")
  }
}

function Run-CLI($root, $args) {
  $env:PYTHONPATH = (Join-Path $root 'src')
  $venvPy = Join-Path $root ".venv/Scripts/python.exe"
  & $venvPy -m blog_keyword_analyzer.cli @args
  exit $LASTEXITCODE
}

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Ensure-Venv $root
Run-CLI $root $Args
