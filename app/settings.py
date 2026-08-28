# -*- coding: utf-8 -*-
"""设置界面：左侧导航 + 多页内容区（QListWidget + QStackedWidget）。

为什么分页：设置项会持续增加（未来新功能），单页对话框塞不下且难导航。
页面采用注册制（PAGES 列表 + 页面工厂），新增设置页只需：
  1. 写一个 make_xxx_page(self) 工厂，返回含 load()/save() 接口的 QWidget；
  2. 在 PAGES 里注册 (key, 标题, 工厂)。
导航切换、统一 load/save 由基类逻辑自动处理。
"""
import logging
import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton,
                               QSpinBox, QStackedWidget, QVBoxLayout,
                               QWidget)

log = logging.getLogger("settings")

URL_HELP = "http(s) 网页地址，留空则使用默认地址"

# 导航页注册表：(key, 标题, 工厂函数名)。需要新页时在此追加即可。
PAGES = [
    ("wallpaper", "动态壁纸", "_make_wallpaper_page"),
    ("screensaver", "屏幕保护", "_make_screensaver_page"),
    ("general", "通用", "_make_general_page"),
    ("about", "关于", "_make_about_page"),
]


def _normalize_url(text: str) -> str:
    from . import config
    text = text.strip()
    if not text:
        return config.DEFAULT_URL
    if text.startswith(("http://", "https://")):
        return text
    if os.path.isfile(text):
        return text
    if len(text) > 3 and "." in text.split("/")[0]:
        return "https://" + text
    return text


class SettingsDialog(QDialog):
    def __init__(self, app):
        super().__init__()
        self.app = app
        from . import version
        self.setWindowTitle("Countdown Desktop 设置 v%s" % version.VERSION)
        self.resize(680, 460)
        self.setMinimumSize(560, 400)
        self.setWindowFlags(self.windowFlags()
                            & ~Qt.WindowType.WindowContextHelpButtonHint)

        outer = QVBoxLayout(self)
        content = QHBoxLayout()

        # ---- 左侧导航 ----
        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setIconSize(QSize(20, 20))
        self.nav.setFixedWidth(148)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.currentRowChanged.connect(self._switch_page)
        content.addWidget(self.nav)

        # ---- 右侧内容区 ----
        self.stack = QStackedWidget()
        self.stack.setContentsMargins(0, 0, 0, 0)
        content.addWidget(self.stack, 1)
        outer.addLayout(content, 1)

        self._pages = {}  # key -> (widget, 标题)
        for key, title, factory in PAGES:
            page = getattr(self, factory)()
            page.setObjectName("page-" + key)
            self.stack.addWidget(page)
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.nav.addItem(item)
            self._pages[key] = (page, title)

        # ---- 底部按钮（全局保存/取消，作用于所有页） ----
        row_btns = QHBoxLayout()
        row_btns.setContentsMargins(16, 8, 16, 12)
        self.btn_save = QPushButton("保存")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        row_btns.addStretch()
        row_btns.addWidget(self.btn_save)
        row_btns.addWidget(self.btn_cancel)
        outer.addLayout(row_btns)

        self._style_nav()
        self.nav.setCurrentRow(0)
        self.load_all()

    # ---------------- 导航 ----------------
    def _style_nav(self) -> None:
        self.nav.setStyleSheet("""
            QListWidget#settingsNav {
                background: transparent; border: none;
                outline: 0; padding: 8px 0;
            }
            QListWidget#settingsNav::item {
                padding: 10px 14px; margin: 2px 6px;
                border-radius: 6px; color: #333;
            }
            QListWidget#settingsNav::item:hover { background: #ececf2; }
            QListWidget#settingsNav::item:selected {
                background: #d8d8e8; color: #111;
            }
        """)

    def _switch_page(self, row: int) -> None:
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)

    def goto_page(self, key: str) -> None:
        """按 key 跳转到指定设置页（供托盘等外部入口定位）。"""
        for row in range(self.nav.count()):
            if self.nav.item(row).data(Qt.ItemDataRole.UserRole) == key:
                self.nav.setCurrentRow(row)
                return

    # ---------------- 页面工厂 ----------------
    def _make_wallpaper_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)

        grp = QGroupBox("动态壁纸")
        form = QFormLayout(grp)
        self.chk_wall = QCheckBox("启用动态壁纸")
        form.addRow(self.chk_wall)
        row_wall = QHBoxLayout()
        self.txt_wall_url = QLineEdit()
        self.txt_wall_url.setPlaceholderText("网页地址，或浏览选择 视频/图片/动图 文件")
        row_wall.addWidget(self.txt_wall_url)
        self.btn_wall_file = QPushButton("浏览…")
        self.btn_wall_file.clicked.connect(lambda: self._pick(self.txt_wall_url))
        row_wall.addWidget(self.btn_wall_file)
        form.addRow("壁纸源", row_wall)
        layout.addWidget(grp)

        layout.addStretch()
        return page

    def _make_screensaver_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)

        grp = QGroupBox("屏幕保护")
        form = QFormLayout(grp)
        self.chk_ss = QCheckBox("启用屏保（自绘全屏窗口，不使用系统屏保）")
        form.addRow(self.chk_ss)
        row_ss_url = QHBoxLayout()
        self.txt_ss_url = QLineEdit()
        self.txt_ss_url.setPlaceholderText("网页地址，或浏览选择 视频/图片/动图 文件")
        row_ss_url.addWidget(self.txt_ss_url)
        self.btn_ss_file = QPushButton("浏览…")
        self.btn_ss_file.clicked.connect(lambda: self._pick(self.txt_ss_url))
        row_ss_url.addWidget(self.btn_ss_file)
        form.addRow("屏保源", row_ss_url)
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(30, 86400)
        self.spin_timeout.setSuffix(" 秒")
        form.addRow("空闲触发时长", self.spin_timeout)
        row_ss = QHBoxLayout()
        self.btn_test = QPushButton("立即测试屏保")
        self.btn_test.clicked.connect(lambda: self.app.start_screensaver())
        row_ss.addWidget(self.btn_test)
        form.addRow(row_ss)
        layout.addWidget(grp)

        layout.addStretch()
        return page

    def _make_general_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)

        grp = QGroupBox("通用")
        form = QFormLayout(grp)
        self.chk_startup = QCheckBox("开机自启（写入注册表 HKCU，卸载自动清理）")
        form.addRow(self.chk_startup)
        layout.addWidget(grp)

        layout.addStretch()
        return page

    def _make_about_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)

        from . import version
        grp = QGroupBox("关于")
        form = QFormLayout(grp)
        for label, value in (("程序", "Countdown Desktop"),
                             ("版本", "v%s" % version.VERSION),
                             ("功能", "动态壁纸 + 屏幕保护（网页/视频/图片/动图）"),
                             ("渲染", "pywebview + WebView2（Chromium）"),
                             ("开源", "GPL-3.0")):
            text = QLabel(value)
            text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            form.addRow(label, text)
        layout.addWidget(grp)

        layout.addStretch()
        return page

    # ---------------- 文件选择 ----------------
    def _pick(self, line_edit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择媒体文件", "",
            "视频/图片/动图 (*.mp4 *.webm *.mkv *.mov *.m4v *.gif *.png *.jpg "
            "*.jpeg *.bmp *.webp);;视频 (*.mp4 *.webm *.mkv *.mov *.m4v);;"
            "图片/动图 (*.gif *.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*.*)")
        if path:
            line_edit.setText(path)

    # ---------------- 统一读取/保存 ----------------
    def load_all(self) -> None:
        """从配置刷新所有页面控件（含通用页）。"""
        from . import config
        cfg = self.app.cfg
        self.chk_wall.setChecked(bool(cfg["wallpaper"]["enabled"]))
        wall_url = cfg["wallpaper"]["url"]
        self.txt_wall_url.setText("" if wall_url == config.DEFAULT_URL else wall_url)
        self.chk_ss.setChecked(bool(cfg["screensaver"]["enabled"]))
        ss_url = cfg["screensaver"]["url"]
        self.txt_ss_url.setText("" if ss_url == config.DEFAULT_URL else ss_url)
        try:
            self.spin_timeout.setValue(int(cfg["screensaver"]["timeout"]))
        except (TypeError, ValueError):
            self.spin_timeout.setValue(600)
        self.chk_startup.setChecked(bool(cfg.get("run_at_startup")))

    def save_all(self) -> bool:
        """写回全部设置。返回壁纸配置是否变化（需要重启播放器）。"""
        from . import config
        cfg = self.app.cfg
        old_enabled = bool(cfg["wallpaper"]["enabled"])
        old_url = cfg["wallpaper"]["url"]

        cfg["wallpaper"]["enabled"] = self.chk_wall.isChecked()
        cfg["wallpaper"]["url"] = _normalize_url(self.txt_wall_url.text())
        cfg["screensaver"]["enabled"] = self.chk_ss.isChecked()
        cfg["screensaver"]["url"] = _normalize_url(self.txt_ss_url.text())
        cfg["screensaver"]["timeout"] = self.spin_timeout.value()
        # 先同步自启（内部可能改 cfg["run_at_startup"]），再统一落盘一次
        self.app.set_autostart(self.chk_startup.isChecked())
        config.save(cfg)
        log.info("config saved")

        return (cfg["wallpaper"]["enabled"] != old_enabled
                or cfg["wallpaper"]["url"] != old_url)

    # 兼容旧调用名
    load = load_all
    save = save_all

    # ---------------- 按钮 ----------------
    def accept(self) -> None:  # 保存
        changed = self.save_all()
        self.app.restart_wallplayer_if_needed(changed)
        super().accept()

    def reject(self) -> None:  # 取消/关闭
        super().reject()
