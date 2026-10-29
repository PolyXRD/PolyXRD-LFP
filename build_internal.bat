@echo off
REM Build PolyXRD LFP [internal evaluation edition] single-file exe.
REM Deltas vs the registered build: the runtime hook overwrites the edition to
REM "internal", the registration module is excluded, the exe name carries
REM "-Internal" (see PolyXRD-LFP-Internal.spec).
REM
REM Output: dist\PolyXRD-LFP-Internal-vX.Y.Z.exe
REM
REM NOTE: keep this file pure ASCII (cmd.exe reads .bat in OEM cp936 here;
REM UTF-8 Chinese text corrupts parsing).
setlocal
cd /d %~dp0

set PYTHONUNBUFFERED=1
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

echo Building PolyXRD LFP ^(internal evaluation^) v%VER% ...
"%PY%" -m PyInstaller --noconfirm --clean PolyXRD-LFP-Internal.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed
    exit /b 1
)
if not exist "dist\PolyXRD-LFP-Internal-v%VER%.exe" (
    echo [ERROR] dist\PolyXRD-LFP-Internal-v%VER%.exe not produced
    exit /b 1
)

echo.
echo Done ^(internal evaluation^):
echo   dist\PolyXRD-LFP-Internal-v%VER%.exe
endlocal
