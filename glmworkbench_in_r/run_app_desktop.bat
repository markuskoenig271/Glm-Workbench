@echo off
setlocal
rem EUC launcher, desktop-window variant: starts the glmworkbenchR Shiny
rem server headless on a fixed port, then opens it in Edge/Chrome APP MODE
rem (own window, no tabs or address bar - looks like a native desktop app).
rem Closing that window shuts the R server down again.
rem
rem Uses the INSTALLED glmworkbenchR package if present (devtools::install()),
rem otherwise loads the package straight from this source folder via pkgload.

set "PORT=8613"

rem --- locate R (no RStudio needed): registry, then Program Files scan ------
set "RSCRIPT="
for /f "tokens=2,*" %%a in ('reg query "HKLM\SOFTWARE\R-core\R" /v InstallPath 2^>nul ^| find "InstallPath"') do set "RHOME=%%b"
if defined RHOME set "RSCRIPT=%RHOME%\bin\Rscript.exe"
if not defined RSCRIPT (
  for /d %%d in ("C:\Program Files\R\R-*") do set "RSCRIPT=%%d\bin\Rscript.exe"
)
if not exist "%RSCRIPT%" (
  echo Could not find an R installation. Install R, or edit this script to
  echo point RSCRIPT at your Rscript.exe ^(a bundled R-Portable works too^).
  pause
  exit /b 1
)

rem --- locate an app-mode capable browser: Edge first, then Chrome ----------
set "BROWSER="
for %%e in (
  "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
  "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
  "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
  "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
  "%LocalAppData%\Google\Chrome\Application\chrome.exe"
) do if not defined BROWSER if exist "%%~e" set "BROWSER=%%~e"
if not defined BROWSER (
  echo Neither Edge nor Chrome found - use run_app.bat ^(browser variant^) instead.
  pause
  exit /b 1
)

set "PKGDIR=%~dp0"
set "PKGDIR=%PKGDIR:\=/%"

echo Starting GLM Workbench server on port %PORT% ...
start "GLM Workbench R server" /min "%RSCRIPT%" -e "if (!requireNamespace('glmworkbenchR', quietly = TRUE)) pkgload::load_all('%PKGDIR%.', quiet = TRUE); print(glmworkbenchR::run_app(data_dir = '%PKGDIR%../data/raw', options = list(port = %PORT%, launch.browser = FALSE)))"

rem --- wait until the server answers (max ~30 s) ----------------------------
set /a TRIES=0
:waitloop
set /a TRIES+=1
curl -s -o nul http://127.0.0.1:%PORT%/ 2>nul
if %errorlevel%==0 goto ready
if %TRIES% geq 30 goto failed
timeout /t 1 /nobreak >nul
goto waitloop

:ready
echo Opening desktop window - closing it stops the app.
start "" /wait "%BROWSER%" --app=http://127.0.0.1:%PORT%/ --no-first-run --no-default-browser-check --user-data-dir="%TEMP%\glm-workbench-appmode"

echo Window closed - stopping the server ...
goto stopserver

:failed
echo Server did not come up within 30 seconds - stopping it again.
:stopserver
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force }"
exit /b 0
