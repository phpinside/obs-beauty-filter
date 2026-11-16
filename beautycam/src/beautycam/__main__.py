"""命令行入口：默认开控制面板；--selftest 只跑算法；--demo 用合成画面演示。"""
from __future__ import annotations

import argparse
import sys

from .params import load_settings


class DemoSource:
    """把合成人像包装成 VideoCapture 的接口，没有摄像头也能看效果。"""

    def __init__(self, width: int = 1280, height: int = 720):
        self.width, self.height = width, height
        self._n = 0
        self._base = None

    def isOpened(self):
        return True

    def set(self, *a, **k):
        return True

    def read(self):
        import cv2
        import numpy as np
        from .selftest import synth_portrait

        if self._base is None:                      # 合成一次即可，逐帧只做平移
            self._base = synth_portrait(self.width, self.height, seed=7)
        self._n += 1
        dx = int(6 * np.sin(self._n / 18.0))        # 轻微呼吸，避免画面完全静止
        m = np.float32([[1, 0, dx], [0, 1, 0]])
        return True, cv2.warpAffine(self._base, m, (self.width, self.height))

    def release(self):
        pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="BeautyCam")
    ap.add_argument("--selftest", action="store_true", help="跑算法自测与性能基准")
    ap.add_argument("--out", default=".", help="自测输出目录")
    ap.add_argument("--frames", type=int, default=24, help="基准帧数")
    ap.add_argument("--demo", action="store_true", help="用合成人像当视频源")
    ap.add_argument("--source", default=None, help="视频文件路径，替代摄像头")
    ap.add_argument("--port", type=int, default=0, help="面板端口（0=随机）")
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = ap.parse_args(argv)

    if args.selftest:
        from .selftest import run_selftest

        m = run_selftest(args.out, args.frames)
        ok = m["hf_drop_pct"] > 10 and m["l_gain"] > 0.5 and m["fps"] > 5
        print("RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 2

    from .webui import run

    settings = load_settings()
    source = None
    if args.demo:
        source = DemoSource(settings.width, settings.height)
        settings.show_preview = True
    elif args.source:
        source = args.source
        settings.show_preview = True

    return run(settings, source=source, port=args.port,
               open_browser=not args.no_browser)


if __name__ == "__main__":
    sys.exit(main())
