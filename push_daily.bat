@echo off
rem Daily rebuild + push of wx-kpi dashboard to GitHub Pages (main branch).
rem NOTE: scheduled-task env has no git in PATH -> use full path to portable git.
set PY=D:\Python\python.exe
set GITDIR=C:\Users\guber\.qwenworkcn\bin\git\mingw64\bin
set GIT=%GITDIR%\git.exe
set PATH=%GITDIR%;%PATH%
set PYTHONIOENCODING=utf-8
set GIT_TERMINAL_PROMPT=0
set LOG=D:\wx-kpi\pipeline\push.log
echo ==== %date% %time% ==== >> "%LOG%"
cd /d D:\wx-kpi\pipeline
"%PY%" build_data.py D:\wx-kpi\pipeline >> "%LOG%" 2>&1
"%PY%" build_html.py D:\wx-kpi\pipeline D:\wx-kpi\index.html >> "%LOG%" 2>&1
cd /d D:\wx-kpi
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set DTH=%%i
"%GIT%" add index.html pipeline >> "%LOG%" 2>&1
"%GIT%" commit -m "auto update %DTH% 18:00" >> "%LOG%" 2>&1
set PUSHOK=0
for /L %%n in (1,1,4) do (
  "%GIT%" -c credential.helper= -c "credential.helper=store --file=C:/Users/guber/.wx-kpi-creds" push origin main >> "%LOG%" 2>&1
  if not errorlevel 1 (
    echo push attempt %%n OK >> "%LOG%"
    set PUSHOK=1
    goto :afterpush
  ) else (
    echo push attempt %%n failed, retrying >> "%LOG%"
    timeout /t 30 /nobreak > nul
  )
)
:afterpush
echo push done PUSHOK=%PUSHOK% >> "%LOG%"
if "%PUSHOK%"=="0" exit /b 1
exit /b 0
