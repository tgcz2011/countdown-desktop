package tray

import (
	"fmt"
	"sync"
	"unsafe"

	"golang.org/x/sys/windows"

	"github.com/tgcz2011/countdown-desktop/internal/win32"
)

const (
	nimAdd    = 0x00000000
	nimDelete = 0x00000002
)

const wmTrayCallback = win32.WM_APP + 1

type Action int

const (
	ActionToggleWallpaper  Action = 1
	ActionToggleScreensaver Action = 2
	ActionOpenSettings     Action = 3
	ActionExit             Action = 4
)

type Icon struct {
	mu      sync.Mutex
	hwnd    win32.HWND
	actions chan Action
	iconID  uint32
}

func New(actions chan Action) (*Icon, error) {
	t := &Icon{actions: actions, iconID: 1}

	className, _ := windows.UTF16PtrFromString("CountdownTrayClass")
	hInst, err := win32.GetModuleHandle()
	if err != nil { return nil, fmt.Errorf("GetModuleHandle: %w", err) }

	wc := win32.WNDCLASSEXW{
		LpfnWndProc:   windows.NewCallback(t.wndProc),
		HInstance:     hInst,
		LpszClassName: className,
	}
	wc.Size = uint32(unsafe.Sizeof(wc))
	if _, err := win32.RegisterClassEx(&wc); err != nil { return nil, fmt.Errorf("RegisterClassEx: %w", err) }

	hwnd, err := win32.CreateWindowEx(0, className, windows.StringToUTF16Ptr("CountdownTray"),
		0, 0, 0, 0, 0, 0, 0, hInst, nil)
	if err != nil { return nil, fmt.Errorf("CreateWindowEx: %w", err) }
	t.hwnd = hwnd

	if err := t.addIcon(); err != nil { win32.DestroyWindow(hwnd); return nil, err }
	return t, nil
}

func (t *Icon) addIcon() error {
	nid := win32.NOTIFYICONDATAW{
		UFlags:           0x00000001 | 0x00000004, // NIF_MESSAGE | NIF_TIP
		UCallbackMessage: wmTrayCallback,
		UVersion:         4,
	}
	nid.CbSize = uint32(unsafe.Sizeof(nid))
	nid.HWnd = t.hwnd
	nid.UID = t.iconID
	tipStr, _ := windows.UTF16FromString("Countdown Desktop")
	copy(nid.SzTip[:], tipStr)

	// Load icon
	iconClass, _ := windows.UTF16PtrFromString("MAINICON")
	icon := win32.LoadIcon(0, iconClass)
	if icon == 0 {
		// Use IDI_APPLICATION (32512)
		icon = win32.LoadIcon(0, (*uint16)(unsafe.Pointer(uintptr(32512))))
	}
	nid.HIcon = icon
	if icon != 0 && icon != win32.HICON(32512) {
		nid.UFlags |= 0x00000002 // NIF_ICON
	}

	// Call Shell_NotifyIconW
	shell32 := windows.NewLazySystemDLL("shell32.dll")
	procShellNotifyIconW := shell32.NewProc("Shell_NotifyIconW")
	procShellNotifyIconW.Call(nimAdd, uintptr(unsafe.Pointer(&nid)))
	procShellNotifyIconW.Call(0x00000004, uintptr(unsafe.Pointer(&nid))) // NIM_SETVERSION
	return nil
}

func (t *Icon) Remove() {
	nid := win32.NOTIFYICONDATAW{CbSize: uint32(unsafe.Sizeof(win32.NOTIFYICONDATAW{})), HWnd: t.hwnd, UID: t.iconID}
	shell32 := windows.NewLazySystemDLL("shell32.dll")
	procShellNotifyIconW := shell32.NewProc("Shell_NotifyIconW")
	procShellNotifyIconW.Call(nimDelete, uintptr(unsafe.Pointer(&nid)))
	win32.DestroyWindow(t.hwnd)
}

func (t *Icon) HWND() win32.HWND { return t.hwnd }

func (t *Icon) showMenu() {
	menu := win32.CreatePopupMenu()
	if menu == 0 { return }
	defer win32.DestroyMenu(menu)

	wpLabel, _ := windows.UTF16PtrFromString("Toggle Wallpaper")
	ssLabel, _ := windows.UTF16PtrFromString("Toggle Screensaver")
	setLabel, _ := windows.UTF16PtrFromString("Settings")
	exitLabel, _ := windows.UTF16PtrFromString("Exit")

	win32.AppendMenu(menu, win32.MF_STRING, uintptr(ActionToggleWallpaper), wpLabel)
	win32.AppendMenu(menu, win32.MF_STRING, uintptr(ActionToggleScreensaver), ssLabel)
	win32.AppendMenu(menu, win32.MF_SEPARATOR, 0, nil)
	win32.AppendMenu(menu, win32.MF_STRING, uintptr(ActionOpenSettings), setLabel)
	win32.AppendMenu(menu, win32.MF_SEPARATOR, 0, nil)
	win32.AppendMenu(menu, win32.MF_STRING, uintptr(ActionExit), exitLabel)
	win32.SetMenuDefaultItem(menu, uint32(ActionOpenSettings), 0)

	var pt win32.POINT
	win32.GetCursorPos(&pt)
	win32.SetForegroundWindow(t.hwnd)

	selected := win32.TrackPopupMenu(menu,
		win32.TPM_LEFTALIGN|win32.TPM_BOTTOMALIGN|win32.TPM_RIGHTBUTTON|win32.TPM_RETURNCMD,
		pt.X, pt.Y, 0, t.hwnd, nil)

	if selected > 0 {
		win32.PostMessage(t.hwnd, win32.WM_APP+2, win32.WPARAM(selected), 0)
	}
}

func (t *Icon) wndProc(hwnd win32.HWND, msg uint32, wparam, lparam uintptr) uintptr {
	switch msg {
	case wmTrayCallback:
		if lparam == 0x0205 || lparam == 0x0204 { t.showMenu() } else if lparam == 0x0203 { t.actions <- ActionOpenSettings }
		return 0
	case win32.WM_APP + 2:
		t.actions <- Action(wparam)
		return 0
	case win32.WM_DESTROY:
		win32.PostQuitMessage(0)
		return 0
	}
	return win32.DefWindowProc(hwnd, msg, win32.WPARAM(wparam), win32.LPARAM(lparam))
}
