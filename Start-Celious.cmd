@echo off
if not exist "%~dp0service\config.json" (
  echo Run Install.cmd first.
  pause
  exit /b 1
)
if not exist "%~dp0service\.venv\Scripts\pythonw.exe" (
  echo Run Install.cmd first.
  pause
  exit /b 1
)
start "" "%~dp0service\.venv\Scripts\pythonw.exe" "%~dp0service\tray.py" --show
