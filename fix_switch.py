import io

path = r'C:\Users\admin\Doubao\chats\2026-09-06\new-chat\countdown-desktop\app\main.py'
with io.open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. 添加 SWITCH_EXAM_EVENT_NAME 和 SWITCH_CMD_FILE 常量
old1 = 'SHOW_SETTINGS_EVENT_NAME = "CountdownDesktop_ShowSettings"'
new1 = (
    'SHOW_SETTINGS_EVENT_NAME = "CountdownDesktop_ShowSettings"\n'
    'SWITCH_EXAM_EVENT_NAME = "CountdownDesktop_SwitchExam"\n'
    'SWITCH_CMD_FILE = os.path.join(os.environ.get("TEMP", "."), "countdown_switch.json")'
)
if old1 in c:
    c = c.replace(old1, new1)
    print('1. constants OK')
else:
    print('1. constants NOT matched')

# 2. 在 _signal_show_settings 之后添加 _signal_switch_exam
old2 = '''    def _signal_show_settings() -> None:
        h = ctypes.windll.kernel32.OpenEventW(0x1F0003, False, SHOW_SETTINGS_EVENT_NAME)
        if not h:
            log.warning("show-settings event not found, running instance may be old version")
            return
        ctypes.windll.kernel32.SetEvent(h)
        ctypes.windll.kernel32.CloseHandle(h)
        log.info("show-settings event signaled to running instance")'''
new2 = old2 + '''

    @staticmethod
    def _signal_switch_exam(overrides: dict) -> None:
        """已有实例运行时：写命令文件 + 发命名事件，通知其切换考试类型。"""
        import json as _json
        try:
            with open(SWITCH_CMD_FILE, "w", encoding="utf-8") as f:
                _json.dump(overrides, f)
        except Exception:
            log.exception("write switch cmd file failed")
        h = ctypes.windll.kernel32.OpenEventW(0x1F0003, False, SWITCH_EXAM_EVENT_NAME)
        if not h:
            log.warning("switch-exam event not found, running instance may be old version")
            return
        ctypes.windll.kernel32.SetEvent(h)
        ctypes.windll.kernel32.CloseHandle(h)
        log.info("switch-exam event signaled: %s", overrides)'''
if old2 in c:
    c = c.replace(old2, new2)
    print('2. _signal_switch_exam OK')
else:
    print('2. _signal_switch_exam NOT matched')

with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)
print('saved')
