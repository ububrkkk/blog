@echo off
setlocal

for %%I in ("%~dp0..") do set ROOT=%%~fI
set VENV_PY=%ROOT%\.venv\Scripts\python.exe
set VENV_PIP=%ROOT%\.venv\Scripts\pip.exe
set STREAMLIT=%ROOT%\.venv\Scripts\streamlit.exe

chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist "%VENV_PY%" (
  echo [i] Creating venv...
  python -m venv "%ROOT%\.venv"
  if errorlevel 1 exit /b 1
)

"%VENV_PIP%" install -r "%ROOT%\requirements.txt"

set PYTHONPATH=%ROOT%\src
"%STREAMLIT%" run "%ROOT%\src\blog_keyword_analyzer\streamlit_platform.py" --server.headless false
exit /b %errorlevel%
