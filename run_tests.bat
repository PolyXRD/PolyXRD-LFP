@echo off
REM Run the test suite, then clean up what it produced.
REM The pytest exit code is preserved, so failures are never masked by the cleanup.
REM
REM Usage:  run_tests.bat          full suite
REM         run_tests.bat fast     skip slow cases (-m "not slow")
REM         run_tests.bat slow     only slow cases
REM
REM Cleanup rules live in tools\clean_after_test.py (run it with --dry to preview).
REM NOTE: keep this file pure ASCII (cmd.exe reads .bat in OEM cp936 here).
setlocal
cd /d %~dp0

set PYTHONUNBUFFERED=1
set PY=D:\Project\XRD\python310\python.exe
if not exist "%PY%" set PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe
if not exist "%PY%" set PY=python

set ARGS=tests -q
if /i "%~1"=="fast" set ARGS=tests -q -m "not slow"
if /i "%~1"=="slow" set ARGS=tests -q -m "slow"

echo [test] pytest %ARGS%
"%PY%" -m pytest %ARGS%
set RC=%ERRORLEVEL%

echo.
echo [test] cleaning artifacts ...
"%PY%" tools\clean_after_test.py

echo.
if "%RC%"=="0" (
    echo [test] PASSED - artifacts cleaned
) else (
    echo [test] FAILED rc=%RC% - artifacts cleaned
)
endlocal & exit /b %RC%
