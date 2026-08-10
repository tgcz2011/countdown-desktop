package settings

import (
	"fmt"
	"strconv"
	"unsafe"

	"golang.org/x/sys/windows"

	"github.com/tgcz2011/countdown-desktop/internal/config"
	"github.com/tgcz2011/countdown-desktop/internal/win32"
)

const (
	idWallpaperURL   = 1001
	idScreensaverURL = 1002
	idTimeout        = 1003
	idWpEnable       = 1004
	idSsEnable       = 1005
	idApply          = 1006
	idSave           = 1007
	idWpTest         = 1008
	idSsTest         = 1009
)

type Window struct {
	hwnd              win32.HWND
	cfg               *config.Config
	onSave            func(*config.Config)
	onTestWallpaper   func()
	onTestScreensaver func()
}

func New(cfg *config.Config, onSave func(*config.Config), onTestWp, onTestSs func()) (*Window, error) {
	w := &Window{cfg: cfg, onSave: onSave, onTestWallpaper: onTestWp, onTestScreensaver: onTestSs}

	className, _ := windows.UTF16PtrFromString("CountdownSettingsClass")
	hInst, err := win32.GetModuleHandle()
	if err != nil { return nil, fmt.Errorf("GetModuleHandle: %w", err) }

	wc := win32.WNDCLASSEXW{
		Style:         win32.CS_HREDRAW | win32.CS_VREDRAW,
		LpfnWndProc:   windows.NewCallback(w.wndProc),
		HInstance:     hInst,
		HbrBackground: win32.GetStockObject(win32.WHITE_BRUSH),
		LpszClassName: className,
	}
	wc.Size = uint32(unsafe.Sizeof(wc))
	if _, err := win32.RegisterClassEx(&wc); err != nil { return nil, fmt.Errorf("RegisterClassEx: %w", err) }

	hwnd, err := win32.CreateWindowEx(
		win32.WS_EX_APPWINDOW,
		className,
		windows.StringToUTF16Ptr("Countdown Desktop - Settings"),
		win32.WS_OVERLAPPEDWINDOW|win32.WS_VISIBLE,
		200, 200, 500, 400,
		0, 0, hInst, unsafe.Pointer(w),
	)
	if err != nil { return nil, fmt.Errorf("CreateWindowEx: %w", err) }
	w.hwnd = hwnd
	return w, nil
}

func (w *Window) HWND() win32.HWND { return w.hwnd }
func (w *Window) Close() { win32.DestroyWindow(w.hwnd) }

func createLabel(hParent win32.HWND, text string, x, y, width, height int32) win32.HWND {
	u16, _ := windows.UTF16PtrFromString(text)
	cName, _ := windows.UTF16PtrFromString("STATIC")
	hInst, _ := win32.GetModuleHandle()
	hwnd, _ := win32.CreateWindowEx(0, cName, u16, win32.WS_CHILD|win32.WS_VISIBLE|win32.SS_LEFT,
		x, y, width, height, hParent, 0, hInst, nil)
	return hwnd
}

func createEdit(hParent win32.HWND, id int32, text string, x, y, width, height int32) win32.HWND {
	cName, _ := windows.UTF16PtrFromString("EDIT")
	hInst, _ := win32.GetModuleHandle()
	hwnd, _ := win32.CreateWindowEx(win32.WS_EX_CLIENTEDGE, cName, nil,
		win32.WS_CHILD|win32.WS_VISIBLE|win32.WS_BORDER|win32.ES_AUTOHSCROLL,
		x, y, width, height, hParent, win32.HMENU(id), hInst, nil)
	if text != "" { win32.SetWindowText(hwnd, text)
	}
	return hwnd
}

func createButton(hParent win32.HWND, id int32, text string, x, y, width, height int32) win32.HWND {
	u16, _ := windows.UTF16PtrFromString(text)
	cName, _ := windows.UTF16PtrFromString("BUTTON")
	hInst, _ := win32.GetModuleHandle()
	hwnd, _ := win32.CreateWindowEx(0, cName, u16, win32.WS_CHILD|win32.WS_VISIBLE|win32.BS_PUSHBUTTON,
		x, y, width, height, hParent, win32.HMENU(id), hInst, nil)
	return hwnd
}

func createCheckbox(hParent win32.HWND, id int32, text string, checked bool, x, y, width, height int32) win32.HWND {
	u16, _ := windows.UTF16PtrFromString(text)
	cName, _ := windows.UTF16PtrFromString("BUTTON")
	hInst, _ := win32.GetModuleHandle()
	hwnd, _ := win32.CreateWindowEx(0, cName, u16, win32.WS_CHILD|win32.WS_VISIBLE|win32.BS_AUTOCHECKBOX,
		x, y, width, height, hParent, win32.HMENU(id), hInst, nil)
	if checked {
		win32.SendMessage(hwnd, win32.BM_SETCHECK, 1, 0)
	}
	return hwnd
}

func getEditText(hwnd win32.HWND) string {
	buf := make([]uint16, 2048)
	n := win32.GetWindowText(hwnd, buf)
	if n > 0 { return windows.UTF16ToString(buf[:n]) }
	return ""
}

func getCheckState(hwnd win32.HWND) bool {
	ret := win32.SendMessage(hwnd, win32.BM_GETCHECK, 0, 0)
	return ret == 1
}

func procGetDlgItemAddr(hwnd win32.HWND, id int32) win32.HWND {
	return win32.GetDlgItem(hwnd, id)
}

func (w *Window) wndProc(hwnd win32.HWND, msg uint32, wp, lp uintptr) uintptr {
	switch msg {
	case win32.WM_CREATE:
		y := int32(10)
		createLabel(hwnd, "Wallpaper URL:", 10, y+4, 120, 20)
		createEdit(hwnd, idWallpaperURL, w.cfg.WallpaperURL, 130, y, 280, 22)
		y += 30
		createCheckbox(hwnd, idWpEnable, "Enable Wallpaper", w.cfg.WallpaperEnabled, 130, y, 150, 20)
		createButton(hwnd, idWpTest, "Test", 300, y, 60, 22)
		y += 35
		createLabel(hwnd, "Screensaver URL:", 10, y+4, 120, 20)
		createEdit(hwnd, idScreensaverURL, w.cfg.ScreensaverURL, 130, y, 280, 22)
		y += 30
		createCheckbox(hwnd, idSsEnable, "Enable Screensaver", w.cfg.ScreensaverEnabled, 130, y, 150, 20)
		createButton(hwnd, idSsTest, "Test", 300, y, 60, 22)
		y += 35
		createLabel(hwnd, "Timeout (seconds):", 10, y+4, 120, 20)
		createEdit(hwnd, idTimeout, strconv.Itoa(w.cfg.ScreensaverTime), 130, y, 80, 22)
		y += 50
		createButton(hwnd, idApply, "Apply", 130, y, 80, 28)
		createButton(hwnd, idSave, "Save && Close", 220, y, 120, 28)
		return 0

	case win32.WM_COMMAND:
		wpLo := int32(wp & 0xFFFF)
		switch wpLo {
		case idApply: w.applySettings(hwnd)
		case idSave:
			w.applySettings(hwnd)
			if err := w.cfg.Save(); err != nil { fmt.Printf("Save config error: %v\n", err) }
			if w.onSave != nil { w.onSave(w.cfg) }
			win32.DestroyWindow(hwnd)
		case idWpTest:
			if w.onTestWallpaper != nil { w.onTestWallpaper() }
		case idSsTest:
			if w.onTestScreensaver != nil { w.onTestScreensaver() }
		}
		return 0

	case win32.WM_CLOSE:
		win32.DestroyWindow(hwnd)
		return 0

	case win32.WM_DESTROY:
		win32.PostQuitMessage(0)
		return 0
	}
	return win32.DefWindowProc(hwnd, msg, win32.WPARAM(wp), win32.LPARAM(lp))
}

func (w *Window) applySettings(hwnd win32.HWND) {
	wpURL := getEditText(win32.GetDlgItem(hwnd, idWallpaperURL))
	ssURL := getEditText(win32.GetDlgItem(hwnd, idScreensaverURL))
	timeoutStr := getEditText(win32.GetDlgItem(hwnd, idTimeout))
	wpEnable := getCheckState(win32.GetDlgItem(hwnd, idWpEnable))
	ssEnable := getCheckState(win32.GetDlgItem(hwnd, idSsEnable))

	if wpURL != "" { w.cfg.WallpaperURL = wpURL }
	if ssURL != "" { w.cfg.ScreensaverURL = ssURL }
	w.cfg.WallpaperEnabled = wpEnable
	w.cfg.ScreensaverEnabled = ssEnable
	if t, err := strconv.Atoi(timeoutStr); err == nil && t > 0 { w.cfg.ScreensaverTime = t }
}
