@echo off
REM ============================================================
REM  WLKMN Studio - one-click setup + launch (Windows)
REM  Double-click this file. First run installs what it needs,
REM  then it opens the app. Later runs just open the app.
REM ============================================================
setlocal
cd /d "%~dp0"
title WLKMN Studio

REM Use adb.exe if you dropped it in this folder (no PATH setup needed).
if exist "%~dp0adb.exe" set "WLKMN_ADB=%~dp0adb.exe"

REM Find Python (py launcher, else python).
set "PY=py"
where py >nul 2>nul || set "PY=python"
where %PY% >nul 2>nul || goto :nopython

echo(
echo   Setting up WLKMN Studio (first run downloads a few things)...
echo(
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto :pipfail

echo(
echo   Launching WLKMN Studio...
echo(
%PY% run.py
goto :end

:nopython
echo(
echo   *** Python was not found. ***
echo   Install it from https://www.python.org/downloads/ and, in the installer,
echo   TICK the box "Add python.exe to PATH". Then double-click START.bat again.
goto :end

:pipfail
echo(
echo   *** Setup failed. ***
echo   Make sure you are connected to the internet and Python is installed
echo   (from python.org, with "Add python.exe to PATH" ticked), then try again.

:end
echo(
pause
