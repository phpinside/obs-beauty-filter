"""美颜参数模型与配置持久化。"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "BeautyCam")
CONFIG_PATH = os.path.join(CONFIG_DIR, "profile.json")


@dataclass
class BeautyParams:
    """所有强度参数统一用 0..1，方便 UI 滑杆直接绑定。"""

    enabled: bool = True
    smooth: float = 0.55        # 磨皮：保边平滑强度
    whiten: float = 0.30        # 美白：肤色亮度提升
    rosy: float = 0.20          # 红润：气色
    sharpen: float = 0.30       # 锐化：还原五官细节
    slim: float = 0.25          # 瘦脸：椭圆向心变形
    eye: float = 0.0            # 大眼：眼区放大（需人脸定位）
    auto_face: bool = True      # 自动人脸定位（失败回退到手动画框）

    # 手动画框（相对比例：中心 x/y、半径 x/y），auto_face 失效时生效
    face_cx: float = 0.50
    face_cy: float = 0.44
    face_rx: float = 0.22
    face_ry: float = 0.26

    # 肤色保护阈值（YCrCb），默认适合亚洲肤色
    skin_cr: float = 0.55
    skin_cb: float = 0.45

    # 渲染缩放：1.0 = 全分辨率；0.75 = 性能模式（先用 3/4 分辨率算，再放大输出）
    process_scale: float = 0.75

    def clamp(self) -> "BeautyParams":
        for name in ("smooth", "whiten", "rosy", "sharpen", "eye"):
            setattr(self, name, min(1.0, max(0.0, getattr(self, name))))
        self.slim = min(0.8, max(-0.8, self.slim))
        self.face_cx = min(0.95, max(0.05, self.face_cx))
        self.face_cy = min(0.95, max(0.05, self.face_cy))
        self.face_rx = min(0.6, max(0.05, self.face_rx))
        self.face_ry = min(0.6, max(0.05, self.face_ry))
        if not (0.4 <= self.process_scale <= 1.0):
            self.process_scale = 1.0
        return self

    @property
    def active(self) -> bool:
        return self.enabled and any(
            v > 0.001 for v in (self.smooth, self.whiten, self.rosy, self.sharpen, self.eye)
        ) or (self.enabled and abs(self.slim) > 0.001)


@dataclass
class AppSettings:
    """设备与输出相关设置，和 BeautyParams 一起存盘。"""

    camera_index: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    mirror: bool = True
    show_preview: bool = True
    virtual_cam: bool = True
    beauty: BeautyParams = field(default_factory=BeautyParams)


def load_settings(path: str = CONFIG_PATH) -> AppSettings:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        beauty = BeautyParams(**{k: v for k, v in raw.get("beauty", {}).items()
                                 if k in BeautyParams.__dataclass_fields__})
        base = {k: v for k, v in raw.items()
                if k in AppSettings.__dataclass_fields__ and k != "beauty"}
        return AppSettings(beauty=beauty.clamp(), **base)
    except Exception:
        return AppSettings()


def save_settings(settings: AppSettings, path: str = CONFIG_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = asdict(settings)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
