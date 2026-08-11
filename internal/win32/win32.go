package win32

import (
	"syscall"
	"unsafe"
)

// Module handles
var (
	user32   = syscall.NewLazyDLL("user32.dll")
	kernel32 = syscall.NewLazyDLL("kernel32.dll")
	gdi32    = syscall.NewLazyDLL("gdi32.dll")
)

// Window class styles
const (
	CS_HREDRAW = 0x0002
	CS_VREDRAW = 0x0001
	CS_DBLCLKS = 0x0008
)

// Window styles
const (
	WS_OVERLAPPED       = 0x00000000
	WS_TILED            = 0x00000000
	WS_MAXIMIZEBOX      = 0x00010000
	WS_MINIMIZEBOX      = 0x00020000
	WS_THICKFRAME       = 0x00040000
	WS_SYSMENU           = 0x00080000
	WS_HSCROLL          = 0x00100000
	WS_VSCROLL          = 0x00200000
	WS_DLGFRAME         = 0x00400000
	WS_BORDER           = 0x00800000
	WS_CAPTION          = 0x00C00000
	WS_MAXIMIZE         = 0x01000000
	WS_CLIPCHILDREN     = 0x02000000
	WS_CLIPSIBLINGS     = 0x04000000
	WS_DISABLED         = 0x08000000
	WS_VISIBLE          = 0x10000000
	WS_MINIMIZE         = 0x20000000
	WS_CHILD            = 0x40000000
	WS_POPUP            = 0x80000000
	WS_OVERLAPPEDWINDOW = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX
	WS_POPUPWINDOW      = WS_POPUP | WS_BORDER | WS_SYSMENU
)

// Extended window styles
const (
	WS_EX_DLGMODALFRAME = 0x00000001
	WS_EX_NOPARENTNOTIFY = 0x00000004
	WS_EX_TOPMOST        = 0x00000008
	WS_EX_ACCEPTFILES    = 0x00000010
	WS_EX_TRANSPARENT    = 0x00000020
	WS_EX_MDICHILD       = 0x00000040
	WS_EX_TOOLWINDOW     = 0x00000080
	WS_EX_WINDOWEDGE     = 0x00000100
	WS_EX_CLIENTEDGE     = 0x00000200
	WS_EX_CONTEXTHELP    = 0x00000400
	WS_EX_RIGHT          = 0x00001000
	WS_EX_LEFT           = 0x00000000
	WS_EX_RTLREADING     = 0x00002000
	WS_EX_LTRREADING     = 0x00000000
	WS_EX_LEFTSCROLLBAR  = 0x00004000
	WS_EX_RIGHTSCROLLBAR = 0x00000000
	WS_EX_CONTROLPARENT  = 0x00010000
	WS_EX_STATICEDGE     = 0x00020000
	WS_EX_APPWINDOW      = 0x00040000
	WS_EX_LAYERED        = 0x00080000
	WS_EX_NOINHERITLAYOUT = 0x00100000
	WS_EX_LAYOUTRTL      = 0x00400000
	WS_EX_NOACTIVATE     = 0x08000000
)

// Window messages
const (
	WM_NULL           = 0x0000
	WM_CREATE         = 0x0001
	WM_DESTROY        = 0x0002
	WM_MOVE           = 0x0003
	WM_SIZE           = 0x0005
	WM_ACTIVATE       = 0x0006
	WM_SETFOCUS       = 0x0007
	WM_KILLFOCUS      = 0x0008
	WM_PAINT          = 0x000F
	WM_CLOSE          = 0x0010
	WM_QUIT           = 0x0012
	WM_ERASEBKGND     = 0x0014
	WM_SHOWWINDOW     = 0x0018
	WM_SETCURSOR      = 0x0020
	WM_MOUSEACTIVATE  = 0x0021
	WM_GETMINMAXINFO  = 0x0024
	WM_WINDOWPOSCHANGING = 0x0046
	WM_WINDOWPOSCHANGED  = 0x0047
	WM_NOTIFY         = 0x004E
	WM_COMMAND        = 0x0111
	WM_SYSCOMMAND     = 0x0112
	WM_TIMER          = 0x0113
	WM_HSCROLL        = 0x0114
	WM_VSCROLL        = 0x0115
	WM_INITMENU       = 0x0116
	WM_INITMENUPOPUP  = 0x0117
	WM_CTLCOLOREDIT   = 0x0133
	WM_CTLCOLORBTN    = 0x0135
	WM_CTLCOLORSTATIC = 0x0138
	WM_MOUSEMOVE      = 0x0200
	WM_LBUTTONDOWN    = 0x0201
	WM_LBUTTONUP      = 0x0202
	WM_LBUTTONDBLCLK  = 0x0203
	WM_RBUTTONDOWN    = 0x0204
	WM_RBUTTONUP      = 0x0205
	WM_MBUTTONDOWN    = 0x0207
	WM_MBUTTONUP      = 0x0208
	WM_KEYDOWN        = 0x0100
	WM_KEYUP          = 0x0101
	WM_SYSKEYDOWN     = 0x0104
	WM_SYSKEYUP       = 0x0105
	WM_HOTKEY         = 0x0312
	WM_APP            = 0x8000
)

// Button messages
const (
	BM_GETCHECK = 0x00F0
	BM_SETCHECK = 0x00F1
	BM_GETSTATE = 0x00F2
	BM_SETSTATE = 0x00F3
	BM_SETSTYLE = 0x00F4
	BM_CLICK    = 0x00F5
)

// Button check states
const (
	BST_UNCHECKED  = 0x0000
	BST_CHECKED    = 0x0001
	BST_INDETERMINATE = 0x0002
)

// Static control styles
const (
	SS_LEFT       = 0x00000000
	SS_CENTER     = 0x00000001
	SS_RIGHT      = 0x00000002
	SS_ICON       = 0x00000003
	SS_BLACKRECT  = 0x00000004
	SS_GRAYRECT   = 0x00000005
	SS_WHITERECT  = 0x00000006
	SS_BLACKFRAME = 0x00000007
	SS_GRAYFRAME  = 0x00000008
	SS_WHITEFRAME = 0x00000009
	SS_SIMPLE     = 0x0000000B
	SS_LEFTNOWORDWRAP = 0x0000000C
)

// Edit control styles
const (
	ES_LEFT       = 0x0000
	ES_CENTER     = 0x0001
	ES_RIGHT      = 0x0002
	ES_MULTILINE  = 0x0004
	ES_UPPERCASE  = 0x0008
	ES_LOWERCASE  = 0x0010
	ES_PASSWORD   = 0x0020
	ES_AUTOVSCROLL = 0x0040
	ES_AUTOHSCROLL = 0x0080
	ES_NOHIDESEL  = 0x0100
	ES_READONLY   = 0x0800
	ES_WANTRETURN = 0x1000
	ES_NUMBER     = 0x2000
)

// Button styles
const (
	BS_PUSHBUTTON    = 0x00000000
	BS_DEFPUSHBUTTON = 0x00000001
	BS_CHECKBOX      = 0x00000002
	BS_AUTOCHECKBOX  = 0x00000003
	BS_RADIOBUTTON   = 0x00000004
	BS_3STATE        = 0x00000005
	BS_AUTO3STATE    = 0x00000006
	BS_GROUPBOX      = 0x00000007
	BS_AUTORADIOBUTTON = 0x00000009
)

// Stock objects
const (
	WHITE_BRUSH         = 0
	LTGRAY_BRUSH        = 1
	GRAY_BRUSH          = 2
	DKGRAY_BRUSH        = 3
	BLACK_BRUSH         = 4
	NULL_BRUSH          = 5
	HOLLOW_BRUSH        = 5
	WHITE_PEN           = 6
	BLACK_PEN           = 7
	NULL_PEN            = 8
	OEM_FIXED_FONT      = 10
	ANSI_FIXED_FONT     = 11
	ANSI_VAR_FONT       = 12
	SYSTEM_FONT         = 13
	DEVICE_DEFAULT_FONT = 14
	DEFAULT_PALETTE     = 15
	SYSTEM_FIXED_FONT   = 16
	DEFAULT_GUI_FONT    = 17
	DC_BRUSH            = 18
	DC_PEN              = 19
)

// System metrics
const (
	SM_CXSCREEN = 0
	SM_CYSCREEN = 1
)

// GetWindowLong/SetWindowLong indices
const (
	GWL_WNDPROC   = -4
	GWL_HINSTANCE  = -6
	GWL_ID         = -12
	GWL_STYLE      = -16
	GWL_EXSTYLE    = -20
	GWL_USERDATA   = -21
)

// ShowWindow commands
const (
	SW_HIDE            = 0
	SW_SHOWNORMAL      = 1
	SW_SHOWMINIMIZED   = 2
	SW_SHOWMAXIMIZED   = 3
	SW_SHOWNOACTIVATE  = 4
	SW_SHOW            = 5
	SW_MINIMIZE        = 6
	SW_SHOWMINNOACTIVE = 7
	SW_SHOWNA          = 8
	SW_RESTORE         = 9
	SW_SHOWDEFAULT     = 10
)

// SetWindowPos constants
const (
	HWND_BOTTOM       = 1
	HWND_NOTOPMOST    = ^uintptr(1) // -2
	HWND_TOP          = 0
	HWND_TOPMOST      = ^uintptr(0) // -1
	SWP_NOSIZE         = 0x0001
	SWP_NOMOVE         = 0x0002
	SWP_NOZORDER       = 0x0004
	SWP_NOREDRAW       = 0x0008
	SWP_NOACTIVATE     = 0x0010
	SWP_FRAMECHANGED   = 0x0020
	SWP_SHOWWINDOW     = 0x0040
	SWP_HIDEWINDOW     = 0x0080
	SWP_NOCOPYBITS     = 0x0100
	SWP_NOOWNERZORDER  = 0x0200
	SWP_NOSENDCHANGING = 0x0400
	SWP_DEFERERASE     = 0x2000
	SWP_ASYNCWINDOWPOS = 0x4000
)

// TrackPopupMenu flags
const (
	TPM_LEFTBUTTON   = 0x0000
	TPM_RIGHTBUTTON  = 0x0002
	TPM_LEFTALIGN    = 0x0000
	TPM_CENTERALIGN  = 0x0004
	TPM_RIGHTALIGN   = 0x0008
	TPM_TOPALIGN     = 0x0000
	TPM_VCENTERALIGN = 0x0010
	TPM_BOTTOMALIGN  = 0x0020
	TPM_HORIZONTAL   = 0x0000
	TPM_VERTICAL     = 0x0040
	TPM_NONOTIFY     = 0x0080
	TPM_RETURNCMD    = 0x0100
)

// Menu item flags
const (
	MF_STRING       = 0x00000000
	MF_SEPARATOR    = 0x00000800
	MF_DEFAULT      = 0x00001000
	MF_GRAYED       = 0x00000001
	MF_DISABLED     = 0x00000002
	MF_CHECKED      = 0x00000008
	MF_POPUP        = 0x00000010
)

// COLORREF helpers
type COLORREF uint32
type HBRUSH uintptr
type HFONT uintptr
type HICON uintptr
type HCURSOR uintptr
type HINSTANCE uintptr
type HMENU uintptr
type HWND uintptr
type LPARAM uintptr
type WPARAM uintptr

// RECT struct
type RECT struct {
	Left   int32
	Top    int32
	Right  int32
	Bottom int32
}

// POINT struct
type POINT struct {
	X int32
	Y int32
}

// MSG struct
type MSG struct {
	HWND    HWND
	Message uint32
	WParam  WPARAM
	LParam  LPARAM
	Time    uint32
	Pt      POINT
}

// WNDCLASSEXW struct
type WNDCLASSEXW struct {
	Size       uint32
	Style      uint32
	LpfnWndProc uintptr
	CbClsExtra int32
	CbWndExtra int32
	HInstance  HINSTANCE
	HIcon      HICON
	HCursor    HCURSOR
	HbrBackground HBRUSH
	LpszMenuName *uint16
	LpszClassName *uint16
	HIconSm    HICON
}

// NOTIFYICONDATAW for tray icons
type NOTIFYICONDATAW struct {
	CbSize           uint32
	HWnd             HWND
	UID              uint32
	UFlags           uint32
	UCallbackMessage uint32
	HIcon            HICON
	SzTip            [128]uint16
	DwState          uint32
	DwStateMask      uint32
	SzInfo           [256]uint16
	UVersion         uint32
	SzInfoTitle      [64]uint16
	DwInfoFlags      uint32
	GuidItem         [16]byte // GUID
	HBalloonIcon     HICON
}

// LASTINPUTINFO
type LASTINPUTINFO struct {
	CbSize uint32
	DwTime uint32
}

// ============================================================
// Kernel32 functions
// ============================================================

var (
	procGetModuleHandleW = kernel32.NewProc("GetModuleHandleW")
	procGetTickCount      = kernel32.NewProc("GetTickCount")
)

func GetModuleHandle() (HINSTANCE, error) {
	ret, _, err := procGetModuleHandleW.Call(0)
	if ret == 0 {
		return 0, err
	}
	return HINSTANCE(ret), nil
}

// ============================================================
// User32 functions
// ============================================================

var (
	procRegisterClassExW     = user32.NewProc("RegisterClassExW")
	procCreateWindowExW      = user32.NewProc("CreateWindowExW")
	procDefWindowProcW       = user32.NewProc("DefWindowProcW")
	procDestroyWindow        = user32.NewProc("DestroyWindow")
	procPostQuitMessage      = user32.NewProc("PostQuitMessage")
	procGetMessageW          = user32.NewProc("GetMessageW")
	procTranslateMessage     = user32.NewProc("TranslateMessage")
	procDispatchMessageW     = user32.NewProc("DispatchMessageW")
	procSendMessageW         = user32.NewProc("SendMessageW")
	procSendMessageTimeoutW  = user32.NewProc("SendMessageTimeoutW")
	procPostMessageW         = user32.NewProc("PostMessageW")
	procGetWindowTextW       = user32.NewProc("GetWindowTextW")
	procSetWindowTextW       = user32.NewProc("SetWindowTextW")
	procGetDlgItem           = user32.NewProc("GetDlgItem")
	procEnableWindow         = user32.NewProc("EnableWindow")
	procGetWindowLongPtrW    = user32.NewProc("GetWindowLongPtrW")
	procSetWindowLongPtrW    = user32.NewProc("SetWindowLongPtrW")
	procSetParent            = user32.NewProc("SetParent")
	procGetParent            = user32.NewProc("GetParent")
	procSetWindowPos         = user32.NewProc("SetWindowPos")
	procFindWindowW          = user32.NewProc("FindWindowW")
	procFindWindowExW        = user32.NewProc("FindWindowExW")
	procShowWindow           = user32.NewProc("ShowWindow")
	procEnumWindows          = user32.NewProc("EnumWindows")
	procGetClassNameW        = user32.NewProc("GetClassNameW")
	procGetWindowThreadProcessId = user32.NewProc("GetWindowThreadProcessId")
	procSetForegroundWindow  = user32.NewProc("SetForegroundWindow")
	procGetCursorPos         = user32.NewProc("GetCursorPos")
	procSetCapture           = user32.NewProc("SetCapture")
	procReleaseCapture       = user32.NewProc("ReleaseCapture")
	procGetAsyncKeyState     = user32.NewProc("GetAsyncKeyState")
	procGetLastInputInfo     = user32.NewProc("GetLastInputInfo")
	procMessageBoxW          = user32.NewProc("MessageBoxW")
	procLoadIconW            = user32.NewProc("LoadIconW")
	procLoadCursorW          = user32.NewProc("LoadCursorW")
	procSetCursor            = user32.NewProc("SetCursor")
	procShowCursor           = user32.NewProc("ShowCursor")
	procGetDC                = user32.NewProc("GetDC")
	procReleaseDC            = user32.NewProc("ReleaseDC")
	procBeginPaint           = user32.NewProc("BeginPaint")
	procEndPaint             = user32.NewProc("EndPaint")
	procInvalidateRect       = user32.NewProc("InvalidateRect")
	procUpdateWindow         = user32.NewProc("UpdateWindow")
	procIsWindowVisible      = user32.NewProc("IsWindowVisible")
	procSetLayeredWindowAttributes = user32.NewProc("SetLayeredWindowAttributes")
	procGetClientRect        = user32.NewProc("GetClientRect")
	procGetSystemMetrics     = user32.NewProc("GetSystemMetrics")
	procGetDesktopWindow     = user32.NewProc("GetDesktopWindow")
	procGetShellWindow       = user32.NewProc("GetShellWindow")
	procSystemParametersInfoW = user32.NewProc("SystemParametersInfoW")
	procSetProcessDpiAwarenessContext = user32.NewProc("SetProcessDpiAwarenessContext")
	procCreatePopupMenu      = user32.NewProc("CreatePopupMenu")
	procAppendMenuW          = user32.NewProc("AppendMenuW")
	procSetMenuDefaultItem   = user32.NewProc("SetMenuDefaultItem")
	procTrackPopupMenu       = user32.NewProc("TrackPopupMenu")
	procDestroyMenu          = user32.NewProc("DestroyMenu")
	procCheckMenuItem        = user32.NewProc("CheckMenuItem")
	procDrawMenuBar          = user32.NewProc("DrawMenuBar")
)

var (
	procGetStockObject = gdi32.NewProc("GetStockObject")
	procDeleteObject   = gdi32.NewProc("DeleteObject")
)

func RegisterClassEx(wc *WNDCLASSEXW) (uint16, error) {
	ret, _, err := procRegisterClassExW.Call(uintptr(unsafe.Pointer(wc)))
	if ret == 0 {
		return 0, err
	}
	return uint16(ret), nil
}

func CreateWindowEx(
	dwExStyle uint32,
	className *uint16,
	windowName *uint16,
	dwStyle uint32,
	x, y, width, height int32,
	hWndParent HWND,
	hMenu HMENU,
	hInstance HINSTANCE,
	lpParam unsafe.Pointer,
) (HWND, error) {
	ret, _, err := procCreateWindowExW.Call(
		uintptr(dwExStyle),
		uintptr(unsafe.Pointer(className)),
		uintptr(unsafe.Pointer(windowName)),
		uintptr(dwStyle),
		uintptr(x),
		uintptr(y),
		uintptr(width),
		uintptr(height),
		uintptr(hWndParent),
		uintptr(hMenu),
		uintptr(hInstance),
		uintptr(lpParam),
	)
	if ret == 0 {
		return 0, err
	}
	return HWND(ret), nil
}

func DefWindowProc(hWnd HWND, msg uint32, wParam WPARAM, lParam LPARAM) uintptr {
	ret, _, _ := procDefWindowProcW.Call(uintptr(hWnd), uintptr(msg), uintptr(wParam), uintptr(lParam))
	return ret
}

func DestroyWindow(hWnd HWND) error {
	ret, _, err := procDestroyWindow.Call(uintptr(hWnd))
	if ret == 0 {
		return err
	}
	return nil
}

func PostQuitMessage(exitCode int32) {
	procPostQuitMessage.Call(uintptr(exitCode))
}

func GetMessage(msg *MSG, hWnd HWND, wMsgFilterMin, wMsgFilterMax uint32) int32 {
	ret, _, _ := procGetMessageW.Call(
		uintptr(unsafe.Pointer(msg)),
		uintptr(hWnd),
		uintptr(wMsgFilterMin),
		uintptr(wMsgFilterMax),
	)
	return int32(ret)
}

func TranslateMessage(msg *MSG) bool {
	ret, _, _ := procTranslateMessage.Call(uintptr(unsafe.Pointer(msg)))
	return ret != 0
}

func DispatchMessage(msg *MSG) uintptr {
	ret, _, _ := procDispatchMessageW.Call(uintptr(unsafe.Pointer(msg)))
	return ret
}

func SendMessage(hWnd HWND, msg uint32, wParam WPARAM, lParam LPARAM) uintptr {
	ret, _, _ := procSendMessageW.Call(uintptr(hWnd), uintptr(msg), uintptr(wParam), uintptr(lParam))
	return ret
}

// SendMessageTimeout with SMTO_NORMAL (0)
func SendMessageTimeout(hWnd HWND, msg uint32, wParam WPARAM, lParam LPARAM, flags uint32, timeout uint32) uintptr {
	ret, _, _ := procSendMessageTimeoutW.Call(uintptr(hWnd), uintptr(msg), uintptr(wParam), uintptr(lParam), uintptr(flags), uintptr(timeout), 0)
	return ret
}

func PostMessage(hWnd HWND, msg uint32, wParam WPARAM, lParam LPARAM) error {
	ret, _, err := procPostMessageW.Call(uintptr(hWnd), uintptr(msg), uintptr(wParam), uintptr(lParam))
	if ret == 0 {
		return err
	}
	return nil
}

func GetWindowText(hWnd HWND, buf []uint16) int {
	ret, _, _ := procGetWindowTextW.Call(uintptr(hWnd), uintptr(unsafe.Pointer(&buf[0])), uintptr(len(buf)-1))
	return int(ret)
}

func SetWindowText(hWnd HWND, text string) error {
	u16, err := syscall.UTF16PtrFromString(text)
	if err != nil {
		return err
	}
	procSetWindowTextW.Call(uintptr(hWnd), uintptr(unsafe.Pointer(u16)))
	return nil
}

func GetDlgItem(hDlg HWND, nIDDlgItem int32) HWND {
	ret, _, _ := procGetDlgItem.Call(uintptr(hDlg), uintptr(nIDDlgItem))
	return HWND(ret)
}

func EnableWindow(hWnd HWND, enable bool) {
	var val uintptr
	if enable {
		val = 1
	}
	procEnableWindow.Call(uintptr(hWnd), val)
}

func GetWindowLongPtr(hWnd HWND, nIndex int32) uintptr {
	ret, _, _ := procGetWindowLongPtrW.Call(uintptr(hWnd), uintptr(nIndex))
	return ret
}

func SetWindowLongPtr(hWnd HWND, nIndex int32, dwNewLong uintptr) uintptr {
	ret, _, _ := procSetWindowLongPtrW.Call(uintptr(hWnd), uintptr(nIndex), dwNewLong)
	return ret
}

func SetParent(hWndChild, hWndNewParent HWND) HWND {
	ret, _, _ := procSetParent.Call(uintptr(hWndChild), uintptr(hWndNewParent))
	return HWND(ret)
}

func GetParent(hWnd HWND) HWND {
	ret, _, _ := procGetParent.Call(uintptr(hWnd))
	return HWND(ret)
}

func SetWindowPos(hWnd HWND, hWndInsertAfter HWND, x, y, cx, cy int32, uFlags uint32) error {
	ret, _, err := procSetWindowPos.Call(
		uintptr(hWnd),
		uintptr(hWndInsertAfter),
		uintptr(x), uintptr(y),
		uintptr(cx), uintptr(cy),
		uintptr(uFlags),
	)
	if ret == 0 {
		return err
	}
	return nil
}

func FindWindow(className, windowName *uint16) HWND {
	ret, _, _ := procFindWindowW.Call(
		uintptr(unsafe.Pointer(className)),
		uintptr(unsafe.Pointer(windowName)),
	)
	return HWND(ret)
}

func FindWindowEx(hWndParent, hWndChildAfter HWND, className, windowName *uint16) HWND {
	ret, _, _ := procFindWindowExW.Call(
		uintptr(hWndParent),
		uintptr(hWndChildAfter),
		uintptr(unsafe.Pointer(className)),
		uintptr(unsafe.Pointer(windowName)),
	)
	return HWND(ret)
}

func ShowWindow(hWnd HWND, nCmdShow int32) bool {
	ret, _, _ := procShowWindow.Call(uintptr(hWnd), uintptr(nCmdShow))
	return ret != 0
}

func EnumWindows(callback uintptr, lParam LPARAM) bool {
	ret, _, _ := procEnumWindows.Call(callback, uintptr(lParam))
	return ret != 0
}

func GetClassName(hWnd HWND, buf []uint16) int {
	ret, _, _ := procGetClassNameW.Call(uintptr(hWnd), uintptr(unsafe.Pointer(&buf[0])), uintptr(len(buf)-1))
	return int(ret)
}

func SetForegroundWindow(hWnd HWND) bool {
	ret, _, _ := procSetForegroundWindow.Call(uintptr(hWnd))
	return ret != 0
}

func GetCursorPos(pt *POINT) bool {
	ret, _, _ := procGetCursorPos.Call(uintptr(unsafe.Pointer(pt)))
	return ret != 0
}

func GetAsyncKeyState(vKey int32) int16 {
	ret, _, _ := procGetAsyncKeyState.Call(uintptr(vKey))
	return int16(ret)
}

func GetLastInputInfo(lii *LASTINPUTINFO) bool {
	ret, _, _ := procGetLastInputInfo.Call(uintptr(unsafe.Pointer(lii)))
	return ret != 0
}

func GetTickCount() uint32 {
	ret, _, _ := procGetTickCount.Call()
	return uint32(ret)
}

func MessageBox(hWnd HWND, text, caption string, uType uint32) int32 {
	t, _ := syscall.UTF16PtrFromString(text)
	c, _ := syscall.UTF16PtrFromString(caption)
	ret, _, _ := procMessageBoxW.Call(uintptr(hWnd), uintptr(unsafe.Pointer(t)), uintptr(unsafe.Pointer(c)), uintptr(uType))
	return int32(ret)
}

func LoadIcon(hInstance HINSTANCE, lpIconName *uint16) HICON {
	ret, _, _ := procLoadIconW.Call(uintptr(hInstance), uintptr(unsafe.Pointer(lpIconName)))
	return HICON(ret)
}

func LoadCursor(hInstance HINSTANCE, lpCursorName *uint16) HCURSOR {
	ret, _, _ := procLoadCursorW.Call(uintptr(hInstance), uintptr(unsafe.Pointer(lpCursorName)))
	return HCURSOR(ret)
}

func GetDC(hWnd HWND) uintptr {
	ret, _, _ := procGetDC.Call(uintptr(hWnd))
	return ret
}

func ReleaseDC(hWnd HWND, hDC uintptr) int32 {
	ret, _, _ := procReleaseDC.Call(uintptr(hWnd), hDC)
	return int32(ret)
}

func GetClientRect(hWnd HWND, rect *RECT) bool {
	ret, _, _ := procGetClientRect.Call(uintptr(hWnd), uintptr(unsafe.Pointer(rect)))
	return ret != 0
}

func GetSystemMetrics(nIndex int32) int32 {
	ret, _, _ := procGetSystemMetrics.Call(uintptr(nIndex))
	return int32(ret)
}

func GetDesktopWindow() HWND {
	ret, _, _ := procGetDesktopWindow.Call()
	return HWND(ret)
}

func CreatePopupMenu() HMENU {
	ret, _, _ := procCreatePopupMenu.Call()
	return HMENU(ret)
}

func AppendMenu(hMenu HMENU, uFlags uint32, uIDNewItem uintptr, lpNewItem *uint16) bool {
	var itemPtr uintptr
	if uFlags&MF_STRING != 0 {
		itemPtr = uintptr(unsafe.Pointer(lpNewItem))
	}
	ret, _, _ := procAppendMenuW.Call(uintptr(hMenu), uintptr(uFlags), uIDNewItem, itemPtr)
	return ret != 0
}

func SetMenuDefaultItem(hMenu HMENU, uItem uint32, fByPos uint32) bool {
	ret, _, _ := procSetMenuDefaultItem.Call(uintptr(hMenu), uintptr(uItem), uintptr(fByPos))
	return ret != 0
}

func TrackPopupMenu(hMenu HMENU, uFlags uint32, x, y int32, nReserved int32, hWnd HWND, prcRect *RECT) int32 {
	ret, _, _ := procTrackPopupMenu.Call(
		uintptr(hMenu), uintptr(uFlags),
		uintptr(x), uintptr(y),
		uintptr(nReserved), uintptr(hWnd),
		uintptr(unsafe.Pointer(prcRect)),
	)
	return int32(ret)
}

func DestroyMenu(hMenu HMENU) bool {
	ret, _, _ := procDestroyMenu.Call(uintptr(hMenu))
	return ret != 0
}

func GetStockObject(fnObject int32) HBRUSH {
	ret, _, _ := procGetStockObject.Call(uintptr(fnObject))
	return HBRUSH(ret)
}

// LWA_ALPHA
const LWA_ALPHA = 0x00000002

func SetLayeredWindowAttributes(hWnd HWND, crKey COLORREF, bAlpha byte, dwFlags uint32) bool {
	ret, _, _ := procSetLayeredWindowAttributes.Call(uintptr(hWnd), uintptr(crKey), uintptr(bAlpha), uintptr(dwFlags))
	return ret != 0
}

func UpdateWindow(hWnd HWND) bool {
	ret, _, _ := procUpdateWindow.Call(uintptr(hWnd))
	return ret != 0
}

func IsWindowVisible(hWnd HWND) bool {
	ret, _, _ := procIsWindowVisible.Call(uintptr(hWnd))
	return ret != 0
}

// DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
const DpiAwarenessPerMonitorV2 = ^uintptr(3) // 0xFFFFFFFC

// SetProcessDpiAwareness makes the process per-monitor DPI aware.
// Must be called before any window creation.
func SetProcessDpiAwareness() {
	// Try PerMonitorV2 first, fall back to system DPI aware (0xFFFFFFFE)
	r, _, _ := procSetProcessDpiAwarenessContext.Call(DpiAwarenessPerMonitorV2)
	if r == 0 {
		procSetProcessDpiAwarenessContext.Call(^uintptr(1)) // DPI_AWARENESS_CONTEXT_SYSTEM_AWARE
	}
}

func ShowCursor(bShow bool) int32 {
	var v uintptr
	if bShow {
		v = 1
	}
	ret, _, _ := procShowCursor.Call(v)
	return int32(ret)
}

// Typed window Z-order values for use with SetWindowPos
var (
	HWND_TOPMOST_HWND = HWND(^uintptr(0))
	HWND_NOTOPMOST_HWND = HWND(^uintptr(1))
	HWND_BOTTOM_HWND = HWND(1)
	HWND_TOP_HWND = HWND(0)
)