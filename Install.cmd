@echo off
cd /d "%~dp0"
py -3.12 setup.py --shortcuts
if errorlevel 1 (
  echo Installation failed. Review the message above. Install Python 3.12 x64 with its launcher first.
  pause
  exit /b 1
)
pause
