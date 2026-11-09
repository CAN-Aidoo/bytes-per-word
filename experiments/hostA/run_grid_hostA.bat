@echo off
rem Host A confirmatory grid session (PROTOCOL 4.6; Host A rule of the 2026-11-08 deviation: launched by a batch file,
rem plain Command Prompt, Claude app and all other user programs closed, charger connected).
rem Copy this file to %USERPROFILE%\hostA-downloads\ and double-click it there, or run it from a plain Command Prompt.
setlocal
set REPO=%USERPROFILE%\bytes-per-word
set OPENBLAS_NUM_THREADS=6
cd /d "%REPO%" || (echo Repository not found at %REPO% & pause & exit /b 1)

echo === Pre-flight and RAM forecast (nothing is run yet) ===
py experiments\grid_hostA.py --check-only
if errorlevel 1 (
  echo.
  echo Pre-flight failed: fix the items above, then run this file again.
  pause
  exit /b 1
)
echo.
echo Pre-flight passed. The session starts in 60 seconds and runs for up to 3 hours.
echo Do not use the laptop until it finishes. Press Ctrl+C now to cancel.
timeout /t 60
py experiments\grid_hostA.py --max-hours 3
echo.
echo Session finished (exit code %errorlevel%). Results are in %REPO%\results\raw\A and results\RUNLOG.md.
echo Now reopen the Claude app and say: "grid session done".
pause
