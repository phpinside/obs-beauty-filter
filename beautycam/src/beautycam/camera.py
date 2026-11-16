"""摄像头采集与虚拟摄像头输出。

输出端优先使用 OBS Virtual Camera（OBS 26+ 自带驱动），
没有的话尝试 Unity Capture，最后退化为仅本地预览。
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np

from .pipeline import BeautyPipeline
from .params import AppSettings, BeautyParams


@dataclass
class VirtualCamStatus:
    ok: bool
    backend: str = ""
    device: str = ""
    error: str = ""


def list_cameras(max_index: int = 6) -> list[tuple[int, str]]:
    """枚举可用摄像头（DirectShow 下逐个试打开，代价可控）。"""
    found: list[tuple[int, str]] = []
    for idx in range(max_index):
        cap = None
        try:
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap is not None and cap.isOpened():
                ok, _ = cap.read()
                if ok:
                    found.append((idx, f"摄像头 {idx}"))
        except Exception:
            pass
        finally:
            if cap is not None:
                cap.release()
    return found


class VirtualOut:
    """虚拟摄像头封装，构造失败不影响主流程。"""

    def __init__(self, width: int, height: int, fps: int,
                 prefer: tuple[str, ...] = ("obs", "unitycapture")):
        self.cam = None
        self.status = VirtualCamStatus(False, error="未初始化")
        try:
            import pyvirtualcam
        except Exception as exc:  # pragma: no cover
            self.status = VirtualCamStatus(False, error=f"缺少 pyvirtualcam: {exc}")
            return

        last_err = ""
        for backend in prefer:
            try:
                self.cam = pyvirtualcam.Camera(width=width, height=height, fps=fps,
                                               fmt=pyvirtualcam.PixelFormat.BGR,
                                               backend=backend, print_fps=False)
                self.status = VirtualCamStatus(True, backend=backend, device=self.cam.device)
                return
            except Exception as exc:
                last_err = f"{backend}: {exc}"
        self.status = VirtualCamStatus(False, error=last_err or "未找到可用虚拟摄像头")

    def send(self, frame_bgr: np.ndarray) -> None:
        if self.cam is not None:
            try:
                self.cam.send(frame_bgr)
            except Exception:
                pass

    def close(self) -> None:
        if self.cam is not None:
            try:
                self.cam.close()
            except Exception:
                pass
            self.cam = None


class CaptureWorker:
    """采集 -> 美颜 -> 预览/推流 的后台线程。"""

    def __init__(self, settings: AppSettings, params: BeautyParams,
                 on_stats=None, source: str | int | None = None):
        self.settings = settings
        self.params = params
        self.on_stats = on_stats
        self.source = source if source is not None else settings.camera_index
        self.pipeline = BeautyPipeline()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.virtual: VirtualOut | None = None
        self.error: str = ""
        self.fps_actual: float = 0.0
        self.started = False

    # ------------------------------------------------------------------ 控制
    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="beauty-cam", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.started = False

    # ------------------------------------------------------------------ 主循环
    def _run(self) -> None:
        src = self.source
        # 支持三种源：摄像头序号 / 视频文件路径 / 任何带 read() 的对象（演示模式）
        if hasattr(src, "read"):
            cap = src
        elif isinstance(src, int):
            cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            self.error = f"无法打开视频源: {src}"
            return

        if isinstance(src, int) and hasattr(cap, "set"):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.height)
            cap.set(cv2.CAP_PROP_FPS, self.settings.fps)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        ok, frame = cap.read()
        if not ok or frame is None:
            self.error = "视频源没有返回画面"
            cap.release()
            return

        h, w = frame.shape[:2]
        if self.settings.virtual_cam:
            self.virtual = VirtualOut(w, h, self.settings.fps)

        self.started = True
        win = "BeautyCam 预览（按 q 或 ESC 关闭预览）"
        frames = 0
        t_last = time.perf_counter()
        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    time.sleep(0.005)
                    continue
                if frame.shape[1] != w or frame.shape[0] != h:
                    frame = cv2.resize(frame, (w, h))
                if self.settings.mirror:
                    frame = cv2.flip(frame, 1)

                out = self.pipeline.process(frame, self.params)

                if self.virtual is not None:
                    self.virtual.send(out)

                frames += 1
                now = time.perf_counter()
                if now - t_last >= 0.5:
                    self.fps_actual = frames / (now - t_last)
                    frames = 0
                    t_last = now
                    if self.on_stats:
                        self.on_stats(self.fps_actual, self.pipeline.last_ms)

                if self.settings.show_preview:
                    try:
                        cv2.imshow(win, out)
                        if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                            self._stop.set()
                    except Exception:
                        pass
        finally:
            cap.release()
            if self.virtual is not None:
                self.virtual.close()
            try:
                cv2.destroyWindow(win)
            except Exception:
                pass
            self.started = False
