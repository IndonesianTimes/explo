@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo [!] Python tidak ditemukan di PATH. Install Python 3.10+ dan ulangi.
  pause
  exit /b 1
)
python "%~dp0panel.py"
endlocal
exit /b
