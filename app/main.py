# -*- coding: utf-8 -*-
"""主程序：托盘图标 + 设置界面 + 空闲检测 + 播放器子进程管理。

进程模型（参考 Lively）：
  主进程(本文件) ── 托盘/设置/空闲检测
    ├─ player wallpaper  （壁纸，常驻，嵌入桌面）
    └─ player screensaver（屏保，空闲触发，输入即退）

命令行参数（单次有效，不写入长期配置）：见 app/cli.py。
"""
import logging
import os
import subprocess
import sys

log = logging.getLogger("main")

# 本次启动的命令行覆盖项（单次有效，不写入长期配置）；播放器子进程透传复用
_CLI_OVERRIDES = {}
_CLI_PROBLEMS = []


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


def _asset_path(name: str) -> str:
    """定位打包资源（图标等）。

    PyInstaller 6.x onedir：datas 在 _internal 下，仅存在于 _MEIPASS；
    exe 同目录不再有 datas（5.x 及以前的老行为）。
    开发态：仓库根/assets。
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            p = os.path.join(meipass, "assets", name)
            if os.path.exists(p):
                return p
        p = os.path.join(_base_dir(), "_internal", "assets", name)
        if os.path.exists(p):
            return p
        return os.path.join(_base_dir(), "assets", name)
    return os.path.join(_base_dir(), "assets", name)


def _spawn_cmd(mode: str) -> list:
    from . import cli
    if getattr(sys, "frozen", False):
        base = [sys.executable, "player", mode]
    else:
        run_py = os.path.join(_base_dir(), "run.py")
        base = [sys.executable, run_py, "player", mode]
    # 把本次启动的 CLI 覆盖透传给播放器，保证壁纸/屏保用同一覆盖配置
    return base + cli.serialize(_CLI_OVERRIDES)


class App:
    def __init__(self):
        from PySide6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu,
                                       QMessageBox)
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import QTimer, Qt
        from . import config, win32, cli

        win32.set_process_dpi_awareness()
        self.qapp = QApplication(sys.argv)
        self.qapp.setQuitOnLastWindowClosed(False)

        if "-h" in sys.argv or "--help" in sys.argv:
            QMessageBox.information(None, "Countdown Desktop", cli.USAGE)
            raise SystemExit(0)
        if _CLI_PROBLEMS:
            QMessageBox.warning(
                None, "Countdown Desktop",
                "以下命令行参数无法识别，已忽略：\n" + "\n".join(_CLI_PROBLEMS))

        self.mutex = win32.create_single_instance_mutex("CountdownDesktop_Single")
        if self.mutex is None:
            if _CLI_OVERRIDES:
                QMessageBox.warning(
                    None, "Countdown Desktop",
                    "程序已在运行。带参数启动需要先退出当前实例。")
            log.info("another instance running, exit")
            raise SystemExit(0)

        self.cfg = config.load()
        cli.apply(_CLI_OVERRIDES, self.cfg)   # CLI 覆盖只改内存，不落盘
        self.wallpaper_proc = None
        self.screensaver_proc = None
        self.settings_dialog = None

        icon_path = _asset_path("icon.ico")
        if not os.path.exists(icon_path):
            icon_path = ""
        tray_path = _asset_path("icon-tray.ico")
        if not os.path.exists(tray_path):
            tray_path = icon_path
        self.icon_colored = QIcon(icon_path) if icon_path else self.qapp.style().standardIcon(
            self.qapp.style().StandardPixmap.SP_ComputerIcon)
        # 深色任务栏用白色 glyph（icon-tray），浅色任务栏回退彩色主图标
        self.icon_tray = QIcon(tray_path) if tray_path else self.icon_colored

        self.tray = QSystemTrayIcon(self.icon_colored)
        self.tray.setToolTip("Countdown Desktop")
        self.menu = QMenu()
        self.act_settings = self.menu.addAction("设置", lambda: self.open_settings("general"))
        self.act_startup = self.menu.addAction(
            "开机自启", lambda: self.set_autostart(self.act_startup.isChecked()))
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
        # 托盘就绪后按系统主题定图标（深色任务栏用白 glyph）
        self._apply_tray_icon_for_theme()

        # 空闲检测
        self.timer = QTimer()
        self.timer.timeout.connect(self._idle_tick)
        self.timer.start(5000)

        # 监听系统主题切换（WM_SETTINGCHANGE "ImmersiveColorSet"），热切换托盘图标
        self._theme_filter = _ThemeChangeFilter(self)
        self.qapp.installNativeEventFilter(self._theme_filter)

        if self.cfg["wallpaper"]["enabled"]:
            self.start_wallpaper()

    # ---------------- 托盘图标 ----------------
    def _apply_tray_icon_for_theme(self) -> None:
        from . import win32
        light = False
        try:
            light = win32.system_uses_light_theme()
        except Exception:
            log.exception("read theme failed")
        self.tray.setIcon(self.icon_colored if light else self.icon_tray)
        self.tray.setToolTip("Countdown Desktop")

    def on_theme_changed(self) -> None:
        log.info("system theme changed, refresh tray icon")
        self._apply_tray_icon_for_theme()

    # ---------------- 壁纸 ----------------
    def start_wallpaper(self) -> None:
        cmd = _spawn_cmd("wallpaper")
        log.info("spawn wallpaper player: %s", cmd)
        self.wallpaper_proc = subprocess.Popen(
            cmd, creationflags=subprocess.CREATE_NO_WINDOW)

    def stop_wallpaper(self) -> None:
        if self.wallpaper_proc and self.wallpaper_proc.poll() is None:
            self.wallpaper_proc.terminate()
            try:
                self.wallpaper_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.wallpaper_proc.kill()
        self.wallpaper_proc = None

    def _restore_wallpaper(self) -> None:
        """退出/关壁纸后强制 explorer 重绘壁纸层（否则桌面白屏）。

        本软件从不修改系统壁纸值（只叠加窗口），因此直接把当前壁纸
        原样重设一次即可：不依赖快照（无跨进程配置同步问题），
        也不会回滚用户中途更换的壁纸。terminate() 强杀播放器时
        events.closed 不会触发，故由主进程负责重绘。
        """
        try:
            from . import win32
            if win32.refresh_desktop_wallpaper():
                log.info("desktop wallpaper refreshed")
        except Exception:
            log.exception("refresh wallpaper failed")

    def refresh_wallpaper(self) -> None:
        self.stop_wallpaper()
        from . import config, cli
        self.cfg = config.load()
        # 刷新后重新套用本次启动的 CLI 覆盖（单次有效）
        cli.apply(_CLI_OVERRIDES, self.cfg)
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
            # 托盘单击多为查状态/改自启等常规操作，落到通用页
            self.open_settings("general")

    def set_autostart(self, enable: bool) -> None:
        """统一自启入口：注册表 + 配置 + 托盘勾选态同步（设置页与托盘共用）。"""
        from . import win32, config
        if enable == bool(self.cfg.get("run_at_startup")):
            self.act_startup.setChecked(enable)
            return
        exe = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(
            os.path.join(_base_dir(), "run.py"))
        try:
            win32.set_autostart(enable, exe)
        except OSError:
            log.exception("set_autostart failed")
            enable = bool(self.cfg.get("run_at_startup"))
        self.cfg["run_at_startup"] = enable
        config.save(self.cfg)
        self.act_startup.setChecked(enable)

    def open_settings(self, page: str = "wallpaper") -> None:
        from .settings import SettingsDialog
        if self.settings_dialog is None or not self.settings_dialog.isVisible():
            self.settings_dialog = SettingsDialog(self)
        if hasattr(self.settings_dialog, "goto_page"):
            self.settings_dialog.goto_page(page)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def restart_wallplayer_if_needed(self, changed: bool) -> None:
        if changed:
            was_running = self.wallpaper_proc is not None
            self.stop_wallpaper()
            if self.cfg["wallpaper"]["enabled"]:
                self.start_wallpaper()
            elif was_running:
                # 关闭壁纸（不退出软件）：立刻还原桌面壁纸
                self._restore_wallpaper()

    def quit(self) -> None:
        log.info("quit")
        self.stop_wallpaper()
        self._restore_wallpaper()
        if self.screensaver_active():
            self.screensaver_proc.terminate()
        self.tray.hide()
        self.qapp.quit()

    def exec_(self) -> int:
        return self.qapp.exec()


def run() -> int:
    global _CLI_OVERRIDES, _CLI_PROBLEMS
    _setup_logging()
    from . import cli
    _CLI_OVERRIDES, _CLI_PROBLEMS = cli.parse_argv(sys.argv)
    log.info("=== main start, pid=%d, cli overrides=%s ===", os.getpid(),
             _CLI_OVERRIDES or "-")
    if _CLI_PROBLEMS:
        log.warning("unknown cli args ignored: %s", _CLI_PROBLEMS)
    app = App()
    return app.exec_()


# 主题过滤器依赖：Qt 原生事件基类 + win32 消息结构（仅非 Windows 平台缺失，程序本身只跑在 Windows）
from PySide6.QtCore import QAbstractNativeEventFilter  # noqa: E402
import ctypes  # noqa: E402
import ctypes.wintypes  # noqa: E402


class _ThemeChangeFilter(QAbstractNativeEventFilter):
    """监听 WM_SETTINGCHANGE（系统主题切换），通知托盘换图标。"""

    WM_SETTINGCHANGE = 0x001A

    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == self.WM_SETTINGCHANGE:
                buf = ctypes.c_wchar_p(msg.lParam) if msg.lParam else None
                if buf and buf.value == "ImmersiveColorSet":
                    try:
                        self.app_ref.on_theme_changed()
                    except Exception:
                        log.exception("on_theme_changed failed")
        return False
