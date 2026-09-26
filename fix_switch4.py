import io

path = r'C:\Users\admin\Doubao\chats\2026-09-06\new-chat\countdown-desktop\app\main.py'
with io.open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 在 _wait_mutex 的 @staticmethod 之前插入 _signal_switch_exam
old = '''    @staticmethod
    def _wait_mutex(timeout: float) -> bool:'''
new = '''    @staticmethod
    def _signal_switch_exam(overrides: dict) -> None:
        """已有实例运行时：写命令文件 + 发命名事件，通知其切换考试类型。"""
        import json as _json
        try:
            with open(SWITCH_CMD_FILE, "w", encoding="utf-8") as f:
                _json.dump(overrides, f)
        except Exception:
            log.exception("write switch cmd file failed")
        h = ctypes.windll.kernel32.OpenEventW(EVENT_MODIFY_STATE, False, SWITCH_EXAM_EVENT_NAME)
        if not h:
            log.warning("switch-exam event not found, running instance may be old version")
            return
        ctypes.windll.kernel32.SetEvent(h)
        ctypes.windll.kernel32.CloseHandle(h)
        log.info("switch-exam event signaled: %s", overrides)

    @staticmethod
    def _wait_mutex(timeout: float) -> bool:'''
if old in c:
    c = c.replace(old, new)
    print('_signal_switch_exam inserted OK')
else:
    print('NOT matched')

with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)
print('saved')
