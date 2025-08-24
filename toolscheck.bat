@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM === Lokasi dasar proyek ===
set "BASE=C:\Users\Admin\Desktop\explo"
set "TOOLS=%BASE%\tools"

REM === Target uji ringan ===
set "TEST_URL=https://primesai.co"

echo ================== TOOLS PATH CHECK ==================
echo BASE  = %BASE%
echo TOOLS = %TOOLS%
echo.

REM ---- subfinder
if exist "%TOOLS%\subfinder.exe" (
  echo [OK ] subfinder.exe ditemukan
  "%TOOLS%\subfinder.exe" -version 2>nul
) else ( echo [ERR] subfinder.exe TIDAK ditemukan di %TOOLS% )

REM ---- httpx
if exist "%TOOLS%\httpx.exe" (
  echo [OK ] httpx.exe ditemukan
  "%TOOLS%\httpx.exe" -version 2>nul
) else ( echo [ERR] httpx.exe TIDAK ditemukan di %TOOLS% )

REM ---- nuclei
if exist "%TOOLS%\nuclei.exe" (
  echo [OK ] nuclei.exe ditemukan
  "%TOOLS%\nuclei.exe" -version 2>nul
) else ( echo [ERR] nuclei.exe TIDAK ditemukan di %TOOLS% )

REM ---- perl / nikto
set "NIKTO_PL=%TOOLS%\nikto\program\nikto.pl"
where perl >nul 2>nul
if errorlevel 1 (
  echo [WARN] Perl tidak ada di PATH  -> install Strawberry Perl atau tambah ke PATH
) else (
  echo [OK ] Perl terdeteksi
  if exist "%NIKTO_PL%" (
    echo [OK ] nikto.pl ditemukan
    perl "%NIKTO_PL%" -Version 1>nul 2>nul && echo       nikto.pl bisa dieksekusi
  ) else (
    echo [ERR] nikto.pl tidak ditemukan di %NIKTO_PL%
  )
)

REM ---- ruby / whatweb / wpscan
where ruby >nul 2>nul
if errorlevel 1 (
  echo [WARN] Ruby tidak ada di PATH -> jalankan RubyInstaller lagi / tambah ke PATH
) else (
  for /f %%R in ('where ruby') do set "RUBYEXE=%%R"
  echo [OK ] Ruby: %RUBYEXE%
  set "WHATWEB=%TOOLS%\whatweb\whatweb"
  set "WPSCAN=%TOOLS%\wpscan\bin\wpscan"

  if exist "%WHATWEB%" (
    echo [OK ] whatweb ditemukan
    ruby "%WHATWEB%" --version 2>nul
  ) else ( echo [ERR] whatweb tidak ditemukan di %WHATWEB% )

  if exist "%WPSCAN%" (
    echo [OK ] wpscan ditemukan
    ruby "%WPSCAN%" --version 2>nul
  ) else ( echo [ERR] wpscan tidak ditemukan di %WPSCAN% )
)

echo.
echo ================== RUNTIME QUICK TEST ==================
echo Target uji: %TEST_URL%
echo (tes ini aman dan sangat ringan)
echo.

REM httpx quick
if exist "%TOOLS%\httpx.exe" (
  "%TOOLS%\httpx.exe" -target "%TEST_URL%" -status-code -title -tech-detect -timeout 8
)

REM nuclei quick (tanpa templates berat)
if exist "%TOOLS%\nuclei.exe" (
  "%TOOLS%\nuclei.exe" -u "%TEST_URL%" -id http-missing-security-headers -silent -ni 2>nul
)

REM whatweb quick
if defined RUBYEXE if exist "%WHATWEB%" (
  ruby "%WHATWEB%" "%TEST_URL%" 1>nul 2>nul && echo [OK ] whatweb jalan (output disembunyikan)
)

REM nikto quick
if exist "%NIKTO_PL%" (
  perl "%NIKTO_PL%" -h "%TEST_URL%" -ask no -nointeractive -timeout 10 1>nul 2>nul && echo [OK ] nikto jalan (output disembunyikan)
)

REM wpscan quick (help saja)
if defined RUBYEXE if exist "%WPSCAN%" (
  ruby "%WPSCAN%" --help 1>nul 2>nul && echo [OK ] wpscan jalan (help OK)
)

echo.
echo ===== Selesai cek tools. Perhatikan baris [ERR]/[WARN] di atas. =====
pause
endlocal
