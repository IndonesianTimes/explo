@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "TOOLS=%ROOT%\tools"
set "OUT=%ROOT%\out"
set "TMP=%ROOT%\tmp"
if not exist "%OUT%" mkdir "%OUT%"

:: autodetect httpx (flat/subfolder)
set "HTTPX=%TOOLS%\httpx\httpx.exe"
if not exist "%HTTPX%" set "HTTPX=%TOOLS%\httpx.exe"
if not exist "%HTTPX%" echo [!] httpx.exe not found & goto :eof

:: cari subs.txt
set "SUBS=%ROOT%\subs.txt"
if not exist "%SUBS%" set "SUBS=%ROOT%\output\subs.txt"
if not exist "%SUBS%" set "SUBS=%ROOT%\out\subs.txt"
if not exist "%SUBS%" echo [!] subs.txt not found & goto :eof

echo [+] httpx tech-detect...
"%HTTPX%" -l "%SUBS%" -json -tech-detect -title -status-code -follow-redirects > "%OUT%\httpx.jsonl"

echo [+] CMS sort...
powershell -ExecutionPolicy Bypass -File "%ROOT%\scripts\cms-sort.ps1" -In "%OUT%\httpx.jsonl" -Out "%OUT%\cms"

echo [=] See:
echo     %OUT%\cms\master.csv
echo     %OUT%\cms\*.csv / *.txt
echo     %OUT%\cms\summary.txt
