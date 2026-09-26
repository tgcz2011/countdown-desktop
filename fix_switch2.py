import io

path = r'C:\Users\admin\Doubao\chats\2026-09-06\new-chat\countdown-desktop\app\main.py'
with io.open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 3. 在 _init_show_settings_event 调用之后添加 _init_switch_exam_event 调用
old3 = '        self._init_show_settings_event()'
new3 = '        self._init_show_settings_event()\n        self._init_switch_exam_event()'
if old3 in c:
    c = c.replace(old3, new3)
    print('3. init call OK')
else:
    print('3. init call NOT matched')

# 4. 在 quit_timer.timeout.connect 里添加 _check_switch_exam_event
old4 = '        self.quit_timer.timeout.connect(self._check_show_settings_event)'
new4 = '        self.quit_timer.timeout.connect(self._check_show_settings_event)\n        self.quit_timer.timeout.connect(self._check_switch_exam_event)'
if old4 in c:
    c = c.replace(old4, new4)
    print('4. timer connect OK')
else:
    print('4. timer connect NOT matched')

# 5. 在 _check_show_settings_event 方法之后添加 _init_switch_exam_event 和 _check_switch_exam_event
old5 = '''    def _check_show_settings_event(self) -> None:
        if self.show_settings_event is not None and _event_signaled(self.show_settings_event):
            ctypes.windll.kernel32.ResetEvent(self.show_settings_event)
            log.info("show-settings event signaled, opening settings")
            self.open_settings("general")'''
new5 = old5 + '''

    def _init_switch_exam_event(self) -> None:
        """创建切换考试事件，复用 quit_timer 轮询。"""
        h = ctypes.windll.kernel32.CreateEventW(None, True, False, SWITCH_EXAM_EVENT_NAME)
        if h:
            ctypes.windll.kernel32.ResetEvent(h)
            self.switch_exam_event = h
            log.info("switch-exam event listening (%s)", SWITCH_EXAM_EVENT_NAME)
        else:
            self.switch_exam_event = None
            log.warning("create switch-exam event failed: %s", ctypes.get_last_error())

    def _check_switch_exam_event(self) -> None:
        if self.switch_exam_event is None or not _event_signaled(self.switch_exam_event):
            return
        ctypes.windll.kernel32.ResetEvent(self.switch_exam_event)
        import json as _json
        try:
            with open(SWITCH_CMD_FILE, "r", encoding="utf-8") as f:
                overrides = _json.load(f)
            log.info("switch-exam event signaled: %s", overrides)
            self.apply_overrides_and_restart(overrides)
        except Exception:
            log.exception("read switch cmd file failed")

    def apply_overrides_and_restart(self, overrides: dict) -> None:
        """应用 CLI 覆盖参数并重启壁纸/屏保进程（供已有实例切换考试类型）。"""
        from . import cli
        cli.apply(overrides, self.cfg)
        # 重启壁纸进程
        was_wallpaper = self.wallpaper_proc is not None and self.wallpaper_proc.poll() is None
        if was_wallpaper:
            self.stop_wallpaper()
            self.start_wallpaper()
        # 重启屏保进程
        if hasattr(self, "screensaver_proc") and self.screensaver_proc and self.screensaver_proc.poll() is None:
            self.screensaver_proc.terminate()
            try:
                self.screensaver_proc.wait(timeout=3)
            except Exception:
                self.screensaver_proc.kill()
            self.screensaver_proc = None
            if getattr(self.cfg, "screensaver_enabled", True):
                self.start_screensaver()
        log.info("overrides applied and players restarted")'''
if old5 in c:
    c = c.replace(old5, new5)
    print('5. switch methods OK')
else:
    print('5. switch methods NOT matched')

with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)
print('saved')
