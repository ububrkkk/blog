param()

$ErrorActionPreference = 'Stop'

try { chcp 65001 | Out-Null } catch {}
$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

function Ensure-Venv($root) {
  $venvPy = Join-Path $root ".venv/Scripts/pythonw.exe"
  if (-not (Test-Path $venvPy)) {
    Write-Host "[i] Creating venv..."
    python -m venv (Join-Path $root ".venv")
    & (Join-Path $root ".venv/Scripts/pip.exe") install -r (Join-Path $root "requirements.txt")
  }
}

function Run-GUI($root) {
  $env:PYTHONPATH = (Join-Path $root 'src')
  $venvPyw = Join-Path $root ".venv/Scripts/pythonw.exe"
  Start-Process -FilePath $venvPyw -ArgumentList "-m","blog_keyword_analyzer.gui" -WorkingDirectory $root
}

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Ensure-Venv $root
Run-GUI $root
