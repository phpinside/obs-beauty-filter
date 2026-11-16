@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title 编译 obs-beauty-filter

REM ============================================================
REM  本机编译脚本：
REM    1) 需要 Visual Studio 2022（含“使用 C++ 的桌面开发”）+ CMake 3.20+
REM    2) 脚本会浅克隆 OBS 源码，把插件挂进 plugins/ 一起编 libobs
REM    3) 产物：dist\obs-plugins\64bit\obs-beauty-filter.dll
REM ============================================================

set OBS_TAG=30.2.3
set ROOT=%~dp0
cd /d "%ROOT%"

where cmake >nul 2>nul || (echo [错误] 找不到 cmake，请先安装 CMake 并加入 PATH & pause & exit /b 1)

if not exist "obs\CMakeLists.txt" (
    echo [1/4] 克隆 OBS %OBS_TAG% 源码（约 100MB，首次较慢）...
    git clone --depth 1 --branch %OBS_TAG% https://github.com/obsproject/obs-studio.git obs || (echo 克隆失败 & pause & exit /b 1)
)

echo [2/4] 把插件挂进 OBS 插件树...
if exist "obs\plugins\obs-beauty-filter" rmdir /s /q "obs\plugins\obs-beauty-filter"
xcopy /e /i /y "src" "obs\plugins\obs-beauty-filter\src" >nul
xcopy /e /i /y "data" "obs\plugins\obs-beauty-filter\data" >nul
copy /y "CMakeLists.txt" "obs\plugins\obs-beauty-filter\CMakeLists.txt" >nul
findstr /c:"add_subdirectory(obs-beauty-filter)" "obs\plugins\CMakeLists.txt" >nul 2>nul || (
    echo.>> "obs\plugins\CMakeLists.txt"
    echo add_subdirectory(obs-beauty-filter)>> "obs\plugins\CMakeLists.txt"
)

echo [3/4] 配置（只编 libobs，不编 UI/Qt）...
cmake -S obs -B build -G "Visual Studio 17 2022" -A x64 ^
  -DENABLE_UI=OFF -DENABLE_QT=OFF -DENABLE_BROWSER=OFF ^
  -DENABLE_VLC=OFF -DENABLE_SCRIPTING=OFF -DENABLE_VIRTUALCAM=OFF ^
  -DCMAKE_BUILD_TYPE=RelWithDebInfo || (echo 配置失败 & pause & exit /b 1)

echo [4/4] 编译...
cmake --build build --config RelWithDebInfo --target obs-beauty-filter || (echo 编译失败 & pause & exit /b 1)
cmake --install build --config RelWithDebInfo --prefix dist

echo.
echo ============================================================
echo  完成：%ROOT%dist\obs-plugins\64bit\obs-beauty-filter.dll
echo  下一步：双击 install-to-obs.bat 装进 OBS
echo ============================================================
pause
