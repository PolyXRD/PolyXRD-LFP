@echo off
REM Build PolyXRD LFP [registered edition] single-file exe (payload of the installer).
REM Requires numpy / scipy / matplotlib / PySide6 / PyInstaller.
REM
REM Output:
REM   dist\PolyXRD-LFP-vX.Y.Z.exe   registered edition (with registration module)
REM
REM That exe is an INTERMEDIATE payload: build_setup.bat wraps it into the
REM installer, then tidy_dist.bat deletes it. dist\ must end up holding exactly
REM two files - the internal evaluation exe and the Setup installer.
REM
REM Internal evaluation build: use build_internal.bat instead.
REM
REM NOTE: keep this file pure ASCII. cmd.exe reads .bat in the OEM codepage
REM (GBK / cp936 on this machine); UTF-8 Chinese text corrupts the parser and
REM makes cmd execute garbage fragments instead of the intended lines.
setlocal
cd /d %~dp0

REM Unbuffered output: a block-buffered crash log loses its last chunk.
set PYTHONUNBUFFERED=1
REM Interpreter priority: project Python 3.10 (ships tkinter, required by the
REM PyInstaller Splash) -> bundled WorkBuddy 3.13 -> whatever is on PATH.
set PY=D:\Project\XRD\python310\python.exe
if not exist "%PY%" set PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe
if not exist "%PY%" set PY=python

set VERTMP=%TEMP%\pxrd_lfp_ver.txt
"%PY%" -c "from lfp.version import __version__; print(__version__)" > "%VERTMP%" 2>nul
set VER=
set /p VER=<"%VERTMP%"
del "%VERTMP%" >nul 2>nul
if "%VER%"=="" (
    echo [ERROR] cannot read version from lfp/version.py
    exit /b 1
)

echo Building PolyXRD LFP ^(registered^) v%VER% ...
"%PY%" -m PyInstaller --noconfirm --clean PolyXRD-LFP.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed
    exit /b 1
)
if not exist "dist\PolyXRD-LFP-v%VER%.exe" (
    echo [ERROR] dist\PolyXRD-LFP-v%VER%.exe not produced
    exit /b 1
)

echo.
echo Done ^(registered payload^):
echo   dist\PolyXRD-LFP-v%VER%.exe  ^(consumed by build_setup.bat^)
endlocal
