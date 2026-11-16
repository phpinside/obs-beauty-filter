"""生成 BeautyCam 图标（纯 Python 写 PNG/ICO，不依赖 Pillow）。

运行：python tools/make_icon.py
输出：assets/beautycam.ico（内含 256x256 PNG，Vista+ 可直接用）
"""
from __future__ import annotations

import os
import struct
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "assets")


def _png(width: int, height: int, rgba: np.ndarray) -> bytes:
    raw = b"".join(b"\x00" + rgba[y].tobytes() for y in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def _ico(png: bytes, size: int) -> bytes:
    # ICONDIR + 单个 ICONDIRENTRY + PNG 数据
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0 if size >= 256 else size,
                        0 if size >= 256 else size, 0, 0, 1, 32, len(png), 22)
    return header + entry + png


def build(size: int = 256, ss: int = 3) -> np.ndarray:
    """4 倍超采样画出圆角底 + 渐变圆 + 高光，最后缩回目标尺寸。"""
    n = size * ss
    y, x = np.mgrid[0:n, 0:n]
    fx = (x + 0.5) / n
    fy = (y + 0.5) / n

    img = np.zeros((n, n, 4), np.uint8)

    # 圆角方形底（深色渐变）
    r = 0.22
    dx = np.abs(fx - 0.5) - (0.5 - r)
    dy = np.abs(fy - 0.5) - (0.5 - r)
    dist = np.sqrt(np.maximum(dx, 0) ** 2 + np.maximum(dy, 0) ** 2) - r
    base_a = np.clip(0.5 - dist * n * 0.5, 0, 1)          # 抗锯齿边缘
    top = np.array([44, 38, 52], np.float32)
    bot = np.array([22, 18, 28], np.float32)
    grad = top[None, None, :] * (1 - fy[..., None]) + bot[None, None, :] * fy[..., None]
    img[..., :3] = grad.astype(np.uint8)
    img[..., 3] = (base_a * 255).astype(np.uint8)

    # 中心渐变圆（粉 -> 橙）
    cx, cy, rad = 0.5, 0.485, 0.285
    d = np.sqrt((fx - cx) ** 2 + (fy - cy) ** 2)
    circle_a = np.clip((rad - d) * n * 0.6, 0, 1)

    c1 = np.array([255, 141, 178], np.float32)            # 粉
    c2 = np.array([255, 196, 120], np.float32)            # 暖橙
    t = np.clip((fy - (cy - rad)) / (2 * rad), 0, 1)[..., None]
    cgrad = c1 * (1 - t) + c2 * t
    img[..., :3] = (img[..., :3] * (1 - circle_a[..., None])
                    + cgrad * circle_a[..., None]).astype(np.uint8)

    # 高光弧
    hi = np.clip(1 - np.sqrt((fx - 0.42) ** 2 + (fy - 0.38) ** 2) / 0.16, 0, 1) ** 2
    hi = (hi * circle_a * 0.55)[..., None]
    img[..., :3] = (img[..., :3] * (1 - hi) + 255 * hi).astype(np.uint8)

    # 三颗小闪光，暗示“美颜/提亮”
    for (sx, sy, sr, a) in ((0.735, 0.235, 0.045, 0.95),
                            (0.795, 0.345, 0.028, 0.8),
                            (0.215, 0.745, 0.033, 0.75)):
        dd = np.sqrt((fx - sx) ** 2 + (fy - sy) ** 2)
        star = np.clip((sr - dd) * n * 0.6, 0, 1) * a
        img[..., :3] = (img[..., :3] * (1 - star[..., None])
                        + 255 * star[..., None]).astype(np.uint8)

    # 降采样
    k = ss
    small = img.reshape(size, k, size, k, 4).astype(np.float32).mean(axis=(1, 3))
    return small.clip(0, 255).astype(np.uint8)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    png = _png(256, 256, build())
    ico_path = os.path.join(OUT_DIR, "beautycam.ico")
    with open(ico_path, "wb") as fh:
        fh.write(_ico(png, 256))
    png_path = os.path.join(OUT_DIR, "beautycam.png")
    with open(png_path, "wb") as fh:
        fh.write(png)
    print("生成:", ico_path, os.path.getsize(ico_path), "bytes")
    print("生成:", png_path, os.path.getsize(png_path), "bytes")


if __name__ == "__main__":
    main()
