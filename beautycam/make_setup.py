"""用 Windows 自带的 IExpress 生成单文件安装包（不需要 NSIS 或任何第三方工具）。

做法：把 release/ 打成一个 payload.zip，再让 IExpress 把
「install.bat + payload.zip」封成自解压 exe；运行后自动调 install.bat，
install.bat 用系统自带 tar 解包 -> 复制到 %LOCALAPPDATA% -> 建快捷方式/卸载项。

为什么不直接把 72 个文件塞给 IExpress：实测只要清单里出现 .xml
（OpenCV 的 haarcascade_*.xml），IExpress 就会静默失败返回 1。
包一层 zip 既绕开这个坑，也把包压得更小。

用法：
    python build.py && python package.py
    python make_setup.py            # 出 BeautyCam-Setup-1.0.0.exe
    python make_setup.py --probe    # 只出探针包，验证「解包 + 自测」链路
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASE = os.path.join(HERE, "release")
IEXPRESS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32", "iexpress.exe")
OUT_EXE = os.path.join(HERE, "BeautyCam-Setup-1.0.0.exe")

PROBE_BAT = r"""@echo off
set "LOG=%TEMP%\bc_probe_result.txt"
set "WORK=%TEMP%\bc_probe"
echo [probe] start > "%LOG%"
if exist "%WORK%" rd /s /q "%WORK%"
mkdir "%WORK%"
tar -xf "%~dp0payload.zip" -C "%WORK%" >>"%LOG%" 2>&1
echo [probe] tar=%ERRORLEVEL% >> "%LOG%"
if not exist "%WORK%\BeautyCam\BeautyCam.exe" (
  echo [probe] MISSING exe >> "%LOG%"
  exit /b 1
)
"%WORK%\BeautyCam\BeautyCam.exe" --selftest --out "%WORK%\out" >>"%LOG%" 2>&1
echo [probe] selftest=%ERRORLEVEL% >> "%LOG%"
copy /y "%WORK%\out\selftest_metrics.json" "%TEMP%\bc_probe_metrics.json" >>"%LOG%" 2>&1
echo [probe] done >> "%LOG%"
"""


def build_payload_zip(stage: str) -> str:
    zip_path = os.path.join(stage, "payload.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for name in ("BeautyCam", "uninstall.bat", "README.md"):
            src = os.path.join(RELEASE, name)
            if not os.path.exists(src):
                continue
            if os.path.isdir(src):
                for root, _dirs, files in os.walk(src):
                    for f in files:
                        full = os.path.join(root, f)
                        zf.write(full, os.path.relpath(full, RELEASE))
            else:
                zf.write(src, name)
    return zip_path


def write_sed(path: str, stage: str, target_exe: str, files: list[str],
              app_launched: str, show_window: int = 1) -> str:
    lines = [
        "[Version]", "Class=IEXPRESS", "SEDVersion=3",
        "[Options]",
        "PackagePurpose=InstallApp",
        f"ShowInstallProgramWindow={show_window}",
        "HideExtractAnimation=0",
        "UseLongFileName=1",
        "InsideCompressed=0",
        "CAB_FixedSize=0",
        "CAB_ResvCodeSigning=0",
        "RebootMode=N",
        "InstallPrompt=",
        "DisplayLicense=",
        "FinishMessage=",
        f"TargetName={target_exe}",
        "FriendlyName=BeautyCam",
        f"AppLaunched={app_launched}",
        "PostInstallCmd=<None>",
        "AdminQuietInstCmd=",
        "UserQuietInstCmd=",
        "SourceFiles=SourceFiles",
        "[Strings]",
    ]
    for i, rel in enumerate(files):
        lines.append(f'FILE{i}="{rel}"')
    lines += ["[SourceFiles]", f"SourceFiles0={stage}\\", "[SourceFiles0]"]
    lines += [f"%FILE{i}%=" for i in range(len(files))]
    with open(path, "w", encoding="ascii", newline="\r\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def main(argv: list[str]) -> int:
    probe = "--probe" in argv
    if not os.path.isdir(RELEASE):
        print("[错误] 没有 release/，请先执行 python package.py")
        return 1
    if not os.path.isfile(IEXPRESS):
        print(f"[错误] 找不到 IExpress: {IEXPRESS}")
        return 1

    stage = tempfile.mkdtemp(prefix="bc_setup_")
    zip_path = build_payload_zip(stage)
    shutil.copy2(os.path.join(HERE, "install.bat"), os.path.join(stage, "install.bat"))
    print(f"[*] payload.zip {os.path.getsize(zip_path) / 1e6:.1f} MB -> {stage}")

    launcher = os.path.join(HERE, "build_launcher", "dist", "setup_launcher.exe")
    if not os.path.isfile(launcher):
        print("[错误] 缺少启动器，请先运行 tools/build_launcher.bat（或 PyInstaller 命令）")
        return 1
    shutil.copy2(launcher, os.path.join(stage, "setup_launcher.exe"))

    sed = os.path.join(stage, "build.sed")
    if probe:
        probe_bat = os.path.join(stage, "probe.bat")
        with open(probe_bat, "w", encoding="ascii", newline="\r\n") as fh:
            fh.write(PROBE_BAT)
        target = os.path.join(stage, "probe.exe")
        write_sed(sed, stage, target, ["probe.bat", "payload.zip"], "probe.bat", 0)
    else:
        target = OUT_EXE
        write_sed(sed, stage, target, ["payload.zip", "setup_launcher.exe"],
                  "setup_launcher.exe", 1)

    print("[*] IExpress 编译中（1~3 分钟）...")
    proc = subprocess.run([IEXPRESS, "/N", "/Q", sed],
                          capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0 or not os.path.isfile(target):
        print(f"[错误] IExpress 失败 rc={proc.returncode}")
        print(proc.stdout[-1500:], proc.stderr[-1500:])
        return 1

    print(f"[*] 完成: {target} ({os.path.getsize(target) / 1e6:.1f} MB)")
    if probe:
        print("[*] 直接运行它，然后看 %TEMP%\\bc_probe_result.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
