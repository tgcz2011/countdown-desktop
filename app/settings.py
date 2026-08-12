# -*- coding: utf-8 -*-
"""设置界面：壁纸与屏保分开配置（URL/本地文件、启用、超时）。"""
import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSpinBox, QVBoxLayout)

log = logging.getLogger("settings")

URL_HELP = "http(s) 网页地址，留空则使用默认地址"


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
        self.resize(520, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)

        # ---- 壁纸 ----
        grp_w = QGroupBox("动态壁纸")
        form_w = QFormLayout(grp_w)
        self.chk_wall = QCheckBox("启用动态壁纸")
        form_w.addRow(self.chk_wall)
        row_wall = QHBoxLayout()
        self.txt_wall_url = QLineEdit()
        self.txt_wall_url.setPlaceholderText("网页地址，或浏览选择 视频/图片/动图 文件")
        row_wall.addWidget(self.txt_wall_url)
        self.btn_wall_file = QPushButton("浏览…")
        self.btn_wall_file.clicked.connect(lambda: self._pick(self.txt_wall_url))
        row_wall.addWidget(self.btn_wall_file)
        form_w.addRow("壁纸源", row_wall)
        layout.addWidget(grp_w)

        # ---- 屏保 ----
        grp_s = QGroupBox("屏幕保护")
        form_s = QFormLayout(grp_s)
        self.chk_ss = QCheckBox("启用屏保（自绘全屏窗口，不使用系统屏保）")
        form_s.addRow(self.chk_ss)
        row_ss_url = QHBoxLayout()
        self.txt_ss_url = QLineEdit()
        self.txt_ss_url.setPlaceholderText("网页地址，或浏览选择 视频/图片/动图 文件")
        row_ss_url.addWidget(self.txt_ss_url)
        self.btn_ss_file = QPushButton("浏览…")
        self.btn_ss_file.clicked.connect(lambda: self._pick(self.txt_ss_url))
        row_ss_url.addWidget(self.btn_ss_file)
        form_s.addRow("屏保源", row_ss_url)
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(30, 86400)
        self.spin_timeout.setSuffix(" 秒")
        form_s.addRow("空闲触发时长", self.spin_timeout)
        row_ss = QHBoxLayout()
        self.btn_test = QPushButton("立即测试屏保")
        self.btn_test.clicked.connect(lambda: self.app.start_screensaver())
        row_ss.addWidget(self.btn_test)
        form_s.addRow(row_ss)
        layout.addWidget(grp_s)

        # ---- 按钮 ----
        row = QHBoxLayout()
        self.btn_save = QPushButton("保存")
        self.btn_save.clicked.connect(self.save)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.close)
        row.addStretch()
        row.addWidget(self.btn_save)
        row.addWidget(self.btn_cancel)
        layout.addLayout(row)

        self.load()

    def _pick(self, line_edit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择媒体文件", "",
            "视频/图片/动图 (*.mp4 *.webm *.mkv *.mov *.m4v *.gif *.png *.jpg "
            "*.jpeg *.bmp *.webp);;视频 (*.mp4 *.webm *.mkv *.mov *.m4v);;"
            "图片/动图 (*.gif *.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*.*)")
        if path:
            line_edit.setText(path)

    def load(self) -> None:
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

    def save(self) -> None:
        from . import config
        cfg = self.app.cfg
        old_enabled = bool(cfg["wallpaper"]["enabled"])
        old_url = cfg["wallpaper"]["url"]

        cfg["wallpaper"]["enabled"] = self.chk_wall.isChecked()
        cfg["wallpaper"]["url"] = _normalize_url(self.txt_wall_url.text())
        cfg["screensaver"]["enabled"] = self.chk_ss.isChecked()
        cfg["screensaver"]["url"] = _normalize_url(self.txt_ss_url.text())
        cfg["screensaver"]["timeout"] = self.spin_timeout.value()
        config.save(cfg)
        log.info("config saved")

        changed = (cfg["wallpaper"]["enabled"] != old_enabled
                   or cfg["wallpaper"]["url"] != old_url)
        self.app.restart_wallplayer_if_needed(changed)
        self.close()
