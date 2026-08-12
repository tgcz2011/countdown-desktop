# -*- coding: utf-8 -*-
"""屏保引擎：CEF 全屏置顶窗口 + 输入监听（非系统屏保）"""
import ctypes
import logging

from PySide6.QtCore import QTimer

from . import desktop
from .cef import CEFEngine

log = logging.getLogger("screensaver")
user32 = ctypes.windll.user32


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_last_input_time() -> int:
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    user32.GetLastInputInfo(ctypes.byref(lii))
    return int(lii.dwTime)


def get_tick_count() -> int:
    return int(ctypes.windll.kernel32.GetTickCount())


def idle_seconds() -> int:
    now = get_tick_count()
    last = get_last_input_time()
    if now < last:
        return 0
    return (now - last) // 1000


class ScreensaverEngine:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.cef = CEFEngine()
        self._poll = QTimer()
        self._poll.setInterval(100)
        self._poll.timeout.connect(self._check_input)
        self._last_input = 0

    def start(self) -> bool:
        if self.cef.is_running():
            return True
        if not self.cfg.get("screensaver_enabled"):
            return False
        url = self.cfg.get("screensaver_url") or "https://zztool.free.nf/countdown"
        w, h = desktop.get_screen_size()
        ok = self.cef.start_screensaver(url, w, h)
        if ok:
            self._last_input = get_last_input_time()
            self._poll.start()
        log.info("screensaver start -> %s", ok)
        return ok

    def stop(self):
        self._poll.stop()
        self.cef.stop()
        log.info("screensaver stopped")

    def _check_input(self):
        cur = get_last_input_time()
        if cur != self._last_input:
            self.stop()
            return
        self._last_input = cur
        for vk in range(0x01, 0x07):
            if user32.GetAsyncKeyState(vk) & 0x8000:
                self.stop()
                return

    def is_running(self) -> bool:
        return self.cef.is_running()
