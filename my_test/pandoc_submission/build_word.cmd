@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_word.ps1"
if errorlevel 1 exit /b %errorlevel%
endlocal
