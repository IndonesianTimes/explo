@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: ===== ROOT / DIR =====
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "TOOLS=%ROOT%\tools"
set "OUT=%ROOT%\out"
set "TMP=%ROOT%\tmp"
if not exist "%OUT%" mkdir "%OUT%"
if not exist "%TMP%" mkdir "%TMP%"
if not exist "%OUT%\wpscan\raw" mkdir "%OUT%\wpscan\raw"
if not exist "%OUT%\logs" mkdir "%OUT%\logs"
set "LOG=%OUT%\logs\wp_scan.log"

:: ===== LOG helper (aman di dalam blok) =====
:log
setlocal EnableDelayedExpansion
set "msg="
:log_more
if "%~1"=="" goto log_done
set "msg=!msg! %~1"
shift
goto log_more
:log_done
set "msg=!msg:~1!"
set "T=%time: =0%"
echo [!T:~0,8!] !msg!
>> "%LOG%" echo [!T:~0,8!] !msg!
endlocal & goto :eof

call :log [i] ROOT=%ROOT%
call :log [i] TOOLS=%TOOLS%
call :log [i] LOG=%LOG%

:: ===== TUNING =====
set "SHARDS=6"                       :: jumlah proses paralel
set "WPSCAN_ENUM=ap,at,tt,cb"        :: plugin, theme, timthumb, config backups
set "UA_OPT=--random-user-agent"
set "TLS_OPT=--disable-tls-checks"
set "NO_BANNER=--no-banner"
set "FORMAT=--format json"

:: ===== DETEKSI WPScan =====
set "WPSCAN_CMD="
set "WPSCAN_PRE="
call :log [+] detect WPScan...

call :try_wpscan_cmd "%TOOLS%\wpscan\wpscan.exe"
if not defined WPSCAN_CMD call :try_wpscan_cmd "%TOOLS%\wpscan\wpscan.bat"
if not defined WPSCAN_CMD call :try_wpscan_cmd "%TOOLS%\wpscan.exe"
if not defined WPSCAN_CMD call :try_wpscan_cmd "%TOOLS%\wpscan.bat"
if not defined WPSCAN_CMD for /f "delims=" %%I in ('where wpscan.exe 2^>nul') do if not defined WPSCAN_CMD call :try_wpscan_cmd "%%~fI"
if not defined WPSCAN_CMD for /f "delims=" %%I in ('where wpscan.bat 2^>nul') do if not defined WPSCAN_CMD call :try_wpscan_cmd "%%~fI"
if not defined WPSCAN_CMD for /f "delims=" %%R in ('where ruby 2^>nul') do if not defined WPSCAN_CMD call :try_ruby_s_wpscan "%%~fR"

if not defined WPSCAN_CMD goto :wpscan_help
call :log [i] wpscan="%WPSCAN_CMD%" %WPSCAN_PRE%

:: ===== INPUT WORDPRESS LIST =====
set "WP_LIST=%OUT%\cms\wordpress.txt"
if exist "%ROOT%\wordpress.txt"         set "WP_LIST=%ROOT%\wordpress.txt"
if exist "%ROOT%\targets\wordpress.txt" set "WP_LIST=%ROOT%\targets\wordpress.txt"

if not exist "%WP_LIST%" (
  call :log [!] wordpress list not found: %WP_LIST%
  call :log [!] expected: out\cms\wordpress.txt (from cms_sort.bat)
  goto :eof
)
call :log [i] list=%WP_LIST%

:: ===== NORMALIZE & SHARD =====
del /q "%TMP%\wp_urls.txt" "%TMP%\wp_urls_shard_*.txt" "%TMP%\done_wpscan_*.flag" 2>nul
type "%WP_LIST%" | findstr /r /v "^\s*$" | sort /unique > "%TMP%\wp_urls.txt"

for /f %%A in ('^< "%TMP%\wp_urls.txt" find /c /v ""') do set "TOTAL=%%A"
if "%TOTAL%"=="0" ( call :log [!] list kosong & goto :eof )
call :log [i] total_targets=%TOTAL%
title WPScan 0/%TOTAL% (0%%)

call :log [+] sharding to %SHARDS%...
for /l %%S in (1,1,%SHARDS%) do ( type nul > "%TMP%\wp_urls_shard_%%S.txt" )
set /a idx=0
for /f "usebackq delims=" %%U in ("%TMP%\wp_urls.txt") do (
  set /a idx+=1
  set /a mod=(!idx!-1)%%%SHARDS%+1
  >>"%TMP%\wp_urls_shard_!mod!.txt" echo %%U
)

:: ===== PARALLEL WPSCAN =====
call :log [+] start parallel scans...
for /l %%S in (1,1,%SHARDS%) do (
  start "" /b cmd /c call "%~f0" :run_shard %%S
)

:: ===== MONITOR PROGRESS UI =====
call :log [i] monitoring progress...
call :now_sec STARTSEC
set "LASTDONE=0"
set "SPIN=0"

:progress_loop
for /f %%A in ('dir /b "%OUT%\wpscan\raw\*.json" 2^>nul ^| find /v /c ""') do set "DONE=%%A"
if not defined DONE set "DONE=0"

set /a PCT=(DONE*100)/TOTAL
set /a FILLED=(PCT*40)/100
set /a EMPTY=40-FILLED
call :rep "#" !FILLED! BARF
call :rep "." !EMPTY!  BARE
call :spinner SPCHR

:: ETA & speed
call :now_sec NOW
set /a ELAP=NOW-STARTSEC
if !ELAP! LSS 1 set ELAP=1
set /a SPEED=(DONE*60)/ELAP
if !SPEED! LSS 1 set SPEED=1
set /a REMAIN=TOTAL-DONE
set /a ETASEC=(REMAIN*60)/SPEED
call :fmt_mmss !ETASEC! ETA

title WPScan !DONE!/!TOTAL! (!PCT!%%)
call :log [>] !SPCHR! [!BARF!!BARE!] !DONE!/!TOTAL! ^(!PCT!%%^) | ~!SPEED!/min | ETA !ETA!

if "!DONE!"=="!TOTAL!" goto progress_done
ping -n 2 127.0.0.1 >nul
goto progress_loop

:progress_done
call :log [+] all shards finished.

:: ===== MERGE & RINGKAS =====
call :log [+] merge & filter High/Critical upload/takeover/RCE...
powershell -ExecutionPolicy Bypass -File "%ROOT%\scripts\wpscan-merge.ps1" -Raw "%OUT%\wpscan\raw" -Out "%OUT%\wpscan"

call :log [=] done. see: out\wpscan\findings.jsonl / findings.txt / summary.txt
goto :eof


:: ===== SUB-ROUTINE: jalankan 1 shard =====
:run_shard
setlocal EnableDelayedExpansion
set "SID=%~2"
set "FILE=%TMP%\wp_urls_shard_%SID%.txt"
if not exist "%FILE%" endlocal & goto :eof
call :log [S!SID!] start

for /f "usebackq delims=" %%U in ("%FILE%") do (
  set "URL=%%U"
  set "FN=!URL:https://=!"
  set "FN=!FN:http://=!"
  set "FN=!FN:/=_!"
  set "FN=!FN::=_!"
  set "OUTJSON=%OUT%\wpscan\raw\%SID%_!FN!.json"

  set "EXTRA_OPTS="
  if defined WPVULNDB_API_TOKEN set "EXTRA_OPTS=--api-token %WPVULNDB_API_TOKEN%"

  call "%WPSCAN_CMD%" %WPSCAN_PRE% --url "!URL!" --enumerate %WPSCAN_ENUM% %FORMAT% -o "!OUTJSON!" ^
    %NO_BANNER% %TLS_OPT% %UA_OPT% %EXTRA_OPTS% 1>nul 2>nul
)

type nul > "%TMP%\done_wpscan_%SID%.flag"
call :log [S!SID!] done
endlocal & goto :eof


:: ===== HELPER: deteksi wpscan =====
:try_wpscan_cmd
setlocal
set "C=%~1"
if not exist "%C%" (endlocal & goto :eof)
"%C%" --version >nul 2>nul
if errorlevel 1 (endlocal & goto :eof)
endlocal & set "WPSCAN_CMD=%~1" & set "WPSCAN_PRE=" & goto :eof

:try_ruby_s_wpscan
setlocal
set "RUBY=%~1"
if not exist "%RUBY%" (endlocal & goto :eof)
"%RUBY%" -S wpscan --version >nul 2>nul
if errorlevel 1 (endlocal & goto :eof)
endlocal & set "WPSCAN_CMD=%~1" & set "WPSCAN_PRE=-S wpscan" & goto :eof


:: ===== HELPER: repeat char N times -> var =====
:rep
setlocal EnableDelayedExpansion
set "char=%~1"
set "count=%~2"
set "out="
for /L %%i in (1,1,!count!) do set "out=!out!!char!"
endlocal & set "%~3=%out%" & goto :eof

:: ===== HELPER: spinner =====
:spinner
set /a SPIN=(SPIN+1)%%4
if %SPIN%==0 (set "SPCHR=-") else if %SPIN%==1 (set "SPCHR=\") else if %SPIN%==2 (set "SPCHR=|") else set "SPCHR=/"
set "%~1=%SPCHR%"
goto :eof

:: ===== HELPER: time seconds since midnight =====
:now_sec
setlocal
set "T=%time: =0%"
set /a S=(1%T:~0,2%-100)*3600 + (1%T:~3,2%-100)*60 + (1%T:~6,2%-100)
endlocal & set "%~1=%S%" & goto :eof

:: ===== HELPER: format mm:ss =====
:fmt_mmss
setlocal
set /a MM=(%~1)/60, SS=(%~1)%%60
if %MM% LSS 10 set "MM=0%MM%"
if %SS% LSS 10 set "SS=0%SS%"
endlocal & set "%~2=%MM%:%SS%" & goto :eof


:: ===== HELP =====
:wpscan_help
call :log [!] WPScan belum terdeteksi untuk shell ini.
call :log [!] Tips: buka CMD baru, atau jalankan: ridk enable
call :log [!] Tes manual:  ruby -S wpscan --version
goto :eof
