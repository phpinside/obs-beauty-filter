# obs-beauty-filter —— OBS 原生美颜滤镜

**优先推荐：Windows x64 已编译，并已在 OBS 中验证可用。**

[下载插件](https://github.com/phpinside/obs-beauty-filter/releases/tag/filter-v1.0.0) · [安装使用说明](INSTALL.md)

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
| 需要编译 | 下载发布包即可；开发时需要 VS + CMake | 否（已打包 exe） |
| 适用源 | 任意现有源，可多层叠加 | 只有摄像头 |
| 性能 | GPU，几乎无损 | CPU，720p 约 30~60fps（看机器） |
| 分发 | 复制两个目录 / 装 NSIS 包 | 复制文件夹 / install.bat |

两个可以**同时用**：BeautyCam 做基础磨皮推给 OBS，滤镜再做局部微调。

## 编译

GitHub Actions 工作流位于仓库根目录，已构建成功，可从运行页面下载 Artifacts。

本机需要 Git、VS 2022 C++ 工具和 Windows SDK。在本目录运行：

```bat
build-windows.bat -ObsRoot "D:\Program Files\obs-studio"
```

脚本自动获取官方 OBS 头文件，从已安装 OBS 生成导入库，只编译插件。
产物位于 dist，包含 DLL、着色器及语言文件。

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

- 本机 OBS Studio 33.0.1 已验证，其他版本需实际验证
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
链接目标为本机 OBS 33.0.1。编译和静态依赖检查已完成，用户已确认 OBS 实机验证通过。


## 美白修复与验证范围

美白采用保持颜色比例的有限增益，不再添加白色偏移；使用肤色色度置信度、人脸椭圆范围和高光保护。锐化改用原图高频，避免放大美白增益。
美白前请在人脸区域参数中将中心和半径对准人脸；范围外美白增量为零。
颜色加手动范围不能替代语义分割，范围内的肤色衣物仍可能误选；此版本不宣称自动识别所有真实皮肤。
运行 `python tests/test_whitening.py` 检查 0、0.01、0.1、0.3、0.5 五档连续性、范围外背景不变、中性色与高光保护。
这些是数值回归，尚需在 OBS 中保持其他参数不变，针对真实人像、窗户、衣物逐档比较；此前的实机验证不代表本次修复已实机验收。
