# -*- coding: utf-8 -*-
"""播放器进程：渲染壁纸/屏保网页窗口。

架构参考 Lively（主程序 + 独立播放器进程）：
- mode=wallpaper: 窗口嵌入桌面壁纸层（WorkerW/Progman），随主程序常驻
- mode=screensaver: 全屏置顶自绘窗口，任意键鼠输入即退出（不用系统屏保）

渲染引擎：pywebview EdgeChromium(WebView2)。已验证 SetParent 后渲染正常
（QtWebEngine 在 reparent 后渲染停止，旧版因此失败的教训）。
"""
import ctypes
import logging
import os
import sys
import threading
import time
from ctypes import wintypes

log = logging.getLogger("player")

WINDOW_TITLE = {"wallpaper": "CountdownWallpaper", "screensaver": "CountdownScreensaver"}


def _setup_logging(mode: str) -> None:
    from . import config
    path = os.path.join(config.config_dir(), "player-%s.log" % mode)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        filename=path,
        encoding="utf-8",
    )


def _find_own_window(title: str):
    from . import win32
    mypid = os.getpid()
    found = [0]

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        pid = wintypes.DWORD()
        win32.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == mypid:
            buf = ctypes.create_unicode_buffer(512)
            win32.user32.GetWindowTextW(hwnd, buf, 512)
            if buf.value == title:
                found[0] = hwnd
                return False
        return True

    win32.user32.EnumWindows(cb, 0)
    return found[0]


def run(mode: str) -> None:
    _setup_logging(mode)
    from . import config, win32, media
    import webview

    win32.set_process_dpi_awareness()
    cfg = config.load()
    title = WINDOW_TITLE[mode]
    url = cfg[mode]["url"]
    x, y, w, h = win32.virtual_screen()

    kind, src, local = media.resolve(url)
    if local is not None:
        _KEEP_LOCAL[mode] = local
    log.info("starting player mode=%s url=%s kind=%s rect=%s", mode, url, kind, (x, y, w, h))

    html = media.build_html(kind, src) if kind in ("video", "anim", "image") else None
    window = webview.create_window(
        title, src if html is None else "", html=html,
        width=w, height=h, x=x, y=y, frameless=True)

    def on_shown():
        try:
            _on_shown(mode, window)
        except Exception:
            log.exception("on_shown failed")

    window.events.shown += on_shown

    webview.start(gui="edgechromium", private_mode=False)
    log.info("player loop exited mode=%s", mode)


_KEEP_LOCAL = {}


def _on_shown(mode: str, window) -> None:
    from . import win32
    time.sleep(0.3)
    hwnd = _find_own_window(WINDOW_TITLE[mode])
    if not hwnd:
        log.error("own window not found")
        window.destroy()
        return
    x, y, w, h = win32.virtual_screen()

    if mode == "wallpaper":
        host_info = win32.find_desktop_host()
        log.info("host=0x%x raised=%s", host_info["host"], host_info["raised"])
        win32.attach_to_desktop(hwnd, host_info, x, y, w, h)
        log.info("wallpaper attached")
    else:
        # 屏保：全屏置顶 + 隐藏光标与任务栏 + 输入监听退出
        win32.set_ex_style(hwnd, add=win32.WS_EX_TOOLWINDOW | win32.WS_EX_NOACTIVATE,
                           remove=win32.WS_EX_APPWINDOW)
        _hide_taskbar(True)
        # 先隐藏任务栏再 maximize：最大化按整显示器计算，绕过工作区夹边；
        # SetWindowPos 单独用会被 Qt 夹到工作区附近尺寸（实测 3824x1707 vs 3840x1746）
        win32.maximize(hwnd)
        win32.topmost_fullscreen(hwnd, x, y, w, h)
        win32.user32.ShowCursor(False)
        log.info("screensaver shown")

        def watch_input():
            time.sleep(1.0)  # 启动瞬间的输入不触发退出
            while True:
                if win32.last_input_idle_seconds() < 0.5:
                    log.info("user input detected, exiting screensaver")
                    break
                time.sleep(0.2)
            _hide_taskbar(False)
            win32.user32.ShowCursor(True)
            window.destroy()

        threading.Thread(target=watch_input, daemon=True).start()


def _hide_taskbar(hide: bool) -> None:
    from . import win32
    tray = win32.user32.FindWindowW("Shell_TrayWnd", None)
    if tray:
        win32.user32.ShowWindow(tray, win32.SW_HIDE if hide else 5)  # 5=SW_SHOW


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "wallpaper")
