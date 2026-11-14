@echo off
setlocal
cd /d "%~dp0"
where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo Windows PowerShell is required to launch UR Chart.
  pause
  exit /b 1
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch-ur-chart.ps1"
if errorlevel 1 (
  echo.
  echo UR Chart could not start. Review the error above.
  pause
  exit /b 1
)
endlocal
