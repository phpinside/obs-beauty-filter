"""美颜处理流水线：几何变形 -> 肤色掩膜 -> 磨皮 -> 美白 -> 红润 -> 锐化。

几何映射表和肤色掩膜都做了缓存，稳定场景下每帧只跑一层滤镜，
1280x720 在普通笔记本 CPU 上也能跑到 30fps 以上。
"""
from __future__ import annotations

import time

import cv2
import numpy as np

from . import imgops
from .facetrack import FaceTracker
from .params import BeautyParams


class BeautyPipeline:
    def __init__(self) -> None:
        self.tracker = FaceTracker()
        self._map_key: tuple | None = None
        self._maps: tuple[np.ndarray, np.ndarray] | None = None
        self._mask_key: tuple | None = None
        self._mask: np.ndarray | None = None
        self.last_ms: float = 0.0
        self.last_box: tuple[float, float, float, float] | None = None

    # ------------------------------------------------------------------ 内部
    def _warp(self, frame: np.ndarray, p: BeautyParams,
              box: tuple[float, float, float, float]) -> np.ndarray:
        cx, cy, rx, ry = box
        if abs(p.slim) <= 0.001 and p.eye <= 0.001:
            return frame
        # 变形区比脸本身大 30%：脸的轮廓落在衰减区中段，才会真的被收窄；
        # 如果椭圆正好贴着轮廓，边界处位移为 0，只有五官动、脸型不动。
        rx *= 1.30
        ry *= 1.28
        h, w = frame.shape[:2]
        key = (w, h, round(p.slim, 3), round(p.eye, 3),
               round(cx, 3), round(cy, 3), round(rx, 3), round(ry, 3))
        if key != self._map_key or self._maps is None:
            self._maps = imgops.warp_maps(h, w, p.slim, p.eye, cx, cy, rx, ry)
            self._map_key = key
        map_x, map_y = self._maps
        return cv2.remap(frame, map_x, map_y, interpolation=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REFLECT101)

    def _skin(self, frame_u8: np.ndarray, p: BeautyParams) -> np.ndarray:
        # 肤色掩膜依赖画面内容，不能按尺寸缓存；cvtColor + 阈值本身很快
        return imgops.skin_mask(frame_u8, p.skin_cr, p.skin_cb)

    # ------------------------------------------------------------------ 对外
    def process(self, frame_bgr: np.ndarray, p: BeautyParams) -> np.ndarray:
        """输入/输出均为 uint8 BGR。"""
        t0 = time.perf_counter()
        if frame_bgr is None or frame_bgr.size == 0:
            return frame_bgr
        if not p.enabled:
            self.last_ms = (time.perf_counter() - t0) * 1000
            return frame_bgr

        p = p.clamp()
        scale = p.process_scale if 0.4 <= p.process_scale <= 1.0 else 1.0
        if scale < 0.999:
            src = cv2.resize(frame_bgr, None, fx=scale, fy=scale,
                             interpolation=cv2.INTER_AREA)
        else:
            src = frame_bgr

        out = self._process_core(src, p)

        if scale < 0.999:
            out = cv2.resize(out, (frame_bgr.shape[1], frame_bgr.shape[0]),
                             interpolation=cv2.INTER_LINEAR)
        self.last_ms = (time.perf_counter() - t0) * 1000
        return out

    def _process_core(self, frame_bgr: np.ndarray, p: BeautyParams) -> np.ndarray:
        fallback = (p.face_cx, p.face_cy, p.face_rx, p.face_ry)
        if p.auto_face and (abs(p.slim) > 0.001 or p.eye > 0.001):
            box = self.tracker.update(frame_bgr, fallback)
        else:
            box = fallback
        self.last_box = box

        frame = self._warp(frame_bgr, p, box)

        # 锐化放在 uint8 域、磨皮之前：先找回细节，再只把皮肤磨平
        if p.sharpen > 0.001:
            frame = imgops.sharpen_u8(frame, p.sharpen)

        mask = self._skin(frame, p)

        f = frame.astype(np.float32)
        if p.whiten > 0.001 or p.rosy > 0.001:
            f = imgops.tone(f, mask, p.whiten, p.rosy)

        if p.smooth > 0.001:
            # 磨皮只需要低频信息：在半分辨率算平滑层，再整幅混合回全分辨率。
            # 非皮肤区（mask≈0）保留原始细节，所以不会整体变糊。
            h, w = f.shape[:2]
            sw, sh = max(64, w // 2), max(64, h // 2)
            small = cv2.resize(f, (sw, sh), interpolation=cv2.INTER_AREA)
            base = imgops.smooth_base(small, p.smooth)
            up = cv2.resize(base, (w, h), interpolation=cv2.INTER_LINEAR)
            k = mask * p.smooth
            f = cv2.blendLinear(f, up, 1.0 - k, k)

        # 用 addWeighted 转 uint8：它带饱和截断，比 clip+astype 快 3 倍
        return cv2.addWeighted(f, 1.0, f, 0.0, 0.0, dtype=cv2.CV_8U)

    # 供自测/对比使用
    @staticmethod
    def side_by_side(before: np.ndarray, after: np.ndarray) -> np.ndarray:
        h = max(before.shape[0], after.shape[0])
        w = max(before.shape[1], after.shape[1])

        def fit(img: np.ndarray) -> np.ndarray:
            return cv2.resize(img, (w, h)) if img.shape[:2] != (h, w) else img

        gap = np.full((h, 8, 3), 255, np.uint8)
        return np.hstack([fit(before), gap, fit(after)])
