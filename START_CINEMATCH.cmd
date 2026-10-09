@echo off
cd /d "%~dp0"
set "OPENBLAS_NUM_THREADS=1"
set "CINE_PYTHON="
if exist ".venv\Scripts\python.exe" set "CINE_PYTHON=%~dp0.venv\Scripts\python.exe"
if not defined CINE_PYTHON if exist "..\..\work\cinematch-venv\Scripts\python.exe" set "CINE_PYTHON=%~dp0..\..\work\cinematch-venv\Scripts\python.exe"
if not defined CINE_PYTHON (
  echo Create the Python environment using README.md first.
  pause
  exit /b 1
)
"%CINE_PYTHON%" scripts\launch_app.py
if errorlevel 1 pause
