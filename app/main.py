# -*- coding: utf-8 -*-
"""主程序：托盘图标 + 设置界面 + 空闲检测 + 播放器子进程管理。

进程模型（参考 Lively）：
  主进程(本文件) ── 托盘/设置/空闲检测
    ├─ player wallpaper  （壁纸，常驻，嵌入桌面）
    └─ player screensaver（屏保，空闲触发，输入即退）
"""
import logging
import os
import subprocess
import sys

log = logging.getLogger("main")


def _setup_logging() -> None:
    from . import config
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        filename=os.path.join(config.config_dir(), "main.log"),
        encoding="utf-8",
    )


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _spawn_cmd(mode: str) -> list:
    if getattr(sys, "frozen", False):
        return [sys.executable, "player", mode]
    run_py = os.path.join(_base_dir(), "run.py")
    return [sys.executable, run_py, "player", mode]


class App:
    def __init__(self):
        from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import QTimer, Qt
        from . import config, win32

        win32.set_process_dpi_awareness()
        self.mutex = win32.create_single_instance_mutex("CountdownDesktop_Single")
        if self.mutex is None:
            log.info("another instance running, exit")
            raise SystemExit(0)

        self.cfg = config.load()
        self.wallpaper_proc = None
        self.screensaver_proc = None
        self.settings_dialog = None

        self.qapp = QApplication(sys.argv)
        self.qapp.setQuitOnLastWindowClosed(False)

        icon_path = os.path.join(_base_dir(), "assets", "icon.ico")
        if not os.path.exists(icon_path):
            icon_path = ""
        self.icon = QIcon(icon_path) if icon_path else self.qapp.style().standardIcon(
            self.qapp.style().StandardPixmap.SP_ComputerIcon)

        self.tray = QSystemTrayIcon(self.icon)
        self.tray.setToolTip("Countdown Desktop")
        self.menu = QMenu()
        self.act_settings = self.menu.addAction("设置", self.open_settings)
        self.act_startup = self.menu.addAction("开机自启", self.toggle_startup)
        self.act_startup.setCheckable(True)
        self.act_startup.setChecked(bool(self.cfg.get("run_at_startup")))
        self.menu.addSeparator()
        self.act_save = self.menu.addAction("立即启动屏保", self.start_screensaver)
        self.act_refresh = self.menu.addAction("刷新壁纸", self.refresh_wallpaper)
        self.menu.addSeparator()
        self.menu.addAction("退出", self.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        # 空闲检测
        self.timer = QTimer()
        self.timer.timeout.connect(self._idle_tick)
        self.timer.start(5000)

        if self.cfg["wallpaper"]["enabled"]:
            self.start_wallpaper()

    # ---------------- 壁纸 ----------------
    def start_wallpaper(self) -> None:
        cmd = _spawn_cmd("wallpaper")
        log.info("spawn wallpaper player: %s", cmd)
        self.wallpaper_proc = subprocess.Popen(
            cmd, creationflags=subprocess.CREATE_NO_WINDOW)

    def stop_wallpaper(self) -> None:
        if self.wallpaper_proc and self.wallpaper_proc.poll() is None:
            self.wallpaper_proc.terminate()
        self.wallpaper_proc = None

    def refresh_wallpaper(self) -> None:
        self.stop_wallpaper()
        self.cfg = __import__("app.config", fromlist=["config"]).load()
        if self.cfg["wallpaper"]["enabled"]:
            self.start_wallpaper()

    # ---------------- 屏保 ----------------
    def start_screensaver(self) -> None:
        if self.screensaver_proc and self.screensaver_proc.poll() is None:
            return
        if not self.cfg["screensaver"]["enabled"]:
            return
        cmd = _spawn_cmd("screensaver")
        log.info("spawn screensaver player")
        self.screensaver_proc = subprocess.Popen(
            cmd, creationflags=subprocess.CREATE_NO_WINDOW)

    def screensaver_active(self) -> bool:
        return self.screensaver_proc is not None and self.screensaver_proc.poll() is None

    def _idle_tick(self) -> None:
        from . import win32
        if not self.cfg["screensaver"]["enabled"]:
            return
        if self.screensaver_active():
            return
        try:
            timeout = float(self.cfg["screensaver"]["timeout"])
        except (TypeError, ValueError):
            timeout = 600.0
        if win32.last_input_idle_seconds() >= timeout:
            log.info("idle %.0fs >= %.0fs, start screensaver",
                     win32.last_input_idle_seconds(), timeout)
            self.start_screensaver()

    # ---------------- 托盘/设置 ----------------
    def _on_tray_activated(self, reason):
        from PySide6.QtWidgets import QSystemTrayIcon
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_settings()

    def toggle_startup(self) -> None:
        from . import win32, config
        enable = self.act_startup.isChecked()
        exe = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(
            os.path.join(_base_dir(), "run.py"))
        try:
            win32.set_autostart(enable, exe)
        except OSError:
            log.exception("set_autostart failed")
        self.cfg["run_at_startup"] = enable
        config.save(self.cfg)

    def open_settings(self) -> None:
        from .settings import SettingsDialog
        if self.settings_dialog is None or not self.settings_dialog.isVisible():
            self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def restart_wallplayer_if_needed(self, changed: bool) -> None:
        if changed:
            self.stop_wallpaper()
            if self.cfg["wallpaper"]["enabled"]:
                self.start_wallpaper()

    def quit(self) -> None:
        log.info("quit")
        self.stop_wallpaper()
        if self.screensaver_active():
            self.screensaver_proc.terminate()
        self.tray.hide()
        self.qapp.quit()

    def exec_(self) -> int:
        return self.qapp.exec()


def run() -> int:
    _setup_logging()
    log.info("=== main start, pid=%d ===", os.getpid())
    app = App()
    return app.exec_()
