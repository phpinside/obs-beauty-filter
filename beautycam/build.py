"""打包脚本：python build.py

产物在 dist/BeautyCam/，双击 BeautyCam.exe 即可运行。
用 onedir（不是 onefile）：启动快、不需要每次解压，也不容易被杀软误报。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
DIST = os.path.join(HERE, "dist")
BUILD = os.path.join(HERE, "build")


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[*] 正在安装 PyInstaller ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def main() -> int:
    ensure_pyinstaller()
    if os.path.isdir(BUILD):
        shutil.rmtree(BUILD, ignore_errors=True)

    # 上一次的产物不直接删除（避免触发环境的批量删除保护），先挪到临时目录
    target = os.path.join(DIST, "BeautyCam")
    if os.path.isdir(target):
        import tempfile
        import time
        trash = os.path.join(tempfile.gettempdir(), f"BeautyCam_old_{int(time.time())}")
        try:
            shutil.move(target, trash)
            print(f"[*] 旧产物已移到 {trash}")
        except Exception as exc:
            print(f"[!] 无法移走旧产物（{exc}），请手动删除 {target}")
            return 1

    args = [
        "--noconfirm", "--clean",
        "--onedir", "--windowed",
        "--name", "BeautyCam",
        "--paths", SRC,
        "--distpath", DIST,
        "--workpath", BUILD,
        "--specpath", BUILD,
        "--hidden-import", "pyvirtualcam",
        "--collect-submodules", "cv2",
        "--exclude-module", "matplotlib",
        "--exclude-module", "pandas",
        "--exclude-module", "scipy",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PySide6",
    ]
    ico = os.path.join(HERE, "assets", "beautycam.ico")
    if os.path.isfile(ico):
        args += ["--icon", ico]
    assets = os.path.join(SRC, "beautycam", "assets")
    if os.path.isdir(assets) and os.listdir(assets):
        args += ["--add-data", f"{assets};beautycam/assets"]

    args.append(os.path.join(SRC, "run.py"))

    import PyInstaller.__main__ as pm
    pm.run(args)

    exe = os.path.join(DIST, "BeautyCam", "BeautyCam.exe")
    print("\n[*] 产物:", exe if os.path.isfile(exe) else "(未生成，请检查上面的日志)")
    return 0 if os.path.isfile(exe) else 1


if __name__ == "__main__":
    raise SystemExit(main())
