# -*- coding: utf-8 -*-
"""系统托盘：QSystemTrayIcon + 右键菜单"""
import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

log = logging.getLogger("tray")


class TrayIcon(QObject):
    toggled_wallpaper = Signal()
    toggled_screensaver = Signal()
    open_settings = Signal()
    exit_app = Signal()

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.icon: QSystemTrayIcon | None = None

        menu = QMenu()
        self.act_wallpaper = QAction("切换壁纸", menu, checkable=True)
        self.act_wallpaper.setChecked(cfg.get("wallpaper_enabled", False))
        self.act_wallpaper.triggered.connect(self.toggled_wallpaper)
        menu.addAction(self.act_wallpaper)

        self.act_screensaver = QAction("切换屏保", menu, checkable=True)
        self.act_screensaver.setChecked(cfg.get("screensaver_enabled", True))
        self.act_screensaver.triggered.connect(self.toggled_screensaver)
        menu.addAction(self.act_screensaver)

        menu.addSeparator()
        act_settings = QAction("设置...", menu)
        act_settings.triggered.connect(self.open_settings)
        menu.addAction(act_settings)

        menu.addSeparator()
        act_exit = QAction("退出", menu)
        act_exit.triggered.connect(self.exit_app)
        menu.addAction(act_exit)

        self.icon = QSystemTrayIcon(_make_icon(), parent)
        self.icon.setToolTip("Countdown Desktop")
        self.icon.setContextMenu(menu)
        self.icon.activated.connect(self._on_activated)
        self.icon.show()
        log.info("tray icon shown")

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # 左键单击
            self.open_settings.emit()

    def sync_checkmarks(self):
        self.act_wallpaper.setChecked(self.cfg.get("wallpaper_enabled", False))
        self.act_screensaver.setChecked(self.cfg.get("screensaver_enabled", True))

    def hide(self):
        if self.icon:
            self.icon.hide()


def _make_icon() -> QIcon:
    """程序图标：蓝底 + 白色倒计时数字 9"""
    try:
        from PySide6.QtGui import QColor, QPainter, QPen
        pm = QPixmap(32, 32)
        pm.fill(QColor(37, 99, 235))
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(255, 255, 255))
        p.setPen(QPen(QColor(255, 255, 255)))
        p.drawEllipse(8, 5, 16, 16)
        p.setPen(QPen(QColor(37, 99, 235)))
        f = p.font()
        f.setPixelSize(14)
        f.setBold(True)
        p.setFont(f)
        p.drawText(9, 18, "9")
        p.drawRect(6, 25, 20, 3)
        p.end()
        return QIcon(pm)
    except Exception:
        return QIcon()
