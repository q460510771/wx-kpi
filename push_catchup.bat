@echo off
rem Evening catch-up: if any commits are still ahead of origin/main (e.g. the 18:00
rem push failed due to a transient github outage), re-push them. Offline-safe: uses the
rem local remote-tracking ref, so it does nothing when origin/main is already up to date.
setlocal
set GITDIR=C:\Users\guber\.qwenworkcn\bin\git\mingw64\bin
set GIT=%GITDIR%\git.exe
set PATH=%GITDIR%;%PATH%
set GIT_TERMINAL_PROMPT=0
set LOG=D:\wx-kpi\pipeline\push.log
cd /d D:\wx-kpi
echo ==== catchup %date% %time% ==== >> "%LOG%"
set AHEAD=0
for /f %%c in ('"%GIT%" rev-list --count origin/main..HEAD 2^>nul') do set AHEAD=%%c
if "%AHEAD%"=="0" (
  echo catchup: nothing to push, origin/main up to date >> "%LOG%"
  exit /b 0
)
echo catchup: %AHEAD% commit^(s^) ahead of origin/main, re-pushing >> "%LOG%"
call D:\wx-kpi\push_retry.bat
exit /b %errorlevel%
