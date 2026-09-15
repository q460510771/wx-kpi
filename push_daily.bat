@echo off
rem Daily rebuild + push of wx-kpi dashboard to GitHub Pages (main branch).
set PY=D:\Python\python.exe
set PYTHONIOENCODING=utf-8
set GIT_TERMINAL_PROMPT=0
set LOG=D:\wx-kpi\pipeline\push.log
echo ==== %date% %time% ==== >> "%LOG%"
cd /d D:\wx-kpi\pipeline
"%PY%" build_data.py D:\wx-kpi\pipeline >> "%LOG%" 2>&1
"%PY%" build_html.py D:\wx-kpi\pipeline D:\wx-kpi\index.html >> "%LOG%" 2>&1
cd /d D:\wx-kpi
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set DTH=%%i
git add index.html pipeline >> "%LOG%" 2>&1
git commit -m "auto update %DTH% 18:00" >> "%LOG%" 2>&1
git -c credential.helper= -c "credential.helper=store --file=C:/Users/guber/.wx-kpi-creds" push origin main >> "%LOG%" 2>&1
echo push exit=%errorlevel% >> "%LOG%"
