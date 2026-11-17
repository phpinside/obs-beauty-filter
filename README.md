# OBS 美颜摄像头 / OBS Beauty Cam

给 OBS 直播使用的美颜工具。**优先推荐方案 B：obs-beauty-filter 原生滤镜，已验证可用。**

| 方案 | 形态 | 状态 |
|---|---|---|
| **B. obs-beauty-filter 插件** | OBS 原生滤镜，C + GLSL，直接挂在任意来源上 | 已编译，OBS 实机验证通过；优先推荐 |
| **A. BeautyCam 应用** | 独立程序，处理摄像头画面后推到 **OBS 虚拟摄像头**，OBS 里当普通采集设备用 | 已打包、已实测 |

美颜算法全部自研，没有依赖任何商业人脸 SDK：YCrCb 肤色掩膜 + 引导滤波保边磨皮 + 明度/暖调重映射 + USM 锐化 + 椭圆向心变形（瘦脸）。


## 方案 B：obs-beauty-filter（优先推荐）

**Windows x64 已编译，并已在 OBS 中验证可用。** 原生滤镜直接挂在现有视频来源上，使用 GPU 处理，无需启动额外的 BeautyCam 应用。

### 下载与安装

1. [下载 Windows 64 位插件包](https://github.com/phpinside/obs-beauty-filter/releases/download/filter-v1.0.0/obs-beauty-filter-win64.zip)。
2. 完全退出 OBS，解压 ZIP。
3. 将包内 `obs-plugins` 和 `data` 两个文件夹复制到 OBS 安装目录并合并。
4. 重启 OBS，右键视频来源 → 滤镜 → 效果滤镜下的“＋” → 美颜滤镜。

建议从磨皮 0.5、美白 0.3、红润 0.2、锐化 0.3 开始调整。瘦脸需要手动设置人脸中心和半径，不会自动跟随。

完整步骤见 [安装使用说明](obs-beauty-filter/INSTALL.md)，开发者参见 [插件文档](obs-beauty-filter/README.md)。仓库根目录的 GitHub Actions 工作流已构建成功。

## 方案 A：BeautyCam

### 下载

装好的包在 [Releases](https://github.com/phpinside/obs-beauty-filter/releases/latest)：

- `BeautyCam-Setup-1.0.0.exe`（65 MB）—— 双击安装，免配置
- `BeautyCam-win64.zip`（58 MB）—— 便携版，解压后跑 `install.bat`

> 未做代码签名，SmartScreen 可能提示"未知发布者"，选「仍要运行」即可。

### 用

1. 先装 **OBS Studio**（虚拟摄像头驱动由 OBS 提供，这是前提）
2. 双击安装包，或解压便携版后双击 `install.bat`
3. 打开 BeautyCam，浏览器会自动弹出控制面板；选摄像头 → 点【开始】
4. OBS 里添加来源 **视频采集设备**，设备选 `OBS Virtual Camera`

没有摄像头也能看效果：`BeautyCam.exe --demo`，用合成人像演示。

控制面板是本地 HTTP 服务（`127.0.0.1`）+ 浏览器页面，不依赖 tkinter/Qt，换机器不会因为缺 GUI 库起不来。参数存 `%APPDATA%\BeautyCam\profile.json`。

### 可调项

磨皮、美白、红润、锐化、瘦脸、大眼强度，人脸自动定位开关（Haar 级联），镜像画面，渲染缩放（性能/画质权衡），输出分辨率。

### 构建

```bash
pip install numpy opencv-python pyvirtualcam pyinstaller
python tools/make_icon.py     # 生成图标
python build.py               # 产物 dist/BeautyCam/BeautyCam.exe（onedir，约 146MB）
python package.py             # 组装 release/ + BeautyCam-win64.zip
python make_setup.py          # 单文件安装包（Windows 自带 IExpress，无需 NSIS）
```

### BeautyCam 应用效果与性能

1280×720，Python 实现，打包后的 exe 实测：

| 指标 | 结果 |
|---|---|
| 单帧耗时 / 帧率 | 25–27 ms / **37–40 fps**（默认 0.75 渲染缩放）；全分辨率 43 ms / 23 fps |
| 磨皮强度 | 皮肤高频纹理能量 **下降 84.6%** |
| 美白 | L 通道 **+12.3** |
| 瘦脸 | 脸宽 495 → 478 px（强度 0.35） |

效果对比图不在仓库里（避免二进制），运行 `BeautyCam.exe --selftest` 会在 `out_selftest/selftest_compare.png` 生成。

## BeautyCam 应用算法

```
帧 → (可选) 人脸检测定位 → 几何变形(瘦脸)
   → 肤色掩膜 (YCrCb 阈值, 软权重)
   → 磨皮: 半分辨率引导滤波求平滑层 → 放大 → 按 mask 做 blendLinear
   → 美白/红润: 向白色插值 + 中间调偏暖
   → 锐化: 亮度域 USM, 皮肤区抑制
   → uint8 输出
```

几个关键选择：

- **只在皮肤区生效**。所有重映射都乘肤色掩膜，头发、眼睛、背景不动，所以不会整体糊。
- **磨皮走低分辨率**。平滑层本质是低频信息，半分辨率算完再放大，质量几乎无损，时间省一大截。
- **保边靠引导滤波**。普通高斯会把五官边缘也抹掉，引导滤波以原图亮度为引导，边缘处增益趋近 1。

### 性能踩过的坑（Python/NumPy）

| 写法 | 慢在哪 | 换掉之后 |
|---|---|---|
| `img[...] *= w[..., None]` | NumPy 广播乘法比 `cv2.multiply` 慢约 3 倍 | `cv2.multiply` + `cv2.merge` |
| `np.clip(f,0,255).astype(np.uint8)` | 两遍遍历 | `cv2.addWeighted(..., dtype=CV_8U)`，带饱和截断，快 3 倍 |
| 全分辨率算引导滤波 | 720p 下 ~120 ms | 半分辨率算再放大 |

最终 720p 从 4 fps 提到 37 fps。

## 目录

```
beautycam/                    方案 A：应用
  src/beautycam/imgops.py       算法原语（掩膜/磨皮/色调/锐化/变形）
  src/beautycam/pipeline.py     流水线编排 + 参数缓存
  src/beautycam/facetrack.py    人脸定位
  src/beautycam/camera.py       采集 + 虚拟摄像头推流
  src/beautycam/webui.py        控制面板后端
  src/beautycam/assets/web/     控制面板前端
  src/beautycam/selftest.py     合成人像自测（出指标 + 对比图）
obs-beauty-filter/            方案 B：OBS 原生滤镜
  src/beauty-filter.c           滤镜实现
  data/shaders/beauty.effect    GPU 版本
```

## 已知限制

- 虚拟摄像头依赖 OBS 的驱动；不装 OBS 就只是本地预览。
- 人脸检测用 Haar 级联，正脸、光照正常时稳，侧脸和大角度会丢；需要更稳可以换 ONNX 轻量模型。
- 原生滤镜已在本机 OBS 验证可用；其他版本和硬件环境需实际验证。
- Python 实现单线程跑 CPU，高分辨率下建议开渲染缩放；要 4K 60fps 得走方案 B 的 GPU 路径。

## 许可

MIT，见 [LICENSE](LICENSE)。算法与代码均为独立实现。


## 效果对比

![美颜前后对比](beautycam/preview_compare.png)

左：原图；右：处理后（磨皮 0.75 / 美白 0.45 / 红润 0.3 / 锐化 0.35 / 瘦脸 0.35）。皮肤纹理被抹平，五官与头发细节保留，没有色偏和接缝。

## Windows 64 位原生滤镜安装

下载和完整安装使用步骤请见 [滤镜安装说明](obs-beauty-filter/INSTALL.md)。


