@echo off
REM ============================================================
REM  WLKMN Studio - one-click setup + launch (Windows)
REM  Double-click this file. It installs anything missing
REM  (Python + adb) and then opens the app.
REM ============================================================
cd /d "%~dp0"
title WLKMN Studio

REM Use adb.exe if it's sitting in this folder (otherwise the app downloads adb itself).
if exist "%~dp0adb.exe" set "WLKMN_ADB=%~dp0adb.exe"

REM --- Find Python (py launcher, then python) ---
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY goto getpython

REM --- Set up + launch ---
echo.
echo   Getting WLKMN Studio ready (first time only, please wait)...
echo.
%PY% -m pip install -q -r requirements.txt
if errorlevel 1 goto pipfail
echo.
echo   Opening WLKMN Studio...
echo.
%PY% run.py
goto end

:getpython
echo.
echo   Python isn't installed yet - I'll install it for you.
echo.
where winget >nul 2>nul
if errorlevel 1 goto nowinget
winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
echo.
echo   ============================================================
echo      Done installing Python!
echo      Now just DOUBLE-CLICK START.bat ONE more time to open the app.
echo   ============================================================
echo.
pause
goto end

:nowinget
echo   I couldn't install Python automatically on this PC.
echo   Please install it from:   https://www.python.org/downloads/
echo   and TICK "Add python.exe to PATH" in the installer, then
echo   double-click START.bat again.
echo.
pause
goto end

:pipfail
echo.
echo   *** Setup couldn't finish - check your internet connection, then try again. ***
echo.
pause

:end
