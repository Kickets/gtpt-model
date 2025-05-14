@echo off
cd /d "C:\path\to\your\gtpt-model"

REM Get timestamp
for /f %%i in ('powershell -command "Get-Date -Format yyyy-MM-dd_HH:mm:ss"') do set timestamp=%%i

git add .
git commit -m "Auto-sync: %timestamp%"
git push origin main