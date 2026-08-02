@echo off
setlocal
rem EUC launcher, browser variant: finds an installed R (no RStudio needed)
rem and starts the Shiny app in the default browser. Stop with Ctrl+C or by
rem closing this console window. For a native-window feel see
rem run_app_desktop.bat.

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

set "APPDIR=%~dp0"
set "APPDIR=%APPDIR:\=/%"
echo Starting GLM Workbench (R Shiny) with %RSCRIPT% ...
"%RSCRIPT%" -e "shiny::runApp('%APPDIR%.', launch.browser = TRUE)"
pause
