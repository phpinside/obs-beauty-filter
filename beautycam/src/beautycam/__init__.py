"""BeautyCam —— 开源美颜摄像头（OpenCV 自研算法，不依赖任何商业美颜 SDK）。"""

__version__ = "1.0.0"
APP_NAME = "BeautyCam 美颜摄像头"

from .params import AppSettings, BeautyParams, load_settings, save_settings  # noqa: E402,F401
from .pipeline import BeautyPipeline  # noqa: E402,F401

__all__ = [
    "__version__",
    "APP_NAME",
    "AppSettings",
    "BeautyParams",
    "load_settings",
    "save_settings",
    "BeautyPipeline",
]
