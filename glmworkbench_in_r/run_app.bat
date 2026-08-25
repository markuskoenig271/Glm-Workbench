@echo off
setlocal
rem EUC launcher, browser variant: finds an installed R (no RStudio needed)
rem and starts the glmworkbenchR Shiny app in the default browser. Stop with
rem Ctrl+C or by closing this console window. For a native-window feel see
rem run_app_desktop.bat.
rem
rem Uses the INSTALLED glmworkbenchR package if present (devtools::install()),
rem otherwise loads the package straight from this source folder via pkgload.

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

set "PKGDIR=%~dp0"
set "PKGDIR=%PKGDIR:\=/%"
echo Starting GLM Workbench (glmworkbenchR) with %RSCRIPT% ...
"%RSCRIPT%" -e "if (!requireNamespace('glmworkbenchR', quietly = TRUE)) pkgload::load_all('%PKGDIR%.', quiet = TRUE); print(glmworkbenchR::run_app(data_dir = '%PKGDIR%../data/raw', options = list(launch.browser = TRUE)))"
pause
