import io

path = r'C:\Users\admin\Doubao\chats\2026-09-06\new-chat\countdown-desktop\app\main.py'
with io.open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 在 run() 里，解析 CLI 之后、创建 App 之前，添加单实例切换逻辑
old = '''    from . import cli
    _CLI_OVERRIDES, _CLI_PROBLEMS = cli.parse_argv(sys.argv)
    log.info("=== main start, pid=%d, cli overrides=%s ===", os.getpid(),
             _CLI_OVERRIDES or "-")
    if _CLI_PROBLEMS:
        log.warning("unknown cli args ignored: %s", _CLI_PROBLEMS)
    app = App()
    return app.exec_()'''
new = '''    from . import cli
    _CLI_OVERRIDES, _CLI_PROBLEMS = cli.parse_argv(sys.argv)
    log.info("=== main start, pid=%d, cli overrides=%s ===", os.getpid(),
             _CLI_OVERRIDES or "-")
    if _CLI_PROBLEMS:
        log.warning("unknown cli args ignored: %s", _CLI_PROBLEMS)
    # 已有实例运行且传入了覆盖参数（如 --exam）：通知已有实例切换后退出，不接管
    if _CLI_OVERRIDES:
        from . import win32
        _mutex = win32.create_single_instance_mutex(MUTEX_NAME)
        if _mutex is None:
            App._signal_switch_exam(_CLI_OVERRIDES)
            print("Countdown Desktop: 已通知运行中的实例切换配置")
            return 0
        ctypes.windll.kernel32.CloseHandle(_mutex)
    app = App()
    return app.exec_()'''
if old in c:
    c = c.replace(old, new)
    print('run() switch logic OK')
else:
    print('run() switch logic NOT matched')
    # 打印附近内容帮助调试
    idx = c.find('from . import cli')
    if idx >= 0:
        print(repr(c[idx:idx+300]))

with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)
print('saved')
