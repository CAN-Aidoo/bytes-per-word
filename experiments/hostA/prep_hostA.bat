@echo off
rem Host A grid session prep (run this BEFORE run_grid_hostA.bat, from a plain Command Prompt, charger connected).
rem 1. stops WSL and waits until its processes are gone
rem 2. fetches the pinned development model if it is missing, and checks its SHA-256 (experiments\MODELS.csv)
rem 3. runs the real pre-flight (grid_hostA.py --check-only) so you see every remaining item
rem It does NOT close the Claude app, plug in the charger, restart the laptop or change power mode: those are yours.
rem The model is downloaded only when it is missing, from the revision pinned in PROTOCOL 3.5 / MODELS.csv.
setlocal enableextensions
set REPO=%USERPROFILE%\bytes-per-word
set MODELS=%USERPROFILE%\hostA-downloads
set DEVFILE=smollm2-360m-instruct-q8_0.gguf
set DEVREV=593b5a2e04c8f3e4ee880263f93e0bd2901ad47f
set DEVSHA=48ab3034d0dd401fbc721eb1df3217902fee7dab9078992d66431f09b7750201
set DEVBYTES=386404992
set DEVURL=https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF/resolve/%DEVREV%/%DEVFILE%

cd /d "%REPO%" || (echo Repository not found at %REPO% & pause & exit /b 1)
if not exist "%MODELS%" mkdir "%MODELS%"

echo === 1. WSL ===
wsl --shutdown >nul 2>&1
set /a TRIES=0
:waitwsl
tasklist 2>nul | findstr /i /b /c:"vmmem" /c:"wsl.exe" >nul
if errorlevel 1 goto wsldone
set /a TRIES+=1
if %TRIES% GEQ 30 goto wslstuck
timeout /t 2 /nobreak >nul
goto waitwsl
:wslstuck
echo WSL processes are still running after 60 s. Trying to end them; this needs a Command Prompt run as administrator.
taskkill /f /im wsl.exe >nul 2>&1
taskkill /f /im vmmem.exe >nul 2>&1
taskkill /f /im vmmemWSL.exe >nul 2>&1
timeout /t 3 /nobreak >nul
tasklist 2>nul | findstr /i /b /c:"vmmem" /c:"wsl.exe" >nul
if errorlevel 1 goto wsldone
echo WSL is still running. Restart the laptop, then run this file again before opening any Ubuntu or WSL terminal.
goto model
:wsldone
echo WSL is stopped.

:model
echo.
echo === 2. Development model ===
if exist "%MODELS%\%DEVFILE%" (
  echo %DEVFILE% is already in %MODELS%. Checking its hash...
  call :checkhash "%MODELS%\%DEVFILE%"
  if errorlevel 1 (
    echo The existing file does not match the recorded hash. Move or delete it, then run this file again.
    goto preflight
  )
  echo Hash matches.
  goto preflight
)
echo %DEVFILE% is missing. Downloading the pinned revision %DEVREV%, about 386 MB...
curl.exe -L --fail -o "%MODELS%\%DEVFILE%.part" "%DEVURL%"
if errorlevel 1 (
  echo Download failed. Check the internet connection and run this file again.
  del "%MODELS%\%DEVFILE%.part" >nul 2>&1
  goto preflight
)
call :checkhash "%MODELS%\%DEVFILE%.part"
if errorlevel 1 (
  echo Hash or size does not match the recorded values, so the file was NOT kept.
  del "%MODELS%\%DEVFILE%.part" >nul 2>&1
  goto preflight
)
move /y "%MODELS%\%DEVFILE%.part" "%MODELS%\%DEVFILE%" >nul
echo Downloaded and verified: %MODELS%\%DEVFILE%

:preflight
echo.
echo === 3. Pre-flight ===
python experiments\grid_hostA.py --check-only
echo.
echo If the list above says NOT STARTING, fix each item, then run run_grid_hostA.bat. Items it can name: Claude app, charger, WSL, model.
pause
exit /b 0

:checkhash
rem %1 = file. Returns errorlevel 0 when size and SHA-256 match the recorded values.
set GOTHASH=
for %%F in (%1) do set GOTSIZE=%%~zF
if not "%GOTSIZE%"=="%DEVBYTES%" (echo Size is %GOTSIZE%, expected %DEVBYTES%. & exit /b 1)
for /f "skip=1 tokens=* delims=" %%H in ('certutil -hashfile %1 SHA256') do if not defined GOTHASH set "GOTHASH=%%H"
set "GOTHASH=%GOTHASH: =%"
if /i "%GOTHASH%"=="%DEVSHA%" exit /b 0
echo SHA-256 is %GOTHASH%, expected %DEVSHA%.
exit /b 1
