"""人脸定位：给瘦脸/大眼提供椭圆框。定位失败时静默回退到手动画框。"""
from __future__ import annotations

import os
import sys

import cv2
import numpy as np


def _cascade_path() -> str | None:
    names = ("haarcascade_frontalface_default.xml", "haarcascade_frontalface_alt2.xml")
    roots = []
    try:
        roots.append(cv2.data.haarcascades)  # type: ignore[attr-defined]
    except Exception:
        pass
    base = getattr(sys, "_MEIPASS", None)
    if base:
        roots.append(os.path.join(base, "cv2", "data"))
        roots.append(os.path.join(base, "beautycam", "assets"))
    here = os.path.dirname(os.path.abspath(__file__))
    roots.append(os.path.join(here, "..", "assets"))
    for root in roots:
        if not root:
            continue
        for name in names:
            p = os.path.join(root, name)
            if os.path.isfile(p):
                return p
    return None


class FaceTracker:
    """每 N 帧检测一次 + 指数平滑，避免框抖动导致画面呼吸。"""

    def __init__(self, detect_interval: int = 6, smoothing: float = 0.35):
        self.detect_interval = detect_interval
        self.smoothing = smoothing
        self._cascade = None
        self._tick = 0
        self._box: tuple[float, float, float, float] | None = None
        path = _cascade_path()
        if path:
            try:
                c = cv2.CascadeClassifier(path)
                if not c.empty():
                    self._cascade = c
            except Exception:
                self._cascade = None

    @property
    def available(self) -> bool:
        return self._cascade is not None

    def update(self, frame_bgr: np.ndarray, fallback: tuple[float, float, float, float]
               ) -> tuple[float, float, float, float]:
        if self._cascade is None:
            return fallback

        self._tick += 1
        if self._tick % self.detect_interval == 1:
            h, w = frame_bgr.shape[:2]
            scale = 320.0 / max(w, 1)
            small = cv2.resize(frame_bgr, (int(w * scale), int(h * scale))) if scale < 1 else frame_bgr
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            faces = self._cascade.detectMultiScale(gray, 1.15, 5, minSize=(48, 48))
            if len(faces) > 0:
                x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])
                sh, sw = small.shape[:2]
                cx = (x + fw / 2) / sw
                cy = (y + fh / 2) / sh
                rx = (fw / 2) / sw * 1.02
                ry = (fh / 2) / sh * 1.02
                # 略微下移，让椭圆覆盖到下巴（瘦脸主要作用区）
                cy += ry * 0.10
                box = (cx, cy, rx, ry)
                if self._box is None:
                    self._box = box
                else:
                    a = self.smoothing
                    self._box = tuple(a * n + (1 - a) * o for n, o in zip(box, self._box))  # type: ignore
            elif self._box is not None and self._tick % (self.detect_interval * 8) == 0:
                self._box = None  # 长时间找不到脸就放弃，回到手动画框

        return self._box or fallback
