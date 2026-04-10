@echo off
set "SCRIPT_DIR=%~dp0"
powershell -NoLogo -ExecutionPolicy Bypass -File "%SCRIPT_DIR%launch_dashboard.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" echo Script exited with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
