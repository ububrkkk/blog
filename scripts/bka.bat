@echo off
setlocal enabledelayedexpansion

rem Determine project root (parent of scripts)
for %%I in ("%~dp0..") do set ROOT=%%~fI
set VENV_PY=%ROOT%\.venv\Scripts\python.exe
set VENV_PIP=%ROOT%\.venv\Scripts\pip.exe

rem Use UTF-8 code page for proper Korean output
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist "%VENV_PY%" (
  echo [i] Creating venv...
  python -m venv "%ROOT%\.venv"
  if errorlevel 1 exit /b 1
  "%VENV_PIP%" install -r "%ROOT%\requirements.txt"
  if errorlevel 1 exit /b 1
)

set PYTHONPATH=%ROOT%\src
"%VENV_PY%" -m blog_keyword_analyzer.cli %*
exit /b %errorlevel%
