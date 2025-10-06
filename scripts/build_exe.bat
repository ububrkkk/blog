@echo off
setlocal

for %%I in ("%~dp0..") do set ROOT=%%~fI
set PYI=%ROOT%\.venv\Scripts\pyinstaller.exe
set PIP=%ROOT%\.venv\Scripts\pip.exe
set PY=%ROOT%\.venv\Scripts\python.exe

if not exist "%PY%" (
  echo [i] Creating venv...
  python -m venv "%ROOT%\.venv"
  if errorlevel 1 exit /b 1
)

"%PIP%" install -r "%ROOT%\requirements.txt" >nul 2>&1
"%PIP%" install pyinstaller >nul 2>&1

set SRC=%ROOT%\src\blog_keyword_analyzer\gui.py
"%PYI%" --noconfirm --onefile --windowed --name BlogKeywordAnalyzer --paths "%ROOT%\src" "%SRC%"
if errorlevel 1 exit /b 1

set EXE=%ROOT%\dist\BlogKeywordAnalyzer.exe
if exist "%EXE%" (
  echo [✓] Build complete: %EXE%
) else (
  echo [!] Build output not found: %EXE%
  exit /b 1
)

exit /b 0

