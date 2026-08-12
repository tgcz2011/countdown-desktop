# -*- coding: utf-8 -*-
"""媒体源支持：网页 / 视频 / 图片 / 动图 统一走 Chromium 渲染。

- 远程 http(s) 源：直接使用。
- 本地文件：起 127.0.0.1 迷你 HTTP 服务（支持 Range，视频可拖动），
  WebView2 默认禁 file:// 访问，故必须走 http。
- 视频/图片/动图：生成内联 HTML（<video>/<img> 铺满黑底），交给同一渲染管线。
"""
import logging
import os
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("media")

VIDEO_EXT = (".mp4", ".webm", ".m4v", ".mov", ".mkv", ".ogv")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".svg", ".ico")
ANIM_EXT = (".gif",)

_PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;width:100vw;height:100vh;background:#000;overflow:hidden}}
video,img{{position:fixed;left:0;top:0;width:100vw;height:100vh;object-fit:cover}}
</style></head><body>{body}</body></html>"""


def guess_kind(source: str) -> str:
    """page / video / image / anim"""
    low = source.lower().split("?", 1)[0]
    if low.endswith(VIDEO_EXT):
        return "video"
    if low.endswith(ANIM_EXT):
        return "anim"
    if low.endswith(IMAGE_EXT):
        return "image"
    return "page"


def build_html(kind: str, src: str) -> str:
    esc = src.replace("&", "&amp;").replace('"', "&quot;")
    if kind == "video":
        body = ('<video src="%s" autoplay loop muted playsinline '
                'onerror="document.body.innerHTML=\'<div style=color:#888;font:20px sans-serif;padding:40px>video load failed</div>\'">'
                '</video>') % esc
    else:  # image / anim
        body = '<img src="%s" alt="">' % esc
    return _PAGE.format(body=body)


class _FileHandler(BaseHTTPRequestHandler):
    file_path = ""

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        path = self.file_path
        size = os.path.getsize(path)
        start, end = 0, size - 1
        ranged = self.headers.get("Range")
        if ranged and ranged.startswith("bytes="):
            try:
                spec = ranged[6:].split(",")[0]
                a, b = spec.split("-", 1)
                start = int(a) if a else 0
                end = int(b) if b else size - 1
                end = min(end, size - 1)
            except ValueError:
                start, end = 0, size - 1
        self.send_response(206 if ranged else 200)
        ext = os.path.splitext(path)[1].lower()
        mime = {".mp4": "video/mp4", ".webm": "video/webm", ".mkv": "video/x-matroska",
                ".mov": "video/quicktime", ".m4v": "video/mp4", ".ogv": "video/ogg",
                ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
                ".svg": "image/svg+xml", ".ico": "image/x-icon"}.get(ext,
                                                                    "application/octet-stream")
        self.send_header("Content-Type", mime)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if ranged:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)


class LocalSource:
    """为本地媒体文件提供 127.0.0.1 HTTP 服务（进程内常驻）。"""

    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        handler = type("H", (_FileHandler,), {"file_path": self.path})
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_address[1]
        t = threading.Thread(target=self.server.serve_forever, daemon=True)
        t.start()
        name = urllib.parse.quote(os.path.basename(self.path))
        self.url = "http://127.0.0.1:%d/%s" % (self.port, name)
        log.info("local source serving %s at %s", self.path, self.url)


def resolve(source: str):
    """返回 (kind, final_src, local_or_None)。

    - http(s) 源直接使用；
    - 本地存在的文件：起 127.0.0.1 服务，返回实例需保活；
    - 域名样式的串补 https；
    - 路径样式但文件不存在：回退默认网页（避免黑屏）。
    """
    from . import config
    source = source.strip()
    if source.startswith(("http://", "https://")):
        return guess_kind(source), source, None
    if os.path.isfile(source):
        local = LocalSource(source)
        return guess_kind(local.url), local.url, local
    if "\\" in source or ":" in source or "/" in source.split(".")[0]:
        log.warning("local source missing, fallback default: %s", source)
        return "page", config.DEFAULT_URL, None
    if len(source) > 3 and "." in source.split("/")[0]:
        return guess_kind("https://" + source), "https://" + source, None
    log.warning("source unusable, fallback to default: %s", source)
    return "page", config.DEFAULT_URL, None
