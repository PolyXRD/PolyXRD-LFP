@echo off
REM Compile the Inno Setup 6 installer.
REM Prerequisite: run build_exe.bat first (produces dist\PolyXRD-LFP-vX.Y.Z.exe).
REM Output: dist\PolyXRD-LFP-vX.Y.Z-Setup.exe
REM NOTE: keep this file pure ASCII (cmd.exe reads .bat in OEM cp936 here).
setlocal
cd /d %~dp0

set PYTHONUNBUFFERED=1
set PY=D:\Project\XRD\python310\python.exe
if not exist "%PY%" set PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe
if not exist "%PY%" set PY=python

set VERTMP=%TEMP%\pxrd_lfp_ver.txt
"%PY%" -c "from lfp.version import __version__; print(__version__)" > "%VERTMP%" 2>nul
set RAW=
set /p RAW=<"%VERTMP%"
del "%VERTMP%" >nul 2>nul
if "%RAW%"=="" (
    echo [ERROR] cannot read version from lfp/version.py
    exit /b 1
)
set VER=v%RAW%

if not exist "dist\PolyXRD-LFP-%VER%.exe" (
    echo [ERROR] missing dist\PolyXRD-LFP-%VER%.exe - run build_exe.bat first
    exit /b 1
)

REM Locate ISCC.exe. Some shells/sandboxes do not export %ProgramFiles(x86)%,
REM hence the explicit literal fallbacks.
set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" for /f "delims=" %%i in ('where ISCC.exe 2^>nul') do set ISCC=%%i
if not exist "%ISCC%" (
    echo [ERROR] Inno Setup 6 ISCC.exe not found
    exit /b 1
)

echo Building installer with Inno Setup 6 ^(/%VER%/^) ...
"%ISCC%" /DAPP_VER=%VER% installer\PolyXRD-LFP.iss
if errorlevel 1 (
    echo [ERROR] Inno Setup compilation failed
    exit /b 1
)
if not exist "dist\PolyXRD-LFP-%VER%-Setup.exe" (
    echo [ERROR] dist\PolyXRD-LFP-%VER%-Setup.exe not produced
    exit /b 1
)

echo.
echo Done:
echo   dist\PolyXRD-LFP-%VER%-Setup.exe
endlocal
