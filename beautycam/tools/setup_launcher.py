"""BeautyCam 安装器（单文件安装包的内核）。

为什么不用 install.bat 干这活：
  * IExpress 的自解压壳只会用 `Command.com /c xxx` 启动 .bat，而新系统没有 command.com；
  * reg.exe 在不少受管环境里被禁用，注册表项就写不进去。
这里用 Python 直接做：解压、复制、建快捷方式（走 PowerShell COM）、写注册表（winreg），
一个 exe 全包，不依赖 cmd 脚本。

打包：见 tools/build_launcher.bat
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import winreg
import zipfile

APP_NAME = "BeautyCam"
DISPLAY_NAME = "BeautyCam 美颜摄像头"
VERSION = "1.0.0"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam"


# --------------------------------------------------------------------------- 小工具
def _out(msg: str) -> None:
    try:
        print(msg, flush=True)
    except Exception:
        pass


def _msgbox(text: str, title: str = "BeautyCam 安装程序", error: bool = False) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10 if error else 0x40)
    except Exception:
        pass


def _setup_console() -> None:
    """让控制台能正确打印中文。"""
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass


def _here() -> str:
    return os.path.dirname(os.path.abspath(
        sys.executable if getattr(sys, "frozen", False) else __file__))


def _wait_key(seconds: int = 12) -> None:
    """等按键，最多等 seconds 秒（双击运行时让用户看清结果）。"""
    try:
        import msvcrt
        import time
        end = time.time() + seconds
        while time.time() < end:
            if msvcrt.kbhit():
                msvcrt.getch()
                return
            time.sleep(0.15)
    except Exception:
        pass


# --------------------------------------------------------------------------- 各步骤
def _extract(zip_path: str, work: str) -> str:
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(work)
    src = os.path.join(work, "BeautyCam")
    if not os.path.isfile(os.path.join(src, "BeautyCam.exe")):
        raise RuntimeError("payload.zip 里没有 BeautyCam\\BeautyCam.exe")
    return src


def _copy(src: str, dest: str, extra: str) -> None:
    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    for name in ("uninstall.bat", "README.md"):
        p = os.path.join(extra, name)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(dest, name))


def _shortcuts(dest: str) -> None:
    exe = os.path.join(dest, "BeautyCam.exe")
    ps = (
        "$ws=New-Object -ComObject WScript.Shell;"
        f"$d=[Environment]::GetFolderPath('Desktop');"
        f"$l=$ws.CreateShortcut($d+'\\{APP_NAME}.lnk');"
        f"$l.TargetPath='{exe}';$l.WorkingDirectory='{dest}';$l.Description='{APP_NAME}';$l.Save();"
        "$sm=Join-Path ([Environment]::GetFolderPath('Programs')) 'BeautyCam';"
        "New-Item -ItemType Directory -Force -Path $sm | Out-Null;"
        f"$l2=$ws.CreateShortcut((Join-Path $sm '{APP_NAME}.lnk'));"
        f"$l2.TargetPath='{exe}';$l2.WorkingDirectory='{dest}';$l2.Save()"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-Command", ps], capture_output=True, timeout=60,
                       creationflags=0x08000000)  # CREATE_NO_WINDOW
    except Exception as exc:
        _out(f"  [警告] 创建快捷方式失败（不影响使用）：{exc}")


def _registry(dest: str) -> None:
    exe = os.path.join(dest, "BeautyCam.exe")
    values = {
        "DisplayName": DISPLAY_NAME,
        "DisplayIcon": exe,
        "InstallLocation": dest,
        "UninstallString": f'"{os.path.join(dest, "uninstall.bat")}"',
        "Publisher": APP_NAME,
        "DisplayVersion": VERSION,
    }
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        for name, value in values.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def _kill_running() -> None:
    try:
        subprocess.run(["taskkill", "/f", "/im", "BeautyCam.exe"],
                       capture_output=True, creationflags=0x08000000)
    except Exception:
        pass


# --------------------------------------------------------------------------- 主流程
def main() -> int:
    _setup_console()
    here = _here()
    zip_path = os.path.join(here, "payload.zip")
    _out(f"[1/5] 安装包目录：{here}")

    if not os.path.isfile(zip_path):
        _out("[错误] 找不到 payload.zip，安装包可能不完整。")
        _msgbox("找不到 payload.zip，安装包可能不完整。\n请重新下载。", error=True)
        return 1

    dest = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                        "Programs", APP_NAME)
    work = os.path.join(tempfile.gettempdir(), "BeautyCamSetup")
    size_mb = os.path.getsize(zip_path) / 1e6
    _out(f"      安装到：{dest}")
    _out(f"[2/5] 解包中（{size_mb:.0f} MB）...")

    _kill_running()
    try:
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        src = _extract(zip_path, work)
        _out("[3/5] 复制文件 ...")
        _copy(src, dest, work)
        _out("[4/5] 创建快捷方式 ...")
        _shortcuts(dest)
        _out("[5/5] 写入卸载信息 ...")
        _registry(dest)
    except Exception as exc:
        _out(f"[错误] 安装失败：{exc!r}")
        _msgbox(f"安装失败：\n{exc}", error=True)
        return 1
    finally:
        shutil.rmtree(work, ignore_errors=True)

    _out("")
    _out("=" * 62)
    _out(f" 安装完成：{dest}")
    _out(" 1) 双击桌面 BeautyCam 图标启动")
    _out(" 2) 浏览器会打开控制面板，选摄像头后点【开始】")
    _out(" 3) OBS 里添加【视频采集设备】-> 设备选【OBS Virtual Camera】")
    _out("=" * 62)
    _out("（这个窗口会在 12 秒后自动关闭，按任意键立即关闭）")
    _wait_key(12)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
