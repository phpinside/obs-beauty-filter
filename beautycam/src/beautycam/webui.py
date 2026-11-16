"""内置 Web 控制面板（只用标准库 http.server，不依赖 tkinter/Qt）。

为什么不用 tkinter：官方 Python 安装包带 tk，但很多嵌入式/精简发行版没有，
而且 tk 的观感也一般。用本机浏览器当 UI，零依赖、好打包、跨机器一致。
"""
from __future__ import annotations

import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .camera import CaptureWorker, list_cameras
from .params import AppSettings, BeautyParams, save_settings


def _asset_dir() -> str:
    base = getattr(sys, "_MEIPASS", None)
    here = os.path.dirname(os.path.abspath(__file__))
    if base:
        p = os.path.join(base, "beautycam", "assets", "web")
        if os.path.isdir(p):
            return p
    return os.path.join(here, "assets", "web")


class Controller:
    """面板与采集线程之间的唯一状态持有者。"""

    def __init__(self, settings: AppSettings, source=None):
        self.settings = settings
        self.params = settings.beauty
        self.source = source
        self.worker: CaptureWorker | None = None
        self.devices: list[tuple[int, str]] = []
        self.last_error = ""
        self.refresh_devices()

    # ---------------------------------------------------------------- 设备
    def refresh_devices(self) -> None:
        if self.source is not None:                 # --demo / --source 模式
            self.devices = [(0, "演示源" if not isinstance(self.source, str)
                             else os.path.basename(self.source))]
            return
        try:
            self.devices = list_cameras()
        except Exception:
            self.devices = []

    # ---------------------------------------------------------------- 状态
    @property
    def running(self) -> bool:
        return self.worker is not None and self.worker.started

    def state(self) -> dict:
        return {
            "running": self.running,
            "beauty": {
                "enabled": self.params.enabled,
                "smooth": self.params.smooth,
                "whiten": self.params.whiten,
                "rosy": self.params.rosy,
                "sharpen": self.params.sharpen,
                "slim": self.params.slim,
                "eye": self.params.eye,
                "auto_face": self.params.auto_face,
                "process_scale": self.params.process_scale,
            },
            "mirror": self.settings.mirror,
            "show_preview": self.settings.show_preview,
            "virtual_cam": self.settings.virtual_cam,
            "width": self.settings.width,
            "height": self.settings.height,
            "fps": self.settings.fps,
            "camera_index": self.settings.camera_index,
            "devices": [[i, n] for i, n in self.devices],
        }

    def stats(self) -> dict:
        w = self.worker
        vcam = ""
        if w is not None and w.virtual is not None:
            st = w.virtual.status
            vcam = (st.backend or "ok") if st.ok else "不可用"
        return {
            "running": self.running,
            "fps": getattr(w, "fps_actual", 0.0) if w else 0.0,
            "ms": w.pipeline.last_ms if w else 0.0,
            "vcam": vcam,
            "error": (w.error if w else "") or self.last_error,
        }

    # ---------------------------------------------------------------- 控制
    def apply(self, payload: dict) -> dict:
        b = payload.get("beauty") or {}
        for key in ("smooth", "whiten", "rosy", "sharpen", "slim", "eye", "process_scale"):
            if key in b:
                setattr(self.params, key, float(b[key]))
        if "enabled" in b:
            self.params.enabled = bool(b["enabled"])
        if "auto_face" in b:
            self.params.auto_face = bool(b["auto_face"])
        self.params.clamp()

        for key in ("mirror", "show_preview", "virtual_cam"):
            if key in payload:
                setattr(self.settings, key, bool(payload[key]))
        for key in ("width", "height", "fps", "camera_index"):
            if key in payload:
                setattr(self.settings, key, int(payload[key]))
        return self.state()

    def start(self) -> dict:
        if self.running:
            return self.state()
        self.last_error = ""
        src = self.source if self.source is not None else self.settings.camera_index
        self.worker = CaptureWorker(self.settings, self.params, source=src)
        self.worker.start()
        return self.state()

    def stop(self) -> dict:
        if self.worker is not None:
            self.worker.stop()
            self.last_error = self.worker.error or self.last_error
            self.worker = None
        return self.state()

    def save(self) -> dict:
        save_settings(self.settings)
        return self.state()

    def reset(self) -> dict:
        d = BeautyParams()
        for key in ("smooth", "whiten", "rosy", "sharpen", "slim", "eye",
                    "auto_face", "enabled", "process_scale"):
            setattr(self.params, key, getattr(d, key))
        return self.state()


def make_handler(ctl: Controller):
    index_path = os.path.join(_asset_dir(), "index.html")

    class Handler(BaseHTTPRequestHandler):
        server_version = "BeautyCam/1.0"

        def log_message(self, *args):        # 静音访问日志
            pass

        # -------------------------------------------------------- 工具
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj: dict) -> None:
            self._send(200, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

        def _body(self) -> dict:
            try:
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return {}

        # -------------------------------------------------------- 路由
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                try:
                    with open(index_path, "rb") as fh:
                        self._send(200, fh.read(), "text/html; charset=utf-8")
                except OSError:
                    self._send(500, b"index.html missing", "text/plain")
            elif self.path == "/api/state":
                self._json(ctl.state())
            elif self.path == "/api/stats":
                self._json(ctl.stats())
            elif self.path == "/favicon.ico":
                self._send(204, b"", "image/x-icon")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path == "/api/params":
                self._json(ctl.apply(self._body()))
            elif self.path == "/api/control":
                action = (self._body() or {}).get("action")
                self._json(ctl.start() if action == "start" else ctl.stop())
            elif self.path == "/api/devices":
                ctl.refresh_devices()
                self._json(ctl.state())
            elif self.path == "/api/save":
                self._json(ctl.save())
            elif self.path == "/api/reset":
                self._json(ctl.reset())
            else:
                self._send(404, b"not found", "text/plain")

    return Handler


def run(settings: AppSettings, source=None, port: int = 0,
        open_browser: bool = True, quiet: bool = False) -> int:
    ctl = Controller(settings, source=source)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(ctl))
    url = f"http://127.0.0.1:{httpd.server_port}/"
    if not quiet:
        print(f"[BeautyCam] 控制面板: {url}")
        print("[BeautyCam] 关闭这个窗口或按 Ctrl+C 即退出")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ctl.stop()
        httpd.server_close()
    return 0
