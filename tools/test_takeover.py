# -*- coding: utf-8 -*-
r"""端到端验证：单实例接管（后启动的实例停止先启动的实例并接管）。

用法：.venv\Scripts\python.exe tools\test_takeover.py
会启动两个真实主进程实例（托盘图标短暂出现），验证第二个接管第一个，
最后清理所有进程与 PID 文件。不读写真实配置（壁纸/屏保均禁用）。
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
RUN = os.path.join(ROOT, "run.py")
PID_FILE = os.path.join(os.environ["APPDATA"], "CountdownDesktop", "main.pid")

BASE_ARGS = [PY, RUN, "--wallpaper-enabled=false", "--screensaver-enabled=false"]


def alive(pid):
    try:
        subprocess.run(["tasklist", "/FI", "PID eq %d" % pid],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
                       timeout=5)
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid],
                             capture_output=True, text=True,
                             creationflags=subprocess.CREATE_NO_WINDOW,
                             timeout=5).stdout
        return str(pid) in out
    except Exception:
        return False


def main():
    # 清理可能残留的 PID 文件
    try:
        os.remove(PID_FILE)
    except OSError:
        pass

    print("[1/5] 启动实例 A（GUI 模拟，无壁纸/屏保）...")
    a = subprocess.Popen(BASE_ARGS, cwd=ROOT,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    print("  A pid =", a.pid)
    time.sleep(4)  # 等 A 拿到互斥量 + 建好命名管道
    if a.poll() is not None:
        print("FAIL: A 启动后立即退出，code=", a.returncode)
        return 1
    print("  A 运行中")

    print("[2/5] 启动实例 B（CLI 模拟，--exam zhongkao），应接管 A...")
    b = subprocess.Popen(BASE_ARGS + ["--exam", "zhongkao"], cwd=ROOT,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    print("  B pid =", b.pid)
    time.sleep(7)  # 等 B 发 quit → A 退出 → B 拿互斥量

    print("[3/5] 检查 A 是否已退出...")
    a_dead = (a.poll() is not None)
    print("  A returncode =", a.returncode, "| alive =", not a_dead)
    if not a_dead:
        print("FAIL: A 未被接管退出")
        a.terminate()
        b.terminate()
        return 1
    print("  OK: A 已退出")

    print("[4/5] 检查 B 是否在运行...")
    b_alive = (b.poll() is None)
    print("  B returncode =", b.returncode, "| alive =", b_alive)
    if not b_alive:
        print("FAIL: B 未成功运行")
        return 1
    print("  OK: B 运行中（接管成功）")

    print("[5/5] 清理：终止 B...")
    b.terminate()
    try:
        b.wait(timeout=5)
    except subprocess.TimeoutExpired:
        b.kill()
    try:
        os.remove(PID_FILE)
    except OSError:
        pass
    print("TAKEOVER_TEST_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
