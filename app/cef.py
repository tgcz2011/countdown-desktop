# -*- coding: utf-8 -*-
"""CEF helper 引擎：spawn helper 进程，控制壁纸嵌入与屏保全屏"""
import ctypes
import logging
import os
import subprocess
import sys
import time
from ctypes import wintypes

from . import desktop

log = logging.getLogger("cef")

user32 = ctypes.windll.user32


def _app_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def helper_dir() -> str:
    """helper 所在目录（打包后 exe 目录，开发时 third_party/cef_helper）"""
    base = _app_base_dir()
    if os.path.exists(os.path.join(base, "cef_helper.exe")):
        return base
    dev = os.path.join(base, "third_party", "cef_helper")
    if os.path.exists(os.path.join(dev, "cef_helper.exe")):
        return dev
    return base


class CEFEngine:
    """管理一个 cef_helper 进程"""

    def __init__(self):
        self.proc = None
        self.hwnd = 0
        self.url = ""
        self.mode = None  # "wallpaper" | "screensaver"

    def _spawn(self, url, width, height, x=0, y=0, visible=False):
        self.stop()
        hdir = helper_dir()
        exe = os.path.join(hdir, "cef_helper.exe")
        if not os.path.exists(exe):
            log.error("cef_helper.exe not found in %s", hdir)
            return False
        self.proc = subprocess.Popen(
            [exe, f"--url={url}", f"--width={width}", f"--height={height}",
             f"--x={x}", f"--y={y}"] + (["--visible"] if visible else []),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            cwd=hdir)
        self.url = url
        self.hwnd = 0
        for _ in range(30):
            if self.proc.poll() is not None:
                log.error("helper exited early")
                return False
            line = self.proc.stdout.readline()
            if not line:
                time.sleep(0.5)
                continue
            line = line.strip()
            if line.startswith("HWND:"):
                try:
                    self.hwnd = int(line[5:], 16)
                except ValueError:
                    pass
                break
        if not self.hwnd:
            log.error("no HWND from helper")
            return False
        log.info("helper hwnd=0x%x url=%s", self.hwnd, url)
        return True

    def start_wallpaper(self, url, width, height):
        """壁纸：helper 隐藏创建 -> 嵌入桌面 -> 显示（Lively 流程）"""
        if not self._spawn(url, width, height):
            return False
        try:
            host_info = desktop.find_desktop_host()
            log.info("wallpaper host=0x%x raised=%s",
                     host_info["host"], host_info["raised"])

            desktop.make_child_window(self.hwnd)
            desktop.set_window_ex_style(
                self.hwnd,
                add=desktop.WS_EX_TOOLWINDOW | desktop.WS_EX_NOACTIVATE,
                remove=desktop.WS_EX_APPWINDOW)
            user32.SetParent(self.hwnd, host_info["host"])
            user32.SetWindowPos(self.hwnd, 1, 0, 0, width, height,
                                desktop.SWP_NOACTIVATE)
            user32.ShowWindow(self.hwnd, 8)
            user32.ShowWindow(self.hwnd, 9)  # restore from minimized

            # Lively RefreshDesktop: 重新发送 0x052C 刷新桌面层
            time.sleep(1)
            progman = desktop.find_progman()
            user32.SendMessageTimeoutW(progman, 0x052C, 0xD, 0x1, 0, 1000, None)
            user32.SetWindowPos(self.hwnd, 1, 0, 0, width, height,
                                desktop.SWP_NOACTIVATE)

            self.mode = "wallpaper"
            log.info("wallpaper embedded to 0x%x", host_info["host"])
            return True
        except Exception as e:
            log.error("wallpaper embed failed: %s", e)
            self.stop()
            return False

    def start_screensaver(self, url, width, height):
        """屏保：helper 顶层全屏置顶窗口（不嵌入桌面）"""
        if not self._spawn(url, width, height, visible=True):
            return False
        try:
            user32.SetWindowPos(self.hwnd, -1, 0, 0, width, height,  # HWND_TOPMOST
                                desktop.SWP_NOACTIVATE)
            user32.ShowWindow(self.hwnd, 9)  # restore
            user32.SetForegroundWindow(self.hwnd)
            user32.ShowCursor(False)
            self.mode = "screensaver"
            log.info("screensaver window topmost")
            return True
        except Exception as e:
            log.error("screensaver start failed: %s", e)
            self.stop()
            return False

    def stop(self):
        if self.proc is not None:
            try:
                if self.proc.poll() is None:
                    self.proc.kill()
                    self.proc.wait(timeout=5)
            except Exception:
                pass
            self.proc = None
        if self.mode == "screensaver":
            user32.ShowCursor(True)
        self.hwnd = 0
        self.mode = None

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None
