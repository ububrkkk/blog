param([switch]$Clean)

$ErrorActionPreference = 'Stop'

function Ensure-Venv($root) {
  $venvPy = Join-Path $root ".venv/Scripts/python.exe"
  if (-not (Test-Path $venvPy)) {
    Write-Host "[i] Creating venv..."
    python -m venv (Join-Path $root ".venv")
  }
}

function Ensure-PyInstaller($root) {
  $pip = Join-Path $root ".venv/Scripts/pip.exe"
  & $pip install -r (Join-Path $root "requirements.txt") | Out-Null
  & $pip install pyinstaller | Out-Null
}

function Build-EXE($root, $clean) {
  $pyinstaller = Join-Path $root ".venv/Scripts/pyinstaller.exe"
  $src = Join-Path $root "src/blog_keyword_analyzer/gui.py"
  $args = @("--noconfirm", "--onefile", "--windowed", "--name", "BlogKeywordAnalyzer", "--paths", (Join-Path $root "src"), $src)
  if ($clean) { $args = @("--clean") + $args }
  & $pyinstaller @args
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed ($LASTEXITCODE)" }
  $exe = Join-Path $root "dist/BlogKeywordAnalyzer.exe"
  if (Test-Path $exe) {
    Write-Host "[✓] Build complete: $exe"
    return $exe
  } else {
    throw "Build output not found at $exe"
  }
}

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Ensure-Venv $root
Ensure-PyInstaller $root
$exe = Build-EXE $root $Clean.IsPresent
Write-Host "[i] You can now double-click: $exe"

