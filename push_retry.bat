@echo off
rem Robust git push for wx-kpi: long retry window + anti-reset http tuning.
rem Self-contained. Called by push_daily.bat after commit, and by push_catchup.bat.
rem Pushes whatever commits are ahead of origin/main, so it also flushes any
rem previously-failed days (eventually consistent). Exit 0 = pushed/up-to-date, 1 = failed.
setlocal
set GITDIR=C:\Users\guber\.qwenworkcn\bin\git\mingw64\bin
set GIT=%GITDIR%\git.exe
set PATH=%GITDIR%;%PATH%
set GIT_TERMINAL_PROMPT=0
set LOG=D:\wx-kpi\pipeline\push.log
set CREDS=C:/Users/guber/.wx-kpi-creds
cd /d D:\wx-kpi
set PUSHOK=0
rem 20 attempts x 60s wait (~27 min window incl. connect timeouts) to ride out transient github outages.
for /L %%n in (1,1,20) do (
  "%GIT%" -c credential.helper= -c "credential.helper=store --file=%CREDS%" -c http.version=HTTP/1.1 -c http.postBuffer=524288000 -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=60 push origin main >> "%LOG%" 2>&1
  if not errorlevel 1 (
    echo push attempt %%n OK >> "%LOG%"
    set PUSHOK=1
    goto :afterpush
  ) else (
    echo push attempt %%n failed, retrying >> "%LOG%"
    timeout /t 60 /nobreak > nul
  )
)
:afterpush
echo push done PUSHOK=%PUSHOK% >> "%LOG%"
if "%PUSHOK%"=="1" exit /b 0
exit /b 1
