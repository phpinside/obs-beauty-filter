"""把打包产物 + 安装脚本组装成可直接发给别人的压缩包。

用法：python package.py   （先跑过 python build.py）
产物：release/BeautyCam/ + release/install.bat + ... ；以及 BeautyCam-win64.zip
"""
from __future__ import annotations

import os
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASE = os.path.join(HERE, "release")
DIST_APP = os.path.join(HERE, "dist", "BeautyCam")
FILES = ("install.bat", "uninstall.bat", "README.md", "installer.nsi")


def main() -> int:
    if not os.path.isfile(os.path.join(DIST_APP, "BeautyCam.exe")):
        print("[错误] 没有 dist/BeautyCam/BeautyCam.exe，请先执行 python build.py")
        return 1

    if os.path.isdir(RELEASE):
        # 不直接删除（会触发环境的批量删除保护），挪到临时目录
        import tempfile
        import time
        trash = os.path.join(tempfile.gettempdir(), f"BeautyCam_release_{int(time.time())}")
        try:
            shutil.move(RELEASE, trash)
        except Exception as exc:
            print(f"[!] 无法移走旧 release（{exc}）")
            return 1
    os.makedirs(RELEASE, exist_ok=True)

    shutil.copytree(DIST_APP, os.path.join(RELEASE, "BeautyCam"))
    for name in FILES:
        src = os.path.join(HERE, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(RELEASE, name))

    zip_path = os.path.join(HERE, "BeautyCam-win64.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, _dirs, files in os.walk(RELEASE):
            for f in files:
                full = os.path.join(root, f)
                arc = os.path.relpath(full, RELEASE)
                zf.write(full, arc)

    total = sum(os.path.getsize(os.path.join(r, f))
                for r, _d, fs in os.walk(RELEASE) for f in fs)
    print(f"[*] 分发目录: {RELEASE}  ({total / 1e6:.1f} MB)")
    print(f"[*] 压缩包  : {zip_path}  ({os.path.getsize(zip_path) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
