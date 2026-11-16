@echo off
rem ASCII-only on purpose (a UTF-8 .bat with CJK text gets mis-parsed by cmd under GBK).
rem A .bat cannot reliably delete the folder it is running from, so this script
rem copies itself to %TEMP% on first run and does the real work from there.
setlocal
set "DEST=%LOCALAPPDATA%\Programs\BeautyCam"
set "SANDBOX=%TEMP%\BeautyCamUninst"

if /i not "%~dp0"=="%SANDBOX%\" (
    if exist "%SANDBOX%" rd /s /q "%SANDBOX%" 2>nul
    mkdir "%SANDBOX%" 2>nul
    copy /y "%~f0" "%SANDBOX%\uninst.bat" >nul 2>nul
    if not exist "%SANDBOX%\uninst.bat" (
        echo [ERROR] Cannot copy uninstaller to TEMP.
        pause & exit /b 1
    )
    start "" "%SANDBOX%\uninst.bat"
    exit /b 0
)

echo Closing BeautyCam ...
taskkill /f /im BeautyCam.exe >nul 2>nul

echo Removing shortcuts ...
del /q "%USERPROFILE%\Desktop\BeautyCam.lnk" >nul 2>nul
del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\BeautyCam\BeautyCam.lnk" >nul 2>nul
rd /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\BeautyCam" >nul 2>nul

echo Removing uninstall entry ...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" /f >nul 2>nul
reg delete "HKCU\Software\BeautyCam" /f >nul 2>nul
rem fallback for machines where reg.exe is restricted
powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam' -Recurse -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath 'HKCU:\Software\BeautyCam' -Recurse -Force -ErrorAction SilentlyContinue" >nul 2>nul

choice /c YN /m "Also delete personal config in %APPDATA%\BeautyCam"
if errorlevel 2 goto keepcfg
rd /s /q "%APPDATA%\BeautyCam" >nul 2>nul
:keepcfg

echo Removing program files ...
rd /s /q "%DEST%" >nul 2>nul

rem self-clean: we run from %TEMP%, so deleting our own folder is safe.
rem (goto) 2>nul makes cmd read past this line before deleting the script.
cd /d "%TEMP%"
(goto) 2>nul & del /f /q "%SANDBOX%\uninst.bat" >nul 2>nul
start "" /min cmd /c "ping -n 3 127.0.0.1 >nul & rd /s /q "%SANDBOX%"" >nul 2>nul

echo.
echo Uninstalled.
timeout /t 3 >nul 2>nul
exit /b 0
