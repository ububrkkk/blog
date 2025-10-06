@echo off
setlocal

for %%I in ("%~dp0..") do set ROOT=%%~fI
set VENV_PYW=%ROOT%\.venv\Scripts\pythonw.exe
set VENV_PIP=%ROOT%\.venv\Scripts\pip.exe

chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist "%VENV_PYW%" (
  echo [i] Creating venv...
  python -m venv "%ROOT%\.venv"
  if errorlevel 1 exit /b 1
  "%VENV_PIP%" install -r "%ROOT%\requirements.txt"
  if errorlevel 1 exit /b 1
)

set PYTHONPATH=%ROOT%\src
start "Blog Keyword Analyzer" "%VENV_PYW%" -m blog_keyword_analyzer.gui
exit /b 0
