# BeautyCam 美颜摄像头

用 OpenCV 自己实现的美颜摄像头，跑在 Windows 上，把处理后的画面推进 **OBS 虚拟摄像头**，
OBS 里再加一路【视频采集设备 → OBS Virtual Camera】就是美颜画面。

不依赖任何商业美颜 SDK（相芯 FaceUnity / 商汤 / 美图都不用），可自由分发、可离线运行。
控制面板是本机浏览器里的网页，**不依赖 tkinter**，所以打包体积小、换机器也不会因为缺 GUI 库启动失败。

---

## 它做了什么

```
摄像头 ──▶ 镜像 ──▶ [人脸定位] ──▶ 椭圆向心变形(瘦脸/大眼)
                        │
                        ▼
              肤色掩膜 ──▶ 保边磨皮(引导滤波) ──▶ 美白/红润 ──▶ 锐化
                        │
                        ▼
              OBS 虚拟摄像头 / 本地预览
```

| 参数 | 作用 | 建议值 |
|---|---|---|
| 磨皮 | 引导滤波压平皮肤纹理，保留五官边缘 | 0.45 ~ 0.70 |
| 美白 | 向白色做掩膜混合，高光做保护 | 0.20 ~ 0.40 |
| 红润 | 中间调向暖肤色混合，改善“白得像病” | 0.15 ~ 0.30 |
| 锐化 | uint8 域 USM，放在磨皮之前，先补细节再磨皮 | 0.25 ~ 0.45 |
| 瘦脸 | 椭圆内向心压缩，负值可以放大 | 0.2 ~ 0.4 |
| 大眼 | 眼区局部放大（依赖人脸定位） | 0 ~ 0.3 |
| 性能模式 | 3/4 分辨率渲染再放大输出 | 默认开 |

参数存在 `%APPDATA%\BeautyCam\profile.json`，换机器复制这个文件即可沿用。

## 性能（本机实测，1280×720，i7 级 16 线程）

| 渲染缩放 | 单帧耗时 | 可跑帧率 |
|---|---|---|
| 1.00（画质优先） | 43 ms | 23 fps |
| 0.75（默认） | 25~27 ms | 37~40 fps |
| 0.50（极速） | 11~12 ms | 80+ fps |

> 早期版本全 float32 逐遍处理只有 4 fps，现在靠三件事提速 10 倍：
> 低分辨率算引导层/掩膜、用 `cv2.blendLinear`/`cv2.multiply` 替代 numpy 广播运算、
> `addWeighted(dtype=CV_8U)` 替代 `clip+astype` 做饱和转换。

## 快速开始（只想用）

两种分发形态，任选一种：

**A. 单文件安装包**（推荐给完全不懂电脑的人）
双击 `BeautyCam-Setup-1.0.0.exe` → 自动解包并安装到 `%LOCALAPPDATA%\Programs\BeautyCam`，桌面出现 BeautyCam 图标。

**B. 免安装压缩包**（体积一样，可以自己看里面有什么）
解压 `BeautyCam-win64.zip` → 双击 `install.bat`。

然后：

1. 装好 **OBS Studio**（它自带 OBS Virtual Camera 驱动，必须要）
2. 双击桌面 **BeautyCam** → 浏览器自动弹出控制面板 → 选摄像头 → 点【开始】
3. OBS 里添加来源：**视频采集设备 → 设备选 `OBS Virtual Camera`**
4. 在面板里拖滑杆，OBS 画面实时变化

> 没有摄像头也能先看效果：`BeautyCam.exe --demo`，用合成人像演示（浏览器面板照常可用）。
>
> 卸载：`%LOCALAPPDATA%\Programs\BeautyCam\uninstall.bat`，或 Windows 设置的「应用」里找 BeautyCam。

## 从源码跑

```bash
python -m pip install numpy opencv-python pyvirtualcam
cd src
python -m beautycam                 # 开面板（自动打开浏览器）
python -m beautycam --selftest      # 只跑算法自测，输出对比图与指标
python -m beautycam --demo          # 合成人像演示
python -m beautycam --source a.mp4  # 用视频文件当源
```

自测产出（不通过会返回非 0，可直接进 CI）：

- `selftest_before.png` / `selftest_after.png` / `selftest_compare.png`
- `selftest_metrics.json`：磨皮前后高频能量下降、亮度增益、脸宽变化、耗时与 fps

本机参考值：磨皮 0.75 → 高频纹理能量下降 **84%**；美白 0.45 → L 通道 +12；瘦脸 0.35 → 脸宽 **-3.4%**。

## 打包成 exe

```bash
python tools/make_icon.py     # 生成图标
python build.py               # 产物: dist/BeautyCam/BeautyCam.exe（onedir，约 146MB）
python package.py             # 组装 release/ + BeautyCam-win64.zip
python -m PyInstaller --onefile --console --name setup_launcher \
       --distpath build_launcher/dist --workpath build_launcher/work \
       tools/setup_launcher.py          # 安装器内核 exe
python make_setup.py          # 单文件安装包 BeautyCam-Setup-1.0.0.exe（系统自带 IExpress）
python make_setup.py --probe  # 只出探针包，验证链路
```

> **为什么安装包要多一个 `setup_launcher.exe`**：
> IExpress 的自解压壳启动 `.bat` 时硬编码用 `Command.com /c xxx`，而新版 Windows 已经没有
> command.com（双击会报「创建进程 command.com 错 / 系统找不到指定的文件」）。
> 把 `AppLaunched` 指向一个 exe，它就改用 CreateProcess 正常启动。
> 另外两件事也踩过：
> ① 启动器必须 `wait()` 等批处理执行完，否则解压壳会在我们退出后立刻删掉 `%TEMP%\IXP000.TMP`；
> ② 直接往 IExpress 清单里塞 70 多个文件，只要出现 `.xml`（OpenCV 的 haarcascade）就静默失败，
> 所以先打成 `payload.zip` 再封包；③ `reg.exe` 在受管环境可能被禁，所以安装器的注册表写入走 Python `winreg`。
>
> 想要更标准的安装包（许可页、可选组件）：装 NSIS 后 `makensis installer.nsi`。

## 目录结构

```
beautycam/
├── src/beautycam/
│   ├── params.py     # 参数模型与配置持久化
│   ├── imgops.py     # 引导滤波 / 肤色掩膜 / 色调 / 变形（性能关键全在这）
│   ├── pipeline.py   # 流水线编排 + 映射表缓存 + 渲染缩放
│   ├── facetrack.py  # Haar 人脸定位 + 指数平滑
│   ├── camera.py     # 采集线程 + 虚拟摄像头输出
│   ├── webui.py      # 内置 HTTP 面板（标准库，无 GUI 依赖）
│   ├── assets/web/   # 面板前端（单文件 HTML）
│   └── selftest.py   # 合成人像 + 量化自测
├── build.py / package.py / installer.nsi
├── install.bat / uninstall.bat
└── tools/            # make_icon.py / bench.py
```

## 常见问题

**OBS 里找不到 OBS Virtual Camera**
OBS 没装或驱动没注册。先正常打开一次 OBS（它会注册驱动），再重启 BeautyCam。

**浏览器没自动弹出面板**
看控制台输出里的地址（`http://127.0.0.1:<port>/`），手动打开；或用 `--port 8080` 固定端口。

**画面很卡**
降分辨率到 1280×720 或 960×540、帧率 30；保持“性能模式”开启；关掉“大眼”（多一次 remap）。

**摄像头被占用**
BeautyCam 会独占摄像头。用虚拟摄像头方案时，OBS 里不要再直接采集同一个摄像头。

**瘦脸位置不对**
面板里关掉“自动人脸定位”，改 `%APPDATA%\BeautyCam\profile.json` 里的 `face_cx/face_cy/face_rx/face_ry`。
注意：变形区会自动比人脸大 30%，否则脸型轮廓不会被收窄。

**会被杀软误报吗**
PyInstaller 打的 exe 偶尔会被误判。介意的话改用源码运行，或给 exe 做代码签名。

## 许可

算法与代码为原创实现，MIT 许可，可商用。**不要**把相芯/商汤等商业 SDK 的二进制塞进这个项目再分发。
