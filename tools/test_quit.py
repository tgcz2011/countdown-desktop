# -*- coding: utf-8 -*-
"""--quit 优雅退出命令端到端测试。

启动一个真实主进程实例，然后用 --quit 通知它退出，验证：
1. 有实例运行时：--quit 优雅退出成功，旧实例退出码 0，--quit 退出码 0
2. 无实例运行时：--quit 直接返回 0（幂等）
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
RUN = os.path.join(ROOT, "run.py")
PID_FILE = os.path.join(os.environ["APPDATA"], "CountdownDesktop", "main.pid")


def wait_pid_file(timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(PID_FILE):
            return True
        time.sleep(0.1)
    return False


def wait_process_exit(proc, timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return True
        time.sleep(0.1)
    return False


def test_quit_running_instance():
    print("[1/3] 启动实例 A（禁用壁纸/屏保）...")
    a = subprocess.Popen(
        [PY, RUN, "--wallpaper-enabled", "off", "--screensaver-enabled", "off"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    assert wait_pid_file(), "A 未创建 PID 文件"
    print("  A pid =", a.pid, "| 运行中")

    print("[2/3] 执行 --quit，应优雅退出 A...")
    q = subprocess.run([PY, RUN, "--quit"], capture_output=True, text=True, timeout=15)
    print("  --quit stdout:", q.stdout.strip())
    print("  --quit returncode =", q.returncode)
    assert q.returncode == 0, "--quit 应返回 0"

    exited = wait_process_exit(a)
    print("  A returncode =", a.returncode, "| alive =", a.poll() is None)
    assert exited, "A 未在超时内退出"
    assert a.returncode == 0, "A 应优雅退出（returncode 0），实际 %s" % a.returncode
    print("  OK: A 优雅退出")

    print("[3/3] 无实例时再次 --quit，应幂等返回 0...")
    q2 = subprocess.run([PY, RUN, "--quit"], capture_output=True, text=True, timeout=10)
    print("  --quit stdout:", q2.stdout.strip())
    print("  --quit returncode =", q2.returncode)
    assert q2.returncode == 0, "无实例时 --quit 应返回 0"
    print("  OK: 幂等")

    print("\nQUIT_TEST_OK")


if __name__ == "__main__":
    # 清理可能残留的实例
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=5)
    except Exception:
        pass
    time.sleep(1)
    test_quit_running_instance()
