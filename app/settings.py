# -*- coding: utf-8 -*-
"""设置窗口（Qt 原生对话框）"""
import logging

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLineEdit,
    QPushButton, QSpinBox, QVBoxLayout,
)

log = logging.getLogger("settings")


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, on_save=None, on_test_wallpaper=None, on_test_screensaver=None):
        super().__init__()
        self.cfg = cfg
        self.on_save = on_save
        self.on_test_wallpaper = on_test_wallpaper
        self.on_test_screensaver = on_test_screensaver

        self.setWindowTitle("Countdown Desktop - Settings")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.wp_url = QLineEdit(cfg.get("wallpaper_url", ""))
        self.ss_url = QLineEdit(cfg.get("screensaver_url", ""))
        self.timeout = QSpinBox()
        self.timeout.setRange(10, 86400)
        self.timeout.setValue(cfg.get("screensaver_time", 600))
        self.timeout.setSuffix(" s")
        self.wp_enabled = QCheckBox("启用壁纸")
        self.wp_enabled.setChecked(cfg.get("wallpaper_enabled", False))
        self.ss_enabled = QCheckBox("启用屏保")
        self.ss_enabled.setChecked(cfg.get("screensaver_enabled", True))

        form.addRow("壁纸 URL", self.wp_url)
        form.addRow("", self.wp_enabled)
        form.addRow("屏保 URL", self.ss_url)
        form.addRow("", self.ss_enabled)
        form.addRow("屏保超时", self.timeout)
        layout.addLayout(form)

        # 测试按钮
        test_row = QHBoxLayout()
        self.btn_test_wp = QPushButton("测试壁纸")
        self.btn_test_ss = QPushButton("测试屏保")
        self.btn_test_wp.clicked.connect(self._test_wp)
        self.btn_test_ss.clicked.connect(self._test_ss)
        test_row.addWidget(self.btn_test_wp)
        test_row.addWidget(self.btn_test_ss)
        test_row.addStretch()
        layout.addLayout(test_row)

        # 底部按钮
        btn_row = QHBoxLayout()
        self.btn_apply = QPushButton("应用")
        self.btn_save = QPushButton("保存并关闭")
        self.btn_cancel = QPushButton("取消")
        self.btn_apply.clicked.connect(self._apply)
        self.btn_save.clicked.connect(self._save_close)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_apply)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

    def _collect(self) -> dict:
        return {
            "wallpaper_url": self.wp_url.text().strip(),
            "screensaver_url": self.ss_url.text().strip(),
            "screensaver_time": self.timeout.value(),
            "wallpaper_enabled": self.wp_enabled.isChecked(),
            "screensaver_enabled": self.ss_enabled.isChecked(),
        }

    def _apply(self):
        self.cfg.update(self._collect())

    def _save_close(self):
        self._apply()
        if self.on_save:
            self.on_save(self.cfg)
        self.accept()

    def _test_wp(self):
        self._apply()
        if self.on_test_wallpaper:
            self.on_test_wallpaper()

    def _test_ss(self):
        self._apply()
        if self.on_test_screensaver:
            self.on_test_screensaver()
