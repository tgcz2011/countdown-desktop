# -*- coding: utf-8 -*-
"""诊断2：屏保窗口几何夹紧来源实验。"""
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
dwm = ctypes.windll.dwmapi
user32.FindWindowW.restype = wintypes.HWND
user32.GetWindowLongPtrW.restype = ctypes.c_long
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongPtrW.restype = ctypes.c_long
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]

try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    pass

h = user32.FindWindowW(None, "CountdownScreensaver")
print("hwnd=0x%x" % (h or 0))
if not h:
    raise SystemExit(1)


def rects(tag):
    rc = wintypes.RECT()
    user32.GetWindowRect(h, ctypes.byref(rc))
    cr = wintypes.RECT()
    user32.GetClientRect(h, ctypes.byref(cr))
    ext = wintypes.RECT()
    dwm.DwmGetWindowAttribute(h, 9, ctypes.byref(ext), ctypes.sizeof(ext))
    print(f"[{tag}] win={rc.right-rc.left}x{rc.bottom-rc.top} client={cr.right}x{cr.bottom} "
          f"dwmbounds={ext.right-ext.left}x{ext.bottom-ext.top} style=0x{user32.GetWindowLongPtrW(h,-16)&0xFFFFFFFF:08x}")


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


mi = MONITORINFO()
mi.cbSize = ctypes.sizeof(MONITORINFO)
user32.GetMonitorInfoW(user32.MonitorFromWindow(h, 2), ctypes.byref(mi))
print("monitor: %dx%d work=%dx%d" % (
    mi.rcMonitor.right - mi.rcMonitor.left, mi.rcMonitor.bottom - mi.rcMonitor.top,
    mi.rcWork.right - mi.rcWork.left, mi.rcWork.bottom - mi.rcWork.top))

rects("initial")

# a) frame changed + setwindowpos
user32.SetWindowPos(h, -1, 0, 0, 3840, 1746, 0x0020 | 0x0040)
time.sleep(0.5)
rects("after SWP+FRAMECHANGED")

# b) placement maximize
class WP(ctypes.Structure):
    _fields_ = [("length", wintypes.UINT), ("flags", wintypes.UINT),
                ("showCmd", wintypes.UINT), ("ptMin", wintypes.POINT),
                ("ptMax", wintypes.POINT), ("rcNormal", wintypes.RECT)]


wp = WP()
wp.length = ctypes.sizeof(WP)
user32.GetWindowPlacement(h, ctypes.byref(wp))
wp.showCmd = 3  # SW_SHOWMAXIMIZED
user32.SetWindowPlacement(h, ctypes.byref(wp))
time.sleep(0.5)
rects("after maximize")

# c) strip any frame styles then SWP
st = user32.GetWindowLongPtrW(h, -16)
st &= ~(0x00C00000 | 0x00040000 | 0x00080000)  # caption/thickframe/dlgframe
user32.SetWindowLongPtrW(h, -16, st)
user32.SetWindowPos(h, -1, 0, 0, 3840, 1746, 0x0020 | 0x0040)
time.sleep(0.5)
rects("after strip styles")

user32.keybd_event(0x41, 0, 0, 0)
user32.keybd_event(0x41, 0, 2, 0)
