@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONPATH=%~dp0
set LOGFILE=%~dp0streamlit_launcher.log

echo ==== AI Compound Asset Assistant launcher ==== > "%LOGFILE%"
echo Time: %date% %time% >> "%LOGFILE%"
echo Workdir: %cd% >> "%LOGFILE%"

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Creating .venv... >> "%LOGFILE%"
  python -m venv .venv >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    echo Failed to create virtual environment. >> "%LOGFILE%"
    exit /b 1
  )
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  echo Dependency installation failed. >> "%LOGFILE%"
  exit /b 1
)

echo Starting Streamlit... >> "%LOGFILE%"
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false >> "%LOGFILE%" 2>&1
echo Streamlit exited with code %errorlevel%. >> "%LOGFILE%"
