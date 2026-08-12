# -*- coding: utf-8 -*-
"""设置界面：壁纸与屏保分开配置（URL、启用、超时）。"""
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QSpinBox, QVBoxLayout)

log = logging.getLogger("settings")

URL_HELP = "http(s) 网页地址，留空则使用默认地址"


def _normalize_url(text: str) -> str:
    from . import config
    text = text.strip()
    if not text:
        return config.DEFAULT_URL
    if not text.startswith(("http://", "https://")):
        text = "https://" + text
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
        self.txt_wall_url = QLineEdit()
        self.txt_wall_url.setPlaceholderText(URL_HELP)
        form_w.addRow("壁纸网页 URL", self.txt_wall_url)
        layout.addWidget(grp_w)

        # ---- 屏保 ----
        grp_s = QGroupBox("屏幕保护")
        form_s = QFormLayout(grp_s)
        self.chk_ss = QCheckBox("启用屏保（自绘全屏窗口，不使用系统屏保）")
        form_s.addRow(self.chk_ss)
        self.txt_ss_url = QLineEdit()
        self.txt_ss_url.setPlaceholderText(URL_HELP)
        form_s.addRow("屏保网页 URL", self.txt_ss_url)
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
