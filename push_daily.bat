@echo off
rem Daily rebuild + push of wx-kpi dashboard to GitHub Pages (main branch).
rem v2: DingTalk fetch step added before WeChat build. Both sources feed
rem     pipeline/build_data.py -> data.json -> build_html.py -> index.html.
rem NOTE: scheduled-task env has no git in PATH -> use full path to portable git.
set PY=D:\Python\python.exe
set GITDIR=C:\Users\guber\.qwenworkcn\bin\git\mingw64\bin
set GIT=%GITDIR%\git.exe
set PATH=%GITDIR%;C:\Users\guber\.qwenworkcn\bin;%PATH%
set PYTHONIOENCODING=utf-8
set GIT_TERMINAL_PROMPT=0
set LOG=D:\wx-kpi\pipeline\push.log
echo ==== %date% %time% ==== >> "%LOG%"
cd /d D:\wx-kpi\pipeline
rem --- Step 1: GATE on today's DingTalk fetch ---
rem dws cannot run headless: auth is host-managed and the shim requires a live
rem QwenWork session (QODERWORK_SOURCE_CHAT_ID). The daily fetch was therefore
rem moved to a QwenWork cron (17:50) that calls dws directly and writes a success
rem marker via pipeline/merge_today.py. Here we only VERIFY that marker; if today's
rem fetch did not succeed we SKIP publishing entirely (no build/commit/push).
"%PY%" check_fetch_marker.py >> "%LOG%" 2>&1
if errorlevel 1 (
  echo push done PUSHOK=SKIP reason=dingtalk_fetch_not_ok >> "%LOG%"
  exit /b 1
)
echo dingtalk fetch marker OK >> "%LOG%"
rem --- Step 2: rebuild combined data.json (WeChat + DingTalk) ---
"%PY%" build_data.py D:\wx-kpi\pipeline >> "%LOG%" 2>&1
rem --- Step 3: regenerate index.html ---
"%PY%" build_html.py D:\wx-kpi\pipeline D:\wx-kpi\index.html >> "%LOG%" 2>&1
cd /d D:\wx-kpi
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set DTH=%%i
"%GIT%" add index.html pipeline >> "%LOG%" 2>&1
"%GIT%" commit -m "auto update %DTH% 18:00" >> "%LOG%" 2>&1
rem Delegate to push_retry.bat: long retry window (~27 min) + anti-reset http tuning,
rem so a transient github outage at 18:00 no longer causes a hard daily failure.
call D:\wx-kpi\push_retry.bat
set PUSHRC=%errorlevel%
if "%PUSHRC%"=="0" exit /b 0
exit /b 1
