# Windows 64 位美颜滤镜安装与使用

## 下载和安装

从 https://github.com/phpinside/obs-beauty-filter/releases 下载 obs-beauty-filter-win64.zip。

1. 完全退出 OBS Studio（包括后台进程）。
2. 解压 ZIP，将其中 obs-plugins 和 data 两个文件夹复制到 OBS 安装目录并合并。
   本机安装目录为 D:\Program Files\obs-studio；其他电脑以自己的 OBS 安装位置为准。
3. 如果 Windows 提示需要管理员权限，选择“继续”。
4. 确认以下文件存在，然后重新启动 OBS：

```text
<OBS目录>\obs-plugins\64bit\obs-beauty-filter.dll
<OBS目录>\data\obs-plugins\obs-beauty-filter\shaders\beauty.effect
<OBS目录>\data\obs-plugins\obs-beauty-filter\locale\zh-CN.ini
<OBS目录>\data\obs-plugins\obs-beauty-filter\locale\en-US.ini
```

## 使用

在“来源”中右键摄像头、媒体源或其他视频来源 → “滤镜” → “效果滤镜”下的“＋” → “美颜滤镜”。
建议磨皮 0.5、美白 0.3、红润 0.2、锐化 0.3 起步。瘦脸默认关闭；启用时需手动调整人脸中心和半径，不会自动跟随人脸。

## 排错与卸载

未出现滤镜：确认已重启 OBS，安装的是 64 位插件，DLL 和 data 均已复制。
在“帮助 → 日志文件 → 查看当前日志”中搜索 beauty-filter；着色器加载失败时检查 data 路径。
卸载：退出 OBS，删除上述 DLL 和 data\obs-plugins\obs-beauty-filter 文件夹。

## 构建与验证范围

本包已在 Windows 使用 VS 2022 / MSVC 19.44、Windows SDK 10.0.26100.0 编译成功。
使用官方 OBS 30.2.3 头文件及本机 OBS 33.0.1 导出接口链接，已检查 DLL 导出及静态依赖。
用户已确认插件在 OBS 中验证可用；其他版本和硬件环境需实际验证。

源码构建：运行 build-windows.bat；自定义 OBS 位置运行：

```bat
build-windows.bat -ObsRoot "C:\Program Files\obs-studio"
```

仓库根目录 .github/workflows/build.yml 支持推送 main 或手动触发，产物在对应 Actions 运行页面的 Artifacts 中下载。


