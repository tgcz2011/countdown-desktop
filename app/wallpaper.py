# -*- coding: utf-8 -*-
"""壁纸引擎：CEF helper 进程 + WorkerW 嵌入（Lively 同构）"""
import logging

from . import desktop
from .cef import CEFEngine

log = logging.getLogger("wallpaper")


class WallpaperEngine:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.cef = CEFEngine()

    def start(self) -> bool:
        if self.cef.is_running():
            return True
        if not self.cfg.get("wallpaper_enabled"):
            return False
        w, h = desktop.get_screen_size()
        ok = self.cef.start_wallpaper(self.cfg["wallpaper_url"], w, h)
        log.info("wallpaper start -> %s", ok)
        return ok

    def stop(self):
        self.cef.stop()
        log.info("wallpaper stopped")

    def refresh(self):
        was = self.cef.is_running()
        self.cef.stop()
        if was:
            self.start()

    def is_running(self) -> bool:
        return self.cef.is_running()
