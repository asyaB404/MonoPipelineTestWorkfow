@echo off
setlocal EnableExtensions

if not "%~1"=="" goto invalid_args
if not exist "functiontest-upload-wrapper.ps1" (
  echo [ERROR] missing functiontest-upload-wrapper.ps1 in the current run directory.
  echo [ERROR] run prepare_upload_wrapper.py from this run directory first.
  exit /b 1
)

rem The current directory is the run directory. Do not pass a Chinese JSON
rem path on the command line; the UTF-8 BOM wrapper resolves it internally.
powershell -NoProfile -ExecutionPolicy Bypass -File "functiontest-upload-wrapper.ps1"
if errorlevel 1 exit /b 1
exit /b 0

:invalid_args
echo [ERROR] report_functiontest.bat accepts no JSON path. Run it from the current run directory.
exit /b 1
