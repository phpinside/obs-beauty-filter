"""自测与性能基准：不需要摄像头也能验证算法是否真的生效。"""
from __future__ import annotations

import os
import time

import cv2
import numpy as np

from .params import BeautyParams
from .pipeline import BeautyPipeline


def synth_portrait(w: int = 1280, h: int = 720, seed: int = 7) -> np.ndarray:
    """合成一张“人像”测试图：肤色椭圆 + 毛孔噪声 + 五官。

    用途是让磨皮/美白/瘦脸的效果可以被量化测量，
    而不是靠肉眼看视频流。
    """
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (58, 48, 42)                                     # 背景（深灰蓝）

    cx, cy = int(w * 0.5), int(h * 0.46)
    rx, ry = int(w * 0.17), int(h * 0.30)
    cv2.ellipse(img, (cx, cy + int(ry * 0.55)), (int(rx * 1.25), int(ry * 0.95)),
                0, 0, 360, (72, 62, 55), -1)                  # 脖子/肩
    cv2.ellipse(img, (cx, cy), (rx, ry), 0, 0, 360, (176, 197, 228), -1)   # 脸（BGR 肤色）

    # 皮肤纹理：高频噪声 + 少量色斑，用来衡量磨皮强度
    tex = rng.normal(0, 9.0, (h, w, 1)).repeat(3, axis=2)
    mask_face = np.zeros((h, w), np.uint8)
    cv2.ellipse(mask_face, (cx, cy), (rx, ry), 0, 0, 360, 255, -1)
    face = img.astype(np.float32) + tex * (mask_face[..., None] / 255.0)
    img = np.clip(face, 0, 255).astype(np.uint8)

    # 五官
    ery = int(ry * 0.10)
    for sign in (-1, 1):
        ex = cx + int(sign * rx * 0.42)
        ey = cy - int(ry * 0.22)
        cv2.ellipse(img, (ex, ey), (int(rx * 0.20), ery), 0, 0, 360, (245, 245, 245), -1)
        cv2.circle(img, (ex, ey), int(ery * 0.55), (40, 35, 30), -1)
        cv2.circle(img, (ex - 2, ey - 2), max(1, int(ery * 0.18)), (255, 255, 255), -1)
        # 眉毛
        cv2.ellipse(img, (ex, ey - int(ry * 0.15)), (int(rx * 0.22), max(3, int(ry * 0.035))),
                    0, 200, 340, (60, 55, 55), -1)
    cv2.ellipse(img, (cx, cy + int(ry * 0.52)), (int(rx * 0.28), int(ry * 0.07)),
                0, 0, 360, (110, 95, 190), -1)                  # 唇
    cv2.ellipse(img, (cx, cy + int(ry * 0.12)), (int(rx * 0.10), int(ry * 0.10)),
                0, 0, 360, (150, 175, 205), -1)                 # 鼻影
    # 头发
    cv2.ellipse(img, (cx, cy - int(ry * 0.42)), (int(rx * 1.18), int(ry * 0.62)),
                0, 180, 360, (35, 30, 28), -1)
    return img


def _hf_energy(img: np.ndarray, box: tuple[int, int, int, int]) -> float:
    x, y, w, h = box
    roi = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2GRAY).astype(np.float32)
    lap = cv2.Laplacian(roi, cv2.CV_32F, ksize=3)
    return float(np.mean(np.abs(lap)))


def _mean_l(img: np.ndarray, box: tuple[int, int, int, int]) -> float:
    x, y, w, h = box
    roi = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2LAB)
    return float(np.mean(roi[..., 0]))


def run_selftest(out_dir: str = ".", frames: int = 24, verbose: bool = True) -> dict:
    """返回可断言的指标字典。"""
    os.makedirs(out_dir, exist_ok=True)
    src = synth_portrait()
    h, w = src.shape[:2]
    box = (int(w * 0.33), int(h * 0.16), int(w * 0.34), int(h * 0.60))

    params = BeautyParams(smooth=0.75, whiten=0.45, rosy=0.30, sharpen=0.35, slim=0.35)
    pipe = BeautyPipeline()

    # 预热（让缓存映射表就位）
    pipe.process(src, params)

    t0 = time.perf_counter()
    for _ in range(frames):
        out = pipe.process(src, params)
    dt = time.perf_counter() - t0

    disabled = BeautyParams(enabled=False)
    raw = pipe.process(src, disabled)

    hf_before, hf_after = _hf_energy(raw, box), _hf_energy(out, box)
    l_before, l_after = _mean_l(raw, box), _mean_l(out, box)

    cv2.imwrite(os.path.join(out_dir, "selftest_before.png"), raw)
    cv2.imwrite(os.path.join(out_dir, "selftest_after.png"), out)
    cv2.imwrite(os.path.join(out_dir, "selftest_compare.png"),
                BeautyPipeline.side_by_side(raw, out))

    # 瘦脸效果：在“额头”高度量脸的宽度（此处只有头部椭圆，不会被脖子干扰）
    def face_width(img: np.ndarray) -> int:
        from .imgops import skin_mask
        m = (skin_mask(img) > 0.5).astype(np.uint8)
        y0, y1 = int(h * 0.28), int(h * 0.32)
        rows = m[y0:y1]
        cols = np.where(rows.any(axis=0))[0]
        return int(cols[-1] - cols[0]) if len(cols) else 0

    metrics = {
        "frames": frames,
        "ms_per_frame": round(dt / frames * 1000, 2),
        "fps": round(frames / dt, 1),
        "hf_before": round(hf_before, 2),
        "hf_after": round(hf_after, 2),
        "hf_drop_pct": round((1 - hf_after / max(hf_before, 1e-6)) * 100, 1),
        "l_before": round(l_before, 2),
        "l_after": round(l_after, 2),
        "l_gain": round(l_after - l_before, 2),
        "face_width_before": face_width(raw),
        "face_width_after": face_width(out),
        "out_dir": os.path.abspath(out_dir),
    }
    if verbose:
        print("== BeautyCam 自测 ==")
        for k, v in metrics.items():
            print(f"  {k:20s} {v}")
        print(f"  对比图: {os.path.join(metrics['out_dir'], 'selftest_compare.png')}")

    import json
    with open(os.path.join(out_dir, "selftest_metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, ensure_ascii=False, indent=2)
    return metrics


if __name__ == "__main__":
    run_selftest()
