"""底层图像算子：保边平滑、肤色掩膜、色调调整、椭圆变形。

这里刻意不依赖任何第三方美颜 SDK，全部用 OpenCV / NumPy 实现，
好处是可以自由分发、离线运行，也不受商业 SDK 的授权限制。

性能约定：
  * “计算量大但结果平滑”的部分（肤色掩膜、引导层）在 1/2 ~ 1/4 分辨率上算，再放大；
  * 全分辨率只做 1~2 遍原地运算，避免反复分配 11MB 的临时数组。
720p 在 8 核笔记本上约 25~35ms/帧。
"""
from __future__ import annotations

import cv2
import numpy as np

SKIN_SCALE = 4        # 肤色掩膜的工作分辨率（1/4）
GUIDE_SCALE = 2       # 引导滤波的工作分辨率（1/2）


def _box(img: np.ndarray, radius: int) -> np.ndarray:
    k = 2 * radius + 1
    return cv2.boxFilter(img, -1, (k, k), normalize=True, borderType=cv2.BORDER_REFLECT)


def guided_filter(guide: np.ndarray, src: np.ndarray, radius: int, eps: float) -> np.ndarray:
    """单通道引导滤波：O(1)/像素，比 bilateral 快一个数量级。"""
    r = max(1, int(radius))
    mean_i = _box(guide, r)
    mean_p = _box(src, r)
    corr_i = _box(guide * guide, r)
    corr_ip = _box(guide * src, r)
    var_i = corr_i - mean_i * mean_i
    cov_ip = corr_ip - mean_i * mean_p
    a = cov_ip / (var_i + eps)
    b = mean_p - a * mean_i
    return _box(a, r) * guide + _box(b, r)


def luma(bgr: np.ndarray) -> np.ndarray:
    """BT.601 亮度（输入 float32 BGR 0..255，输出单通道 HxW）。"""
    out = cv2.transform(bgr, np.array([[0.114, 0.587, 0.299]], np.float32))
    return out if out.ndim == 2 else out[..., 0]


def skin_mask(bgr_u8: np.ndarray, cr: float = 0.55, cb: float = 0.45,
              feather: int = 0) -> np.ndarray:
    """YCrCb 肤色概率掩膜，输出 float32 0..1（全分辨率）。

    在 1/4 分辨率上做阈值 + 羽化，放大回来 —— 掩膜本身就是低频的，
    肉眼看不出差别，但快 10 倍以上。
    """
    h, w = bgr_u8.shape[:2]
    sw, sh = max(32, w // SKIN_SCALE), max(32, h // SKIN_SCALE)
    small = cv2.resize(bgr_u8, (sw, sh), interpolation=cv2.INTER_AREA)
    ycc = cv2.cvtColor(small, cv2.COLOR_BGR2YCrCb)

    cr_lo, cr_hi = 133.0 - 12.0 * (1.0 - cr), 173.0 + 12.0 * cr
    cb_lo, cb_hi = 77.0 - 12.0 * (1.0 - cb), 127.0 + 12.0 * cb
    m = cv2.inRange(ycc, (28, int(cr_lo), int(cb_lo)), (246, int(cr_hi), int(cb_hi)))

    sigma = feather if feather > 0 else max(1.6, sw * 0.012)
    m = cv2.GaussianBlur(m, (0, 0), sigma)
    m_f = m.astype(np.float32) * (1.0 / 255.0)
    return cv2.resize(m_f, (w, h), interpolation=cv2.INTER_LINEAR)


def _guide_gain(bgr_f32: np.ndarray, strength: float) -> np.ndarray:
    """在低分辨率算“平滑亮度 / 原亮度”，返回与输入同尺寸的增益图（单通道）。"""
    h, w = bgr_f32.shape[:2]
    sw, sh = max(64, w // GUIDE_SCALE), max(64, h // GUIDE_SCALE)
    small = cv2.resize(bgr_f32, (sw, sh), interpolation=cv2.INTER_AREA)
    g = luma(small)

    radius = max(2, int(min(sw, sh) * 0.012 + strength * min(sw, sh) * 0.014))
    base = guided_filter(g, g, radius, 90.0)
    gain_small = base / np.maximum(g, 1.0)

    return cv2.resize(gain_small, (w, h), interpolation=cv2.INTER_LINEAR)


def smooth_base(bgr_f32: np.ndarray, strength: float) -> np.ndarray:
    """返回“只保留低频”的版本（新数组），供上层按掩膜做混合。

    先把每个通道乘上柔化后的亮度增益：皮肤被压平，五官边缘因为增益≈1 保留。
    """
    gain = _guide_gain(bgr_f32, strength)
    if not np.isfinite(gain).all():
        gain = np.nan_to_num(gain, nan=1.0, posinf=1.0, neginf=1.0)
    out = cv2.multiply(bgr_f32, cv2.merge([gain, gain, gain]))
    return out


def smooth(bgr_f32: np.ndarray, mask: np.ndarray, strength: float,
           radius: int = 0, eps: float = 120.0) -> np.ndarray:
    """保边磨皮（原地修改并返回）：按 strength*mask 向低频版本靠拢。"""
    if strength <= 0.001:
        return bgr_f32
    base = smooth_base(bgr_f32, strength)
    k = mask * strength
    res = cv2.blendLinear(bgr_f32, base, 1.0 - k, k)
    np.copyto(bgr_f32, res)
    return bgr_f32


_CONST_CACHE: dict[tuple, np.ndarray] = {}
WARM_COLOR = (188.0, 175.0, 202.0)   # BGR：偏红的暖肤色，用于“红润”


def _const_image(h: int, w: int, color: tuple[float, float, float]) -> np.ndarray:
    """常量色图缓存：blendLinear 需要同尺寸的第二张图，每帧新建 11MB 太浪费。"""
    key = (h, w, color)
    arr = _CONST_CACHE.get(key)
    if arr is None:
        if len(_CONST_CACHE) > 6:
            _CONST_CACHE.clear()
        arr = np.empty((h, w, 3), np.float32)
        arr[:] = color
        _CONST_CACHE[key] = arr
    return arr


def tone(bgr_f32: np.ndarray, mask: np.ndarray, whiten: float, rosy: float) -> np.ndarray:
    """美白 + 红润：都表达成“按掩膜向某个色偏做混合”，交给 blendLinear 一次算完。

    返回新数组（blendLinear 无法原地）。比原来的逐通道加减法快约 3 倍。
    """
    if whiten <= 0.001 and rosy <= 0.001:
        return bgr_f32
    h, w = bgr_f32.shape[:2]

    if whiten > 0.001:
        t = mask * (whiten * 0.34)
        white = _const_image(h, w, (255.0, 255.0, 255.0))
        bgr_f32 = cv2.blendLinear(bgr_f32, white, 1.0 - t, t)

    if rosy > 0.001:
        g = luma(bgr_f32)
        # 中间调权重：0.55 附近最重，过暗过亮都不加
        mid = np.abs(g * (1.0 / 255.0) - 0.55)
        mid *= -1.0 / 0.45
        mid += 1.0
        np.clip(mid, 0, 1, out=mid)
        wgt = mid * mask * (rosy * 0.55)
        warm = _const_image(h, w, WARM_COLOR)
        bgr_f32 = cv2.blendLinear(bgr_f32, warm, 1.0 - wgt, wgt)

    return bgr_f32


def whiten(bgr_f32: np.ndarray, mask: np.ndarray, amount: float) -> np.ndarray:
    """兼容旧接口：只做美白。"""
    return tone(bgr_f32, mask, amount, 0.0)


def rosy(bgr_f32: np.ndarray, mask: np.ndarray, amount: float) -> np.ndarray:
    """兼容旧接口：只做红润。"""
    return tone(bgr_f32, mask, 0.0, amount)


def sharpen_u8(img_u8: np.ndarray, amount: float, sigma: float = 1.0) -> np.ndarray:
    """在 uint8 域做 USM：全图锐化，放在磨皮之前，皮肤随后会被磨掉，不会放大毛孔。

    uint8 的 GaussianBlur + addWeighted 比 float32 三通道版本快 4 倍左右。
    """
    if amount <= 0.001:
        return img_u8
    blur = cv2.GaussianBlur(img_u8, (0, 0), sigma, borderType=cv2.BORDER_REFLECT)
    a = amount * 0.9
    return cv2.addWeighted(img_u8, 1.0 + a, blur, -a, 0.0)


def sharpen(bgr_f32: np.ndarray, mask: np.ndarray, amount: float) -> np.ndarray:
    """浮点域 USM（保留给自测/接口兼容）：只对亮度做 3x3 模糊再加回三个通道。"""
    if amount <= 0.001:
        return bgr_f32
    L = luma(bgr_f32)
    blur = cv2.blur(L, (3, 3), borderType=cv2.BORDER_REFLECT)
    detail = L - blur

    k = 1.0 - mask * 0.75
    k *= amount * 1.1
    detail *= k
    cv2.add(bgr_f32, cv2.merge([detail, detail, detail]), dst=bgr_f32)
    return bgr_f32


def warp_maps(h: int, w: int, slim: float, eye: float,
              cx: float, cy: float, rx: float, ry: float,
              scale: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """生成瘦脸 / 大眼的 remap 查找表（输出坐标 -> 源坐标）。

    在 1/scale 分辨率上算位移场再放大：位移场是平滑的，放大后无可见误差，
    但建表时间从 ~40ms 降到 ~6ms（只在参数变化时重建）。
    """
    if scale > 1:
        sh, sw = max(16, h // scale), max(16, w // scale)
    else:
        sh, sw = h, w

    xs = (np.arange(sw, dtype=np.float32) + 0.5) / sw
    ys = (np.arange(sh, dtype=np.float32) + 0.5) / sh
    gx = np.broadcast_to(xs, (sh, sw)).copy()
    gy = np.broadcast_to(ys[:, None], (sh, sw)).copy()

    map_x = gx
    map_y = gy

    if abs(slim) > 0.001:
        dx = (gx - cx) * (1.0 / max(rx, 1e-3))
        dy = (gy - cy) * (1.0 / max(ry, 1e-3))
        r2 = dx * dx + dy * dy
        fall = np.clip(1.0 - r2, 0.0, 1.0)
        fall = np.power(fall, 1.3)      # 指数越小，靠边缘的收缩越明显（轮廓才会真的变窄）
        k = fall * (slim * 0.34)
        k += 1.0
        map_x = cx + (gx - cx) * k

    if eye > 0.001:
        for sign in (-1.0, 1.0):
            ex = cx + sign * rx * 0.62
            ey = cy - ry * 0.30
            erx, ery = max(rx * 0.30, 1e-3), max(ry * 0.20, 1e-3)
            ddx = (gx - ex) * (1.0 / erx)
            ddy = (gy - ey) * (1.0 / ery)
            r2 = ddx * ddx + ddy * ddy
            fall = np.clip(1.0 - r2, 0.0, 1.0)
            fall *= fall
            k = 1.0 - fall * (eye * 0.16)
            map_x = ex + (map_x - ex) * k
            map_y = ey + (map_y - ey) * k

    if scale > 1:
        map_x = cv2.resize(map_x, (w, h), interpolation=cv2.INTER_LINEAR)
        map_y = cv2.resize(map_y, (w, h), interpolation=cv2.INTER_LINEAR)

    np.clip(map_x, 0.0, 1.0, out=map_x)
    np.clip(map_y, 0.0, 1.0, out=map_y)
    return (map_x * (w - 1)).astype(np.float32), (map_y * (h - 1)).astype(np.float32)
