@echo off
cd /d "%~dp0"
echo Installing the Plain language...
python -m pip install --user .
if errorlevel 1 (
  echo pip install failed. Make sure Python 3.8 or newer is installed and on PATH.
  exit /b 1
)
echo Building the editor extension...
python tools\package_vsix.py
if errorlevel 1 (
  echo Could not build the extension package.
  exit /b 1
)
set VSIX=
for %%f in (dist\*.vsix) do set VSIX=%%f
if "%VSIX%"=="" (
  echo No .vsix file was found in dist after building.
  exit /b 1
)
set INSTALLED=0
where code >nul 2>nul
if not errorlevel 1 (
  code --install-extension "%VSIX%"
  set INSTALLED=1
)
where cursor >nul 2>nul
if not errorlevel 1 (
  cursor --install-extension "%VSIX%"
  set INSTALLED=1
)
if "%INSTALLED%"=="0" (
  echo VS Code and Cursor were not found on PATH.
  echo To install by hand: open the Extensions view, click ... and choose
  echo Install from VSIX, then pick %VSIX%
)
echo Done. Try it: plain run examples\hello.pln
