@echo off
REM Produce every deliverable in one shot (for manual testing):
REM   1) internal evaluation single-file exe
REM   2) registered single-file exe
REM   3) registered installer (Inno Setup 6)
REM Any failing step aborts the chain (no half-built output).
REM NOTE: keep this file pure ASCII (cmd.exe reads .bat in OEM cp936 here).
setlocal
cd /d %~dp0

call build_internal.bat
if errorlevel 1 goto :fail

call build_exe.bat
if errorlevel 1 goto :fail

call build_setup.bat
if errorlevel 1 goto :fail

echo.
echo ============================================
echo  All done, artifacts in dist\ :
dir /b dist\*.exe
echo ============================================
endlocal
exit /b 0

:fail
echo.
echo [ABORT] the previous build step failed - see the output above.
endlocal
exit /b 1
