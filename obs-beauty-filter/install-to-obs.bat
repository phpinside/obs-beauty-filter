@echo off
chcp 65001 >nul
title 安装 obs-beauty-filter 到 OBS
setlocal

set DIST=%~dp0dist
if not exist "%DIST%\obs-plugins\64bit\obs-beauty-filter.dll" (
    echo [错误] 没找到 dist\obs-plugins\64bit\obs-beauty-filter.dll
    echo        请先运行 build-windows.bat 编译。
    pause & exit /b 1
)

REM 依次尝试：注册表 -> 默认目录
set OBS=
for /f "tokens=2,*" %%a in ('reg query "HKLM\SOFTWARE\OBS Studio" /v InstallPath 2^>nul ^| findstr InstallPath') do set OBS=%%b
if not defined OBS if exist "%ProgramFiles%\obs-studio\bin\64bit\obs64.exe" set OBS=%ProgramFiles%\obs-studio
if not defined OBS if exist "%ProgramFiles(x86)%\obs-studio\bin\64bit\obs64.exe" set OBS=%ProgramFiles(x86)%\obs-studio

if not defined OBS (
    echo [错误] 没找到 OBS Studio 安装目录。请先安装 OBS，或手动把 dist 里的
    echo        obs-plugins\64bit\*.dll 复制到 OBS 的同样位置。
    pause & exit /b 1
)

echo 目标 OBS：%OBS%
echo 正在复制...
net session >nul 2>nul || (echo [提示] 需要管理员权限，正在请求提升... & powershell -Command "Start-Process '%~f0' -Verb RunAs" & exit /b)

xcopy /e /i /y "%DIST%\obs-plugins" "%OBS%\obs-plugins" >nul
xcopy /e /i /y "%DIST%\data\obs-plugins" "%OBS%\data\obs-plugins" >nul

echo.
echo 装好了。打开 OBS，在任意画面源上点【右键 -> 滤镜 -> 添加 -> 美颜滤镜】。
echo 提示：装完记得在 OBS 的“帮助 -> 日志文件”里确认没有加载失败。
pause
