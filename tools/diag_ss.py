# -*- coding: utf-8 -*-
"""诊断：屏保窗口几何 vs 虚拟屏幕/工作区。"""
import ctypes
import sys
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.FindWindowW.restype = wintypes.HWND
user32.GetWindowLongPtrW.restype = ctypes.c_long
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]

try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    pass

hwnd = user32.FindWindowW(None, "CountdownScreensaver")
print("ss hwnd=0x%x" % (hwnd or 0))
if hwnd:
    rc = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rc))
    print("ss rect: %d,%d -> %d,%d (w=%d h=%d)" % (
        rc.left, rc.top, rc.right, rc.bottom, rc.right - rc.left, rc.bottom - rc.top))
    style = user32.GetWindowLongPtrW(hwnd, -16)
    print("style=0x%08x" % (style & 0xFFFFFFFF))

vs_x = user32.GetSystemMetrics(76)
vs_y = user32.GetSystemMetrics(77)
vs_w = user32.GetSystemMetrics(78)
vs_h = user32.GetSystemMetrics(79)
print("virtual screen: %d,%d %dx%d" % (vs_x, vs_y, vs_w, vs_h))

wa = wintypes.RECT()
user32.SystemParametersInfoW(48, 0, ctypes.byref(wa), 0)  # SPI_GETWORKAREA
print("work area: %d,%d -> %d,%d" % (wa.left, wa.top, wa.right, wa.bottom))

tray = user32.FindWindowW("Shell_TrayWnd", None)
print("taskbar visible=%s" % bool(user32.IsWindowVisible(tray)))
