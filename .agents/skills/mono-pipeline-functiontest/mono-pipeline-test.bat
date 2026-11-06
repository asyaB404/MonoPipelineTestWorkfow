@echo off
rem 创建日期：2026-10-26；作者：Cyou。
rem 功能：薄 Windows 入口；参数：原样传入包内 CLI，显式本机 MONO_PIPELINE_PYTHON 或 py -3。
rem 不安装环境、不定位维护机 Python、不编译/构建或启动游戏；需要 CPython 3.10+。
setlocal DisableDelayedExpansion
if not defined MONO_PIPELINE_PYTHON goto local_launcher
if not exist "%MONO_PIPELINE_PYTHON%" goto missing_python
"%MONO_PIPELINE_PYTHON%" -I -B "%~dp0scripts\cli.py" %*
exit /b %errorlevel%
:local_launcher
where py >nul 2>&1
if errorlevel 1 goto missing_python
py -3 -I -B "%~dp0scripts\cli.py" %*
exit /b %errorlevel%
:missing_python
echo A local CPython 3.10+ is required. Set MONO_PIPELINE_PYTHON to an existing python.exe or provide the local py launcher.
exit /b 3
