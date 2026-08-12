# -*- coding: utf-8 -*-
"""开发验证：设置界面渲染与保存逻辑。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication


class DummyApp:
    def __init__(self):
        from app import config
        self.cfg = config.load()
        self.calls = []

    def start_screensaver(self):
        self.calls.append("start_screensaver")

    def restart_wallplayer_if_needed(self, changed):
        self.calls.append(("restart", changed))


if __name__ == "__main__":
    qapp = QApplication(sys.argv)
    from app.settings import SettingsDialog
    dummy = DummyApp()
    dlg = SettingsDialog(dummy)
    dlg.show()
    qapp.processEvents()
    dlg.grab().save("verify_settings_ui.png")
    print("ui captured; fields:",
          dlg.chk_wall.isChecked(), dlg.chk_ss.isChecked(), dlg.spin_timeout.value())
    # 模拟修改并保存
    dlg.txt_wall_url.setText("https://example.com/wall")
    dlg.spin_timeout.setValue(120)
    dlg.save()
    from app import config
    cfg2 = config.load()
    print("saved cfg:", cfg2["wallpaper"]["url"], cfg2["screensaver"]["timeout"],
          "calls:", dummy.calls)
    qapp.quit()
