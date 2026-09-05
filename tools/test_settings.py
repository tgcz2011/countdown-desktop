# -*- coding: utf-8 -*-
r"""开发验证：设置界面渲染与保存逻辑（含倒计时类型切换）。

注意：全程使用临时 APPDATA，不会读写真实配置。

用法：QT_QPA_PLATFORM=offscreen .venv\Scripts\python.exe tools\test_settings.py
"""
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config

# 隔离：指向临时配置目录
_TMP = tempfile.mkdtemp(prefix="cd-settings-")
config.config_dir = lambda: _TMP

from PySide6.QtWidgets import QApplication


class DummyApp:
    def __init__(self):
        self.cfg = config.load()
        self.calls = []

    def start_screensaver(self):
        self.calls.append("start_screensaver")

    def restart_wallplayer_if_needed(self, changed):
        self.calls.append(("restart", changed))

    def set_autostart(self, enable):
        self.calls.append(("autostart", enable))
        self.cfg["run_at_startup"] = bool(enable)


if __name__ == "__main__":
    qapp = QApplication(sys.argv)
    from app.settings import SettingsDialog
    dummy = DummyApp()
    dlg = SettingsDialog(dummy)
    dlg.show()
    qapp.processEvents()
    dlg.grab().save("verify_settings_ui.png")

    # 默认应落在「倒计时」页且为高考
    print("exam combo data:", dlg.cmb_exam.currentData(),
          "countdown page rows:", dlg.nav.count(),
          "url field enabled:", dlg.txt_wall_url.isEnabled(),
          "wall url:", dlg.txt_wall_url.text())

    # 切到中考并保存 → 壁纸/屏保 URL 均应为中考地址
    dlg.cmb_exam.setCurrentIndex(dlg.cmb_exam.findData("zhongkao"))
    print("after switch: wall url (readonly) =", dlg.txt_wall_url.text(),
          "enabled =", dlg.txt_wall_url.isEnabled())
    dlg.save()
    cfg2 = config.load()
    print("saved cfg:", "exam_type =", cfg2["exam_type"],
          "| wall =", cfg2["wallpaper"]["url"],
          "| ss =", cfg2["screensaver"]["url"],
          "| calls =", dummy.calls)
    ok = (cfg2["exam_type"] == "zhongkao"
          and cfg2["wallpaper"]["url"] == config.JUNIOR_URL
          and cfg2["screensaver"]["url"] == config.JUNIOR_URL)
    print("ZHONGKAO_SAVE_OK" if ok else "ZHONGKAO_SAVE_FAIL")

    # 切回自定义，填两个不同地址并保存
    dlg.cmb_exam.setCurrentIndex(dlg.cmb_exam.findData("custom"))
    print("custom mode: wall enabled =", dlg.txt_wall_url.isEnabled())
    dlg.txt_wall_url.setText("https://wall.example.com")
    dlg.txt_ss_url.setText("https://ss.example.com")
    dlg.save()
    cfg3 = config.load()
    ok2 = (cfg3["exam_type"] == "custom"
           and cfg3["wallpaper"]["url"] == "https://wall.example.com"
           and cfg3["screensaver"]["url"] == "https://ss.example.com")
    print("CUSTOM_SAVE_OK" if ok2 else "CUSTOM_SAVE_FAIL",
          cfg3["wallpaper"]["url"], cfg3["screensaver"]["url"])

    qapp.quit()
    shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(0 if (ok and ok2) else 1)
