param()

$ErrorActionPreference = 'Stop'

try { chcp 65001 | Out-Null } catch {}
$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

function Ensure-Venv($root) {
  $venvPy = Join-Path $root ".venv/Scripts/python.exe"
  if (-not (Test-Path $venvPy)) {
    Write-Host "[i] Creating venv..."
    python -m venv (Join-Path $root ".venv")
  }
}

function Ensure-Deps($root) {
  $pip = Join-Path $root ".venv/Scripts/pip.exe"
  & $pip install -r (Join-Path $root "requirements.txt")
}

function Run-Streamlit($root) {
  $env:PYTHONPATH = (Join-Path $root 'src')
  $streamlit = Join-Path $root ".venv/Scripts/streamlit.exe"
  & $streamlit run (Join-Path $root 'src/blog_keyword_analyzer/streamlit_platform.py') --server.headless false
}

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Ensure-Venv $root
Ensure-Deps $root
Run-Streamlit $root
