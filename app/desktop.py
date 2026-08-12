# -*- coding: utf-8 -*-
"""桌面窗口结构定位与壁纸嵌入（ctypes Win32，参考 Lively Wallpaper）

关键经验（Go 版踩坑）：
1. 0x052C 必须带 wParam=0xD, lParam=0x1 才能创建 raised desktop 的 WorkerW
2. SetParent 前必须先设 WS_CHILD 样式（SetParent 不会自动加）
3. 窗口操作必须与窗口创建在同一线程（Qt GUI 线程内调用即满足）
4. Win11 raised desktop：Progman 有 WS_EX_NOREDIRECTIONBITMAP，
   壁纸窗口需 WS_EX_LAYERED + SetLayeredWindowAttributes(bAlpha=0xFF)
"""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 常量
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_POPUP = 0x80000000
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000
WS_EX_LAYERED = 0x00080000
WS_EX_NOREDIRECTIONBITMAP = 0x00200000
LWA_ALPHA = 0x00000002
SWP_NOACTIVATE = 0x0010
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
SW_HIDE = 0
SW_SHOWNA = 8
HWND_BOTTOM = 1
SM_CXSCREEN = 0
SM_CYSCREEN = 1
WM_052C = 0x052C


def set_process_dpi_awareness() -> None:
    """PerMonitorV2 DPI awareness（必须在创建任何窗口前调用）"""
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        if not user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            user32.SetProcessDPIAware()
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def get_screen_size() -> tuple:
    w = user32.GetSystemMetrics(SM_CXSCREEN)
    h = user32.GetSystemMetrics(SM_CYSCREEN)
    return int(w), int(h)


def find_progman():
    return user32.FindWindowW("Progman", None)


def send_spawn_workerw(progman) -> None:
    """发送 0x052C wParam=0xD lParam=0x1 创建壁纸 WorkerW"""
    import logging
    log = logging.getLogger("desktop")
    for i in range(2):
        log.info("sending 0x052C (%d/2) progman=0x%x", i + 1, progman)
        r = user32.SendMessageTimeoutW(progman, WM_052C, 0xD, 0x1, 0, 1000, None)
        log.info("0x052C returned %r", r)


def _get_window_long_ptr(hwnd, index):
    try:
        return user32.GetWindowLongPtrW(hwnd, index)
    except Exception:
        return user32.GetWindowLongW(hwnd, index)


def _set_window_long_ptr(hwnd, index, value):
    try:
        return user32.SetWindowLongPtrW(hwnd, index, value)
    except Exception:
        return user32.SetWindowLongW(hwnd, index)


def is_raised_desktop(progman) -> bool:
    ex = _get_window_long_ptr(progman, GWL_EXSTYLE)
    return bool(ex & WS_EX_NOREDIRECTIONBITMAP)


def find_defview_under(parent) -> int:
    return user32.FindWindowExW(parent, 0, "SHELLDLL_DefView", None)


def find_workerw_with_defview() -> tuple:
    """枚举顶层 WorkerW，返回 (host, defView)。

    与 Lively 一致：找到含 DefView 的 WorkerW 后，取它的**下一个 WorkerW 兄弟**
    作为壁纸宿主（壁纸专用 WorkerW 层）。找不到下一个则回退到 DefView 所在 WorkerW。
    """
    result = [0, 0]

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        if buf.value == "WorkerW":
            dv = find_defview_under(hwnd)
            if dv:
                # Lively: workerW = FindWindowEx(NULL, tophandle, "WorkerW", NULL)
                nxt = user32.FindWindowExW(0, hwnd, "WorkerW", None)
                result[0] = nxt if nxt else hwnd
                result[1] = dv
                return False  # 停止枚举
        return True

    user32.EnumWindows(cb, 0)
    return result[0], result[1]


def find_desktop_host():
    """定位壁纸宿主窗口。

    返回 dict: {host, defview, raised, progman, workerw}
    - raised=True: host=Progman（壁纸窗口 SetParent 到 Progman）
    - raised=False: host=含 DefView 的 WorkerW（经典布局）
    """
    import logging
    log = logging.getLogger("desktop")
    progman = find_progman()
    log.info("progman=0x%x", progman)
    if not progman:
        raise RuntimeError("Progman not found")

    send_spawn_workerw(progman)
    raised = is_raised_desktop(progman)
    log.info("raised=%s", raised)

    # 1. DefView 在 Progman 下（Win11 layered ShellView / 部分环境）
    defview = find_defview_under(progman)
    log.info("defview under progman=0x%x", defview)
    host = progman
    workerw = 0

    if not defview:
        # 2. DefView 在顶层 WorkerW 下（经典布局）
        log.info("searching WorkerW...")
        workerw, defview = find_workerw_with_defview()
        log.info("workerw=0x%x defview=0x%x", workerw, defview)
        if defview:
            host = workerw

    if not defview:
        raise RuntimeError("SHELLDLL_DefView not found")

    if raised:
        # raised desktop：找到 Progman 下的壁纸 WorkerW（由 0x052C 创建）
        workerw = user32.FindWindowExW(progman, 0, "WorkerW", None)

    return {
        "host": host,
        "defview": defview,
        "raised": raised,
        "progman": progman,
        "workerw": workerw,
    }


def make_child_window(hwnd) -> None:
    """先转 WS_CHILD（SetParent 不自动加 WS_CHILD，不设则 SetParent 无效）"""
    style = _get_window_long_ptr(hwnd, GWL_STYLE)
    style &= ~WS_POPUP
    style &= ~WS_OVERLAPPEDWINDOW
    style |= WS_CHILD | WS_VISIBLE
    _set_window_long_ptr(hwnd, GWL_STYLE, style)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                        SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def set_window_ex_style(hwnd, add=0, remove=0) -> None:
    ex = _get_window_long_ptr(hwnd, GWL_EXSTYLE)
    ex |= add
    ex &= ~remove
    _set_window_long_ptr(hwnd, GWL_EXSTYLE, ex)


def set_layered_alpha(hwnd, alpha=255) -> None:
    """LAYERED 窗口必须显式设置 alpha，否则完全不绘制"""
    set_window_ex_style(hwnd, add=WS_EX_LAYERED)
    user32.SetLayeredWindowAttributes(hwnd, 0, alpha, LWA_ALPHA)


def attach_wallpaper(hwnd, host_info, width, height) -> None:
    """把壁纸窗口嵌入桌面（必须在 GUI 线程调用）。

    步骤（Lively 对齐）：
    1. WS_CHILD（必须手动）
    2. raised: WS_EX_LAYERED + alpha（微软官方要求）；exstyle toolwindow/noactivate
    3. SetParent 到 host
    4. SetWindowPos 全屏 + Z-order 底部（图标层之上）
    5. ShowWindow 确保可见
    """
    make_child_window(hwnd)

    if host_info["raised"]:
        set_layered_alpha(hwnd, 255)
    set_window_ex_style(hwnd,
                        add=WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
                        remove=WS_EX_APPWINDOW | WS_EX_LAYERED if not host_info["raised"] else WS_EX_APPWINDOW)

    host = host_info["host"]
    user32.SetParent(hwnd, host)

    # Z-order：底部（在 DefView 图标层之下）
    user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, width, height, SWP_NOACTIVATE)

    if host_info["raised"] and host_info["workerw"]:
        # 确保壁纸 WorkerW 保持在 Progman Z-order 最底
        user32.SetWindowPos(host_info["workerw"], HWND_BOTTOM, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

    # 确保可见（样式修改可能隐藏窗口）
    user32.ShowWindow(hwnd, SW_SHOWNA)
    user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, width, height, SWP_NOACTIVATE)


def is_window_visible(hwnd) -> bool:
    return bool(user32.IsWindowVisible(hwnd))


def _enum_top_windows():
    """枚举所有顶层窗口句柄"""
    results = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        results.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    return results


def _get_class_name(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _get_pid(hwnd) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def attach_chromium_view(qt_hwnd, host_info, width, height) -> None:
    """QtWebEngine 把 Chromium 内容渲染到独立的 Chrome_WidgetWin_0 顶层窗口。

    找到同进程的 Chrome_WidgetWin_0，把它也嵌入桌面（SetParent + 全屏 + 显示）。
    """
    import logging
    log = logging.getLogger("desktop")
    import os

    my_pid = os.getpid()
    host = host_info["host"]

    found = 0
    for hwnd in _enum_top_windows():
        if _get_pid(hwnd) != my_pid:
            continue
        cls = _get_class_name(hwnd)
        if cls == "Chrome_WidgetWin_0":
            found = hwnd
            break
        # QtWebEngine 的 Chromium 视图可能以子窗口形式存在
        # （某些版本挂在 Qt 窗口下）——枚举 Qt 窗口的子窗口兜底
        if hwnd == qt_hwnd:
            children = []

            @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def cb2(ch, lp):
                children.append(ch)
                return True

            user32.EnumChildWindows(hwnd, cb2, 0)
            for ch in children:
                if _get_class_name(ch) == "Chrome_WidgetWin_0":
                    found = ch
                    break

    if not found:
        log.warning("Chrome_WidgetWin_0 not found (qt hwnd=0x%x)", qt_hwnd)
        return

    log.info("found Chrome_WidgetWin_0=0x%x, embedding...", found)
    make_child_window(found)
    set_window_ex_style(found, add=WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
                        remove=WS_EX_APPWINDOW)
    user32.SetParent(found, host)
    user32.SetWindowPos(found, HWND_BOTTOM, 0, 0, width, height, SWP_NOACTIVATE)
    user32.ShowWindow(found, SW_SHOWNA)
    log.info("Chrome_WidgetWin_0 embedded to 0x%x", host)
