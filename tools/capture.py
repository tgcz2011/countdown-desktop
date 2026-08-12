# -*- coding: utf-8 -*-
"""开发验证用：捕获桌面宿主窗口/屏幕内容。用法: capture.py <out.png> [host|screen]"""
import ctypes
import sys
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.FindWindowW.restype = wintypes.HWND
user32.FindWindowExW.restype = wintypes.HWND
user32.GetWindowLongPtrW.restype = ctypes.c_long
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
GWL_STYLE, GWL_EXSTYLE = -16, -20


def find_host():
    progman = user32.FindWindowW("Progman", None)
    user32.SendMessageTimeoutW(progman, 0x052C, 0xD, 0x1, 0, 1000, None)
    dv = user32.FindWindowExW(progman, None, "SHELLDLL_DefView", None)
    if dv:
        return progman
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lp):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        if buf.value == "WorkerW" and user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(cb, 0)
    if not found:
        return progman
    nxt = user32.FindWindowExW(None, found[0], "WorkerW", None)
    return nxt if nxt else found[0]


def capture_fullcontent(hwnd, path):
    from PIL import Image
    rc = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rc))
    w, h = rc.right - rc.left, rc.bottom - rc.top
    gdi = ctypes.windll.gdi32
    hdc = user32.GetDC(hwnd)
    memdc = gdi.CreateCompatibleDC(hdc)
    bmp = gdi.CreateCompatibleBitmap(hdc, w, h)
    gdi.SelectObject(memdc, bmp)
    gdi.BitBlt(memdc, 0, 0, w, h, hdc, 0, 0, 0xCC0020)
    ok = user32.PrintWindow(hwnd, memdc, 2)
    bmi = (ctypes.c_ubyte * 40)()
    bmi[0:4] = (40).to_bytes(4, "little")
    bmi[4:8] = w.to_bytes(4, "little", signed=True)
    bmi[8:12] = (-h).to_bytes(4, "little", signed=True)
    bmi[12:14] = (1).to_bytes(2, "little")
    bmi[14:16] = (32).to_bytes(2, "little")
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi.GetDIBits(memdc, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    img = Image.frombuffer("RGB", (w, h), buf.raw, "raw", "BGRX", 0, 1)
    img.save(path)
    gdi.DeleteObject(bmp)
    gdi.DeleteDC(memdc)
    user32.ReleaseDC(hwnd, hdc)
    print(f"saved {path} {w}x{h} ok={ok}")


def capture_screen(path):
    from PIL import ImageGrab
    img = ImageGrab.grab(all_screens=True)
    img.save(path)
    print(f"saved screen {path} {img.size}")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "cap.png"
    mode = sys.argv[2] if len(sys.argv) > 2 else "host"
    if mode == "host":
        capture_fullcontent(find_host(), out)
    else:
        capture_screen(out)
