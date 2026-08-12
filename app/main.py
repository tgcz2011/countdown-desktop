# -*- coding: utf-8 -*-
"""Countdown Desktop 入口（Python + CEF 自带 Chromium）

用法:
  countdown-desktop.exe                 # 正常启动（托盘）
  countdown-desktop.exe --test-wallpaper   # 壁纸 25s 自动退出
  countdown-desktop.exe --test-screensaver # 屏保 15s 自动退出
  countdown-desktop.exe --test-settings    # 设置窗口 15s 自动关闭
  countdown-desktop.exe --test-standalone  # 独立 CEF 窗口（调试渲染）
"""
import ctypes
import logging
import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from . import desktop
from .cef import CEFEngine
from .config import load as load_config, save as save_config
from .screensaver import ScreensaverEngine, idle_seconds
from .settings import SettingsDialog
from .tray import TrayIcon
from .wallpaper import WallpaperEngine

APP_VERSION = "2.0.0.0"

log = logging.getLogger("main")


def setup_logging():
    try:
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logging.basicConfig(
            filename=os.path.join(exe_dir, "log.txt"),
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            encoding="utf-8",
        )
    except Exception:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)


def single_instance() -> bool:
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, "CountdownDesktop_SingleInstance")
    return bool(mutex)


def run_test_mode(mode, cfg, wp, ss, app):
    if mode == "wallpaper":
        cfg["wallpaper_enabled"] = True
        ok = wp.start()
        log.info("TEST wallpaper start -> %s", ok)
        QTimer.singleShot(25000, app.quit)
    elif mode == "screensaver":
        ok = ss.start()
        log.info("TEST screensaver start -> %s", ok)
        QTimer.singleShot(15000, app.quit)
    elif mode == "settings":
        dlg = SettingsDialog(cfg)
        dlg.show()
        QTimer.singleShot(15000, dlg.close)
        dlg.exec()
        return
    elif mode == "standalone":
        w, h = desktop.get_screen_size()
        cef = CEFEngine()
        ok = cef.start_screensaver(cfg.get("screensaver_url",
                                           "https://zztool.free.nf/countdown"),
                                   w, h)
        log.info("TEST standalone start -> %s", ok)
        QTimer.singleShot(20000, app.quit)


def main():
    desktop.set_process_dpi_awareness()  # 必须在任何窗口创建前
    setup_logging()
    log.info("Countdown Desktop v%s starting (args=%s)", APP_VERSION, sys.argv[1:])

    if not single_instance():
        log.info("another instance is running, exit")
        return

    test_mode = None
    for a in sys.argv[1:]:
        if a in ("--test-wallpaper", "--test-screensaver", "--test-settings",
                 "--test-standalone"):
            test_mode = a[len("--test-"):]

    cfg = load_config()
    log.info("config: wp=%s ss=%s timeout=%ss",
             cfg["wallpaper_enabled"], cfg["screensaver_enabled"],
             cfg["screensaver_time"])

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 托盘应用常驻

    wp = WallpaperEngine(cfg)
    ss = ScreensaverEngine(cfg)

    if test_mode:
        run_test_mode(test_mode, cfg, wp, ss, app)
        app.exec()
        return

    tray = TrayIcon(cfg)
    tray.toggled_wallpaper.connect(lambda: toggle_wallpaper(cfg, wp, tray))
    tray.toggled_screensaver.connect(lambda: toggle_screensaver(cfg, ss, tray))
    tray.open_settings.connect(lambda: open_settings(cfg, wp, ss))
    tray.exit_app.connect(lambda: exit_app(wp, ss, tray, app))

    if cfg["wallpaper_enabled"]:
        wp.start()

    idle_timer = QTimer()
    idle_timer.setInterval(5000)
    idle_timer.timeout.connect(lambda: check_idle(cfg, ss))
    idle_timer.start()

    log.info("entering main loop")
    app.exec()
    log.info("app exited")


def toggle_wallpaper(cfg, wp, tray):
    cfg["wallpaper_enabled"] = not cfg["wallpaper_enabled"]
    save_config(cfg)
    if cfg["wallpaper_enabled"]:
        wp.start()
    else:
        wp.stop()
    tray.sync_checkmarks()


def toggle_screensaver(cfg, ss, tray):
    cfg["screensaver_enabled"] = not cfg["screensaver_enabled"]
    save_config(cfg)
    tray.sync_checkmarks()


def open_settings(cfg, wp, ss):
    dlg = SettingsDialog(
        cfg,
        on_save=lambda c: (save_config(c),
                           (wp.refresh() if c["wallpaper_enabled"] else wp.stop())),
        on_test_wallpaper=lambda: wp.refresh(),
        on_test_screensaver=lambda: ss.start(),
    )
    dlg.show()


def check_idle(cfg, ss):
    if ss.is_running():
        return
    if not cfg.get("screensaver_enabled"):
        return
    if idle_seconds() >= cfg.get("screensaver_time", 600):
        log.info("idle %ds, starting screensaver", idle_seconds())
        ss.start()


def exit_app(wp, ss, tray, app):
    log.info("exit requested")
    wp.stop()
    ss.stop()
    tray.hide()
    app.quit()


if __name__ == "__main__":
    main()
