# obs-beauty-filter —— OBS 原生美颜滤镜

挂在**任意画面源**上的滤镜（视频采集设备 / 媒体源 / 窗口采集 / 游戏采集都行），
在 OBS 里点【右键 → 滤镜 → 添加 → 美颜滤镜】即可。CPU 占用几乎为零，全部在 GPU 着色器里算。

```
OBS 源 ──▶ [美颜滤镜] ──▶ 输出
              │
              ├─ 肤色掩膜（只磨皮肤）
              ├─ 9 抽样保边模糊（磨皮，不掉五官）
              ├─ 提亮 + 暖调（美白 / 红润）
              ├─ 非皮肤区 USM（锐化）
              └─ 椭圆向心变形（瘦脸）
```

## 与 BeautyCam App 方案的区别

| | obs-beauty-filter（本目录） | BeautyCam（另一目录） |
|---|---|---|
| 形态 | OBS 插件 DLL | 独立 exe + 虚拟摄像头 |
| 需要编译 | 是（Visual Studio + CMake） | 否（已打包 exe） |
| 适用源 | 任意现有源，可多层叠加 | 只有摄像头 |
| 性能 | GPU，几乎无损 | CPU，720p 约 30~60fps（看机器） |
| 分发 | 复制两个目录 / 装 NSIS 包 | 复制文件夹 / install.bat |

两个可以**同时用**：BeautyCam 做基础磨皮推给 OBS，滤镜再做局部微调。

## 编译

### 方式 A：GitHub Actions（最省事，不用装 VS）

推到 GitHub，`.github/workflows/build.yml` 会自动：
拉 OBS 30.2.3 源码 → 关掉 UI/Qt 只编 libobs → 编插件 → 产出 `obs-beauty-filter-win64.zip`。

### 方式 B：本机编

需要 **Visual Studio 2022**（勾选“使用 C++ 的桌面开发”）+ **CMake 3.20+**：

```bat
build-windows.bat        :: 首次会浅克隆 OBS 源码，比较慢
install-to-obs.bat       :: 装进 OBS（需要管理员权限）
```

手动等价步骤：

```bat
git clone --depth 1 --branch 30.2.3 https://github.com/obsproject/obs-studio.git obs
xcopy /e /i src  obs\plugins\obs-beauty-filter\src
xcopy /e /i data obs\plugins\obs-beauty-filter\data
copy CMakeLists.txt obs\plugins\obs-beauty-filter\
echo add_subdirectory(obs-beauty-filter)>> obs\plugins\CMakeLists.txt

cmake -S obs -B build -G "Visual Studio 17 2022" -A x64 ^
      -DENABLE_UI=OFF -DENABLE_QT=OFF -DENABLE_BROWSER=OFF ^
      -DENABLE_VLC=OFF -DENABLE_SCRIPTING=OFF
cmake --build build --config RelWithDebInfo --target obs-beauty-filter
cmake --install build --config RelWithDebInfo --prefix dist
```

产物布局（与 OBS 官方插件一致）：

```
dist/obs-plugins/64bit/obs-beauty-filter.dll
dist/data/obs-plugins/obs-beauty-filter/shaders/beauty.effect
dist/data/obs-plugins/obs-beauty-filter/locale/{en-US,zh-CN}.ini
```

## 参数

| 参数 | 范围 | 说明 |
|---|---|---|
| 磨皮 | 0 ~ 1 | 0.5 左右最自然；1.0 会明显“塑料感” |
| 美白 | 0 ~ 1 | 0.3 起步；太亮会吃掉鼻梁阴影 |
| 红润 | 0 ~ 1 | 补气色，0.2 足够 |
| 锐化 | 0 ~ 1 | 只作用于非皮肤区，0.3~0.4 让眼睛更清 |
| 瘦脸强度 | -0.6 ~ 0.6 | 正值收窄，负值放大 |
| 人脸中心/半径 X/Y | 0 ~ 1 | 手动画框，默认 0.5/0.46/0.22/0.30 |

> 瘦脸是**手动画框**，不做人脸检测：插件层做人脸检测需要额外引入模型和线程，
> 而且摄像头一动框就飘。想要自动跟随，用 BeautyCam App（它有 Haar 定位）。

## 兼容性

- OBS Studio 27 ~ 31（用了 `obs_source_process_filter_begin/end` 这个一直稳定的接口）
- 只支持 **64 位** OBS（32 位已停止维护）
- 需要源码里 `data/shaders/beauty.effect` 与 DLL 一起部署，缺了会在日志里报加载失败

## 排错

装完没出现在滤镜列表里 → 看 OBS【帮助 → 日志文件】，搜 `beauty-filter`：

- `failed to load module` → DLL 架构不对（给了 32 位）或 OBS 版本过旧
- `无法加载 shaders/beauty.effect` → data 目录没拷到 `OBS\data\obs-plugins\obs-beauty-filter\`
- 画面全黑 → 当前显卡驱动不支持 effect 编译，日志里会有 shader 编译错误行

## 本机独立构建（已验证）
运行 `build-windows.bat`，默认使用 `D:\Program Files\obs-studio` 中的 OBS。
其他安装位置：`build-windows.bat -ObsRoot "C:\Program Files\obs-studio"`。
脚本自动发现 VS 2022 C++ 工具及其 CMake，下载官方 OBS 30.2.3 头文件，
从本机 obs.dll 导出表生成 x64 导入库，只编译本插件，无需编译 OBS 或下载 CURL/Qt。
产物位于 dist，包含 DLL、语言文件及 shader。需要 Git、VS 2022 C++ 工具和 Windows SDK。
2026-11-17：MSVC 19.44、Windows SDK 10.0.26100.0、CMake 3.31 构建成功；
链接目标为本机 OBS 33.0.1。此记录仅确认编译及静态依赖检查，尚未确认 OBS 加载和 GPU 渲染。

