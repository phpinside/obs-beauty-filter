@echo off
rem BeautyCam installer (ASCII-only on purpose: a UTF-8 .bat with CJK text
rem gets mis-parsed by cmd.exe under GBK code pages and breaks the script).
setlocal
title BeautyCam Setup

set "HERE=%~dp0"
set "DEST=%LOCALAPPDATA%\Programs\BeautyCam"
set "WORK=%TEMP%\BeautyCamSetup"

rem Layout A: single-file setup (payload.zip next to this script)
rem Layout B: portable zip    (BeautyCam\ folder next to this script)
if exist "%HERE%payload.zip" (
    echo [1/4] Extracting payload ...
    if exist "%WORK%" rd /s /q "%WORK%" 2>nul
    mkdir "%WORK%" 2>nul
    rem 用 Expand-Archive 而不是 tar：PATH 里的 tar 可能是 GNU tar（Git/MSYS 自带），
    rem 它会把 "C:\..." 当成远程主机，也不支持 zip。
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%HERE%payload.zip' -DestinationPath '%WORK%' -Force" >nul 2>nul
    if not exist "%WORK%\BeautyCam\BeautyCam.exe" (
        if exist "%SystemRoot%\System32\tar.exe" "%SystemRoot%\System32\tar.exe" -xf "%HERE%payload.zip" -C "%WORK%" >nul 2>nul
    )
    set "SRC=%WORK%\BeautyCam"
    set "EXTRA=%WORK%"
) else (
    set "SRC=%HERE%BeautyCam"
    set "EXTRA=%HERE%"
)

if not exist "%SRC%\BeautyCam.exe" (
    echo [ERROR] BeautyCam.exe not found.
    echo         Keep install.bat next to BeautyCam\ folder, or next to payload.zip.
    pause & exit /b 1
)

echo [2/4] Closing running instance ...
taskkill /f /im BeautyCam.exe >nul 2>nul

echo [3/4] Copying files to %DEST% ...
if exist "%DEST%" rd /s /q "%DEST%" 2>nul
xcopy /e /i /y "%SRC%" "%DEST%" >nul
if not exist "%DEST%\BeautyCam.exe" (
    echo [ERROR] Copy failed. Check permissions or free disk space.
    pause & exit /b 1
)
if exist "%EXTRA%\uninstall.bat" copy /y "%EXTRA%\uninstall.bat" "%DEST%\uninstall.bat" >nul 2>nul
if exist "%EXTRA%\README.md" copy /y "%EXTRA%\README.md" "%DEST%\README.md" >nul 2>nul

echo [4/4] Creating shortcuts and uninstall entry ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $d=[Environment]::GetFolderPath('Desktop'); $l=$ws.CreateShortcut($d+'\BeautyCam.lnk'); $l.TargetPath='%DEST%\BeautyCam.exe'; $l.WorkingDirectory='%DEST%'; $l.Description='BeautyCam'; $l.Save(); $sm=Join-Path ([Environment]::GetFolderPath('Programs')) 'BeautyCam'; New-Item -ItemType Directory -Force -Path $sm | Out-Null; $l2=$ws.CreateShortcut((Join-Path $sm 'BeautyCam.lnk')); $l2.TargetPath='%DEST%\BeautyCam.exe'; $l2.WorkingDirectory='%DEST%'; $l2.Save()" >nul 2>nul

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" /v DisplayName /t REG_SZ /d "BeautyCam" /f >nul 2>nul
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" /v DisplayIcon /t REG_SZ /d "%DEST%\BeautyCam.exe" /f >nul 2>nul
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" /v InstallLocation /t REG_SZ /d "%DEST%" /f >nul 2>nul
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" /v UninstallString /t REG_SZ /d "\"%DEST%\uninstall.bat\"" /f >nul 2>nul
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" /v Publisher /t REG_SZ /d "BeautyCam" /f >nul 2>nul
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" /v DisplayVersion /t REG_SZ /d "1.0.0" /f >nul 2>nul

if exist "%WORK%" rd /s /q "%WORK%" 2>nul

echo.
echo ============================================================
echo  Installed to: %DEST%
echo  1) Double-click "BeautyCam" on the desktop
echo  2) The control panel opens in your browser; pick a camera and hit Start
echo  3) In OBS add "Video Capture Device" and choose "OBS Virtual Camera"
echo ============================================================
timeout /t 8 >nul
