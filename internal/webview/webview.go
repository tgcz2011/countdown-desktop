package webview

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sync"
	"syscall"
	"time"
	"unsafe"

	"golang.org/x/sys/windows"
	"golang.org/x/sys/windows/registry"


	"github.com/tgcz2011/countdown-desktop/internal/win32"
)

var (
	modWebView2Loader                    *windows.LazyDLL
	procCreateCoreWebView2Environment    *windows.LazyProc
	procGetAvailableBrowserVersionString *windows.LazyProc

	// activeHandlers keeps COM callback objects alive across the Go/COM boundary.
	// WebView2 holds raw pointers to these objects; without a Go-side reference the
	// GC could collect them while WebView2 still calls into them.
	activeHandlers sync.Map
)

// keepHandler registers a COM handler so the GC won't collect it.
func keepHandler(h interface{}) {
	activeHandlers.Store(h, struct{}{})
}

// releaseHandler unregisters a COM handler once its callback has fired.
func releaseHandler(h interface{}) {
	activeHandlers.Delete(h)
}

var (
	ole32               = windows.NewLazySystemDLL("ole32.dll")
	procCoInitializeEx  = ole32.NewProc("CoInitializeEx")
	procCoUninitialize  = ole32.NewProc("CoUninitialize")
)

// ensureCom initializes COM on the calling thread (safe to call multiple times).
// Returns true if we are responsible for uninitializing (first init on this thread).
func ensureCom() bool {
	r, _, _ := procCoInitializeEx.Call(0, 0x00000002) // COINIT_APARTMENTTHREADED
	return r == 0 // S_OK = first init
}

func uninitCom(owned bool) {
	if owned {
		procCoUninitialize.Call()
	}
}

// loadWebView2Loader finds and loads WebView2Loader.dll.
// Search order: 1) next to the executable (bundled) 2) WebView2 Runtime install dir (registry) 3) System32
func loadWebView2Loader() error {
	if modWebView2Loader != nil {
		if err := modWebView2Loader.Load(); err == nil {
			return nil
		}
	}

	// 1. exe directory (bundled with the app)
	if exe, err := os.Executable(); err == nil {
		loaderPath := filepath.Join(filepath.Dir(exe), "WebView2Loader.dll")
		if _, statErr := os.Stat(loaderPath); statErr == nil {
			dll := windows.NewLazyDLL(loaderPath)
			if err := dll.Load(); err == nil {
				modWebView2Loader = dll
				return nil
			}
		}
	}

	// 2. WebView2 Runtime install dir from registry
	if pv, ok := webView2RuntimeVersion(); ok {
		for _, base := range []string{
			"C:\\Program Files (x86)\\Microsoft\\EdgeWebView\\Application",
			"C:\\Program Files\\Microsoft\\EdgeWebView\\Application",
		} {
			loaderPath := filepath.Join(base, pv, "WebView2Loader.dll")
			if _, statErr := os.Stat(loaderPath); statErr == nil {
				dll := windows.NewLazyDLL(loaderPath)
				if err := dll.Load(); err == nil {
					modWebView2Loader = dll
					return nil
				}
			}
		}
	}

	// 3. System32 fallback
	dll := windows.NewLazySystemDLL("WebView2Loader.dll")
	if err := dll.Load(); err == nil {
		modWebView2Loader = dll
		return nil
	}
	return fmt.Errorf("WebView2Loader.dll not found")
}

// webView2RuntimeVersion reads the installed WebView2 Runtime version from registry.
func webView2RuntimeVersion() (string, bool) {
	const keyPath = `SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`
	k, err := registry.OpenKey(registry.LOCAL_MACHINE, keyPath, registry.QUERY_VALUE)
	if err != nil {
		return "", false
	}
	defer k.Close()
	pv, _, err := k.GetStringValue("pv")
	if err != nil || pv == "" {
		return "", false
	}
	return pv, true
}

// IsAvailable checks if WebView2 runtime + loader are usable.
func IsAvailable() bool {
	if err := loadWebView2Loader(); err != nil {
		return false
	}
	proc := getBrowserVersionProc()
	if proc == nil {
		return false
	}
	var version *uint16
	r, _, _ := syscall.SyscallN(proc.Addr(), uintptr(unsafe.Pointer(&version)))
	return r == 0 && version != nil
}

func getBrowserVersionProc() *windows.LazyProc {
	if procGetAvailableBrowserVersionString == nil {
		if modWebView2Loader == nil {
			return nil
		}
		procGetAvailableBrowserVersionString = modWebView2Loader.NewProc("GetAvailableCoreWebView2BrowserVersionString")
	}
	return procGetAvailableBrowserVersionString
}

func GetAvailableVersion() (string, error) {
	if err := loadWebView2Loader(); err != nil {
		return "", fmt.Errorf("WebView2Loader not found: %w", err)
	}
	proc := getBrowserVersionProc()
	if proc == nil {
		return "", fmt.Errorf("WebView2Loader proc missing")
	}
	var version *uint16
	r, _, _ := syscall.SyscallN(proc.Addr(), uintptr(unsafe.Pointer(&version)))
	if r != 0 {
		return "", windows.Errno(r)
	}
	if version == nil {
		return "", fmt.Errorf("no WebView2 runtime")
	}
	return windows.UTF16PtrToString(version), nil
}

// ============================================================
// COM IUnknown base
// ============================================================

type iUnknownVtbl struct {
	QueryInterface uintptr
	AddRef         uintptr
	Release        uintptr
}

var iidIUnknown = windows.GUID{
	Data1: 0x00000000, Data2: 0x0000, Data3: 0x0000,
	Data4: [8]byte{0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46},
}

type comRefCounted struct {
	mu       sync.Mutex
	refCount int32
}

func (c *comRefCounted) addRef() uint32 {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.refCount++
	return uint32(c.refCount)
}

func (c *comRefCounted) release() uint32 {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.refCount--
	return uint32(c.refCount)
}

// ============================================================
// ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler
// ============================================================

var iidEnvCompletedHandler = windows.GUID{
	Data1: 0x8B2C6C5E, Data2: 0x8A1E, Data3: 0x4A1C,
	Data4: [8]byte{0x8D, 0x3C, 0x2C, 0x4E, 0x5E, 0x1E, 0x4E, 0x2E},
}

type envCompletedHandlerVtbl struct {
	iUnknownVtbl
	Invoke uintptr
}

type envCompletedHandler struct {
	lpVtbl   *envCompletedHandlerVtbl
	comRefCounted
	callback func(err error, env *ICoreWebView2Environment)
}

func newEnvCompletedHandler(cb func(err error, env *ICoreWebView2Environment)) *envCompletedHandler {
	h := &envCompletedHandler{callback: cb}
	h.refCount = 1
	h.lpVtbl = &envCompletedHandlerVtbl{}
	ptr := uintptr(unsafe.Pointer(h))
	h.lpVtbl.QueryInterface = syscall.NewCallback(func(this uintptr, riid uintptr, ppv uintptr) uintptr {
		return envHandlerQI(ptr, riid, ppv)
	})
	h.lpVtbl.AddRef = syscall.NewCallback(func(this uintptr) uintptr {
		return envHandlerAddRef(ptr)
	})
	h.lpVtbl.Release = syscall.NewCallback(func(this uintptr) uintptr {
		return envHandlerRelease(ptr)
	})
	h.lpVtbl.Invoke = syscall.NewCallback(func(this uintptr, result uintptr, env uintptr) uintptr {
		return envHandlerInvoke(ptr, result, env)
	})
	keepHandler(h)
	return h
}

func envHandlerQI(thisPtr uintptr, riidPtr uintptr, ppvPtr uintptr) uintptr {
	h := (*envCompletedHandler)(unsafe.Pointer(thisPtr))
	riid := (*windows.GUID)(unsafe.Pointer(riidPtr))
	ppv := (**unsafe.Pointer)(unsafe.Pointer(ppvPtr))
	if *riid == iidEnvCompletedHandler || *riid == iidIUnknown {
		h.addRef()
		*ppv = (*unsafe.Pointer)(unsafe.Pointer(h))
		return 0
	}
	*ppv = nil
	return 0x80004002
}

func envHandlerAddRef(thisPtr uintptr) uintptr { return uintptr((*envCompletedHandler)(unsafe.Pointer(thisPtr)).addRef()) }
func envHandlerRelease(thisPtr uintptr) uintptr { return uintptr((*envCompletedHandler)(unsafe.Pointer(thisPtr)).release()) }

func envHandlerInvoke(thisPtr uintptr, result uintptr, envPtr uintptr) uintptr {
	h := (*envCompletedHandler)(unsafe.Pointer(thisPtr))
	if h.callback == nil { return 0 }
	var env *ICoreWebView2Environment
	if result == 0 && envPtr != 0 { env = (*ICoreWebView2Environment)(unsafe.Pointer(envPtr)) }
	var err error
	if result != 0 { err = windows.Errno(result) }
	h.callback(err, env)
	releaseHandler(h)
	return 0
}

// ============================================================
// ICoreWebView2CreateCoreWebView2ControllerCompletedHandler
// ============================================================

var iidControllerCompletedHandler = windows.GUID{
	Data1: 0x6C7A3F2E, Data2: 0x8B2C, Data3: 0x4E1A,
	Data4: [8]byte{0x9D, 0x1E, 0x3F, 0x2A, 0x5C, 0x8E, 0x1B, 0x4D},
}

type controllerCompletedHandlerVtbl struct {
	iUnknownVtbl
	Invoke uintptr
}

type controllerCompletedHandler struct {
	lpVtbl   *controllerCompletedHandlerVtbl
	comRefCounted
	callback func(err error, controller *ICoreWebView2Controller)
}

func newControllerCompletedHandler(cb func(err error, controller *ICoreWebView2Controller)) *controllerCompletedHandler {
	h := &controllerCompletedHandler{callback: cb}
	h.refCount = 1
	h.lpVtbl = &controllerCompletedHandlerVtbl{}
	h.lpVtbl.QueryInterface = syscall.NewCallback(func(this uintptr, riid uintptr, ppv uintptr) uintptr {
		riid2 := (*windows.GUID)(unsafe.Pointer(riid))
		ppv2 := (**unsafe.Pointer)(unsafe.Pointer(ppv))
		if *riid2 == iidControllerCompletedHandler || *riid2 == iidIUnknown {
			(*controllerCompletedHandler)(unsafe.Pointer(this)).addRef()
			*ppv2 = (*unsafe.Pointer)(unsafe.Pointer(this))
			return 0
		}
		*ppv2 = nil
		return 0x80004002
	})
	h.lpVtbl.AddRef = syscall.NewCallback(func(this uintptr) uintptr {
		return uintptr((*controllerCompletedHandler)(unsafe.Pointer(this)).addRef())
	})
	h.lpVtbl.Release = syscall.NewCallback(func(this uintptr) uintptr {
		return uintptr((*controllerCompletedHandler)(unsafe.Pointer(this)).release())
	})
	h.lpVtbl.Invoke = syscall.NewCallback(func(this uintptr, result uintptr, ctrl uintptr) uintptr {
		h2 := (*controllerCompletedHandler)(unsafe.Pointer(this))
		if h2.callback == nil { return 0 }
		var c *ICoreWebView2Controller
		if result == 0 && ctrl != 0 { c = (*ICoreWebView2Controller)(unsafe.Pointer(ctrl)) }
		var err error
		if result != 0 { err = windows.Errno(result) }
		h2.callback(err, c)
		releaseHandler(h2)
		return 0
	})
	keepHandler(h)
	return h
}

// ============================================================
// COM Interface wrappers
// ============================================================

// ICoreWebView2Environment
type icv2EnvVtbl struct {
	iUnknownVtbl
	CreateCoreWebView2Controller            uintptr
	CreateWebResourceResponse               uintptr
	get_BrowserVersionString                uintptr
	AddNewBrowserVersionAvailable           uintptr
	RemoveNewBrowserVersionAvailable        uintptr
	CreateWebResourceRequest                uintptr
	GetProcessInfos                         uintptr
	GetProcessExtendedInfos                 uintptr
	CreateContextMenuItem                   uintptr
	CreateSharedBuffer                      uintptr
	GetFailureReportFolderPath              uintptr
	GetAutomationProvider                   uintptr
	GetProcessExtendedInfosWithPrerequisite uintptr
}

type ICoreWebView2Environment struct{ lpVtbl *icv2EnvVtbl }

func (e *ICoreWebView2Environment) CreateCoreWebView2Controller(parentHwnd windows.HWND, handler *controllerCompletedHandler) error {
	r, _, _ := syscall.SyscallN(e.lpVtbl.CreateCoreWebView2Controller, uintptr(unsafe.Pointer(e)), uintptr(parentHwnd), uintptr(unsafe.Pointer(handler)))
	if r != 0 { return windows.Errno(r) }
	return nil
}

// ICoreWebView2Controller
type icv2CtrlVtbl struct {
	iUnknownVtbl
	_                                  [41]uintptr // skip methods 3-43
	get_CoreWebView2                   uintptr // 44
	_                                  [29]uintptr // skip methods 45-73
	Close                              uintptr // 74 ish
}

// Actually let me use the correct method indices
// The vtable indices for ICoreWebView2Controller are:
// 0-2: IUnknown
// 3: get_IsVisible
// 4: put_IsVisible
// 5: get_Bounds
// 6: put_Bounds
// ...
// The get_CoreWebView2 method is at index 25 (after counting IUnknown + 22 methods before it)

type IcV2CtrlFullVtbl struct {
	iUnknownVtbl
	get_IsVisible                    uintptr
	put_IsVisible                    uintptr
	get_Bounds                       uintptr
	put_Bounds                       uintptr
	get_ZoomFactor                   uintptr
	put_ZoomFactor                   uintptr
	add_ZoomFactorChanged            uintptr
	remove_ZoomFactorChanged         uintptr
	SetBoundsAndZoomFactor           uintptr
	MoveFocus                        uintptr
	add_MoveFocusRequested           uintptr
	remove_MoveFocusRequested        uintptr
	add_GotFocus                     uintptr
	remove_GotFocus                  uintptr
	add_LostFocus                    uintptr
	remove_LostFocus                 uintptr
	add_AcceleratorKeyPressed        uintptr
	remove_AcceleratorKeyPressed     uintptr
	get_ParentWindow                 uintptr
	put_ParentWindow                 uintptr
	NotifyParentWindowPositionChanged uintptr
	Close                            uintptr
	get_CoreWebView2                 uintptr
}

type ICoreWebView2Controller struct{ lpVtbl *IcV2CtrlFullVtbl }

func (c *ICoreWebView2Controller) put_IsVisible(visible bool) error {
	var v uintptr
	if visible { v = 1 }
	r, _, _ := syscall.SyscallN(c.lpVtbl.put_IsVisible, uintptr(unsafe.Pointer(c)), v)
	if r != 0 { return windows.Errno(r) }
	return nil
}

func (c *ICoreWebView2Controller) put_Bounds(left, top, right, bottom int32) error {
	type tagRECT struct{ Left, Top, Right, Bottom int32 }
	r, _, _ := syscall.SyscallN(c.lpVtbl.put_Bounds, uintptr(unsafe.Pointer(c)), uintptr(unsafe.Pointer(&tagRECT{left, top, right, bottom})))
	if r != 0 { return windows.Errno(r) }
	return nil
}

func (c *ICoreWebView2Controller) get_CoreWebView2() (*ICoreWebView2, error) {
	var wv *ICoreWebView2
	r, _, _ := syscall.SyscallN(c.lpVtbl.get_CoreWebView2, uintptr(unsafe.Pointer(c)), uintptr(unsafe.Pointer(&wv)))
	if r != 0 { return nil, windows.Errno(r) }
	return wv, nil
}

func (c *ICoreWebView2Controller) Close() error {
	r, _, _ := syscall.SyscallN(c.lpVtbl.Close, uintptr(unsafe.Pointer(c)))
	if r != 0 { return windows.Errno(r) }
	return nil
}

func (c *ICoreWebView2Controller) AddRef() uint32 {
	r, _, _ := syscall.SyscallN(c.lpVtbl.AddRef, uintptr(unsafe.Pointer(c)))
	return uint32(r)
}

func (c *ICoreWebView2Controller) Release() uint32 {
	r, _, _ := syscall.SyscallN(c.lpVtbl.Release, uintptr(unsafe.Pointer(c)))
	return uint32(r)
}

func (c *ICoreWebView2Controller) NotifyParentWindowPositionChanged() error {
	r, _, _ := syscall.SyscallN(c.lpVtbl.NotifyParentWindowPositionChanged, uintptr(unsafe.Pointer(c)))
	if r != 0 { return windows.Errno(r) }
	return nil
}

func (c *ICoreWebView2Controller) get_ParentWindow() (windows.HWND, error) {
	var hwnd windows.HWND
	r, _, _ := syscall.SyscallN(c.lpVtbl.get_ParentWindow, uintptr(unsafe.Pointer(c)), uintptr(unsafe.Pointer(&hwnd)))
	if r != 0 { return 0, windows.Errno(r) }
	return hwnd, nil
}

// ICoreWebView2
type icv2Vtbl struct {
	iUnknownVtbl
	get_Settings                uintptr
	get_Source                  uintptr
	Navigate                    uintptr
	NavigateToString            uintptr
	add_NavigationStarting      uintptr
	remove_NavigationStarting   uintptr
	add_ContentLoading          uintptr
	remove_ContentLoading       uintptr
	add_SourceChanged           uintptr
	remove_SourceChanged        uintptr
	add_HistoryChanged          uintptr
	remove_HistoryChanged       uintptr
	add_NavigationCompleted     uintptr
	remove_NavigationCompleted  uintptr
	_                           [14]uintptr // skip methods 17-30
	Reload                      uintptr     // 31 (verified from WebView2.h)
}

type ICoreWebView2 struct{ lpVtbl *icv2Vtbl }

func (w *ICoreWebView2) Navigates(url string) error {
	u16, err := windows.UTF16PtrFromString(url)
	if err != nil { return err }
	r, _, _ := syscall.SyscallN(w.lpVtbl.Navigate, uintptr(unsafe.Pointer(w)), uintptr(unsafe.Pointer(u16)))
	if r != 0 { return windows.Errno(r) }
	return nil
}

// Reload reloads the current page. ICoreWebView2::Reload - vtable slot 28.
func (w *ICoreWebView2) Reload() error {
	r, _, _ := syscall.SyscallN(w.lpVtbl.Reload, uintptr(unsafe.Pointer(w)))
	if r != 0 { return windows.Errno(r) }
	return nil
}

func (w *ICoreWebView2) AddRef() uint32 {
	r, _, _ := syscall.SyscallN(w.lpVtbl.AddRef, uintptr(unsafe.Pointer(w)))
	return uint32(r)
}

func (w *ICoreWebView2) Release() uint32 {
	r, _, _ := syscall.SyscallN(w.lpVtbl.Release, uintptr(unsafe.Pointer(w)))
	return uint32(r)
}

func (w *ICoreWebView2) get_Settings() (*ICoreWebView2Settings, error) {
	var s *ICoreWebView2Settings
	r, _, _ := syscall.SyscallN(w.lpVtbl.get_Settings, uintptr(unsafe.Pointer(w)), uintptr(unsafe.Pointer(&s)))
	if r != 0 { return nil, windows.Errno(r) }
	return s, nil
}

// ICoreWebView2Settings
type icv2SettingsVtbl struct {
	iUnknownVtbl
	_                                [10]uintptr // skip methods 3-12
	get_AreDefaultContextMenusEnabled uintptr
	put_AreDefaultContextMenusEnabled uintptr
	get_AreHostObjectsAllowed        uintptr
	put_AreHostObjectsAllowed        uintptr
	get_IsZoomControlEnabled         uintptr
	put_IsZoomControlEnabled         uintptr
	get_IsBuiltInErrorPageEnabled    uintptr
	put_IsBuiltInErrorPageEnabled    uintptr
}

type ICoreWebView2Settings struct{ lpVtbl *icv2SettingsVtbl }

func (s *ICoreWebView2Settings) put_AreDefaultContextMenusEnabled(enabled bool) error {
	var v uintptr
	if enabled { v = 1 }
	r, _, _ := syscall.SyscallN(s.lpVtbl.put_AreDefaultContextMenusEnabled, uintptr(unsafe.Pointer(s)), v)
	if r != 0 { return windows.Errno(r) }
	return nil
}

func (s *ICoreWebView2Settings) put_AreDevToolsEnabled(enabled bool) error {
	var v uintptr
	if enabled { v = 1 }
	r, _, _ := syscall.SyscallN(s.lpVtbl.put_IsZoomControlEnabled, uintptr(unsafe.Pointer(s)), v)
	if r != 0 { return windows.Errno(r) }
	return nil
}

func (s *ICoreWebView2Settings) put_IsStatusBarEnabled(enabled bool) error {
	var v uintptr
	if enabled { v = 1 }
	r, _, _ := syscall.SyscallN(s.lpVtbl.put_IsBuiltInErrorPageEnabled, uintptr(unsafe.Pointer(s)), v)
	if r != 0 { return windows.Errno(r) }
	return nil
}

func (s *ICoreWebView2Settings) AddRef() uint32 {
	r, _, _ := syscall.SyscallN(s.lpVtbl.AddRef, uintptr(unsafe.Pointer(s)))
	return uint32(r)
}

func (s *ICoreWebView2Settings) Release() uint32 {
	r, _, _ := syscall.SyscallN(s.lpVtbl.Release, uintptr(unsafe.Pointer(s)))
	return uint32(r)
}

// ============================================================
// High-level WebView wrapper
// ============================================================

type WebView struct {
	hwnd       win32.HWND
	controller *ICoreWebView2Controller
	webView    *ICoreWebView2
	settings   *ICoreWebView2Settings
	ready      chan struct{}
	readyErr   error

	// opCh dispatches controller operations to the window thread
	// (WebView2 controller methods must run on the thread that created the controller).
	opCh chan func() error
}

// registerHostClassOnce ensures the host window class is registered only once.
var registerHostClassOnce sync.Once

func CreateWebView(parentHwnd win32.HWND, url string, x, y, width, height int32) (*WebView, error) {
	wv := &WebView{ready: make(chan struct{}), opCh: make(chan func() error, 32)}
	created := make(chan error, 1)

	go func() {
		// Win32 windows + their message pumps must live on the same OS thread.
		runtime.LockOSThread()
		defer runtime.UnlockOSThread()

		comOwned := ensureCom()
		_ = comOwned

		// Register host window class once per process
		registerHostClassOnce.Do(func() {
			className, err := windows.UTF16PtrFromString("CountdownWebViewHost")
			if err != nil {
				return
			}
			hInst, err := win32.GetModuleHandle()
			if err != nil {
				return
			}
			wc := win32.WNDCLASSEXW{
				Style:         win32.CS_HREDRAW | win32.CS_VREDRAW,
				LpfnWndProc:   windows.NewCallback(hostWndProc),
				HInstance:     hInst,
				HbrBackground: win32.GetStockObject(win32.BLACK_BRUSH),
				LpszClassName: className,
			}
			wc.Size = uint32(unsafe.Sizeof(wc))
			_, _ = win32.RegisterClassEx(&wc)
		})

		className, _ := windows.UTF16PtrFromString("CountdownWebViewHost")
		hInst, _ := win32.GetModuleHandle()

		style := uint32(win32.WS_CHILD | win32.WS_VISIBLE)
		if parentHwnd == 0 {
			style = uint32(win32.WS_OVERLAPPEDWINDOW | win32.WS_VISIBLE)
		}

		hwnd, err := win32.CreateWindowEx(
			win32.WS_EX_NOACTIVATE,
			className,
			windows.StringToUTF16Ptr("CountdownDesktop"),
			style, x, y, width, height,
			parentHwnd, 0, hInst, nil,
		)
		if err != nil {
			created <- fmt.Errorf("CreateWindowEx: %w", err)
			return
		}
		wv.hwnd = hwnd

		// Kick off environment + controller creation (async callbacks)
		startWebView2(wv, url)

		created <- nil

		// Message pump - required by WebView2 initialization.
		// GetMessage(0) retrieves messages for ALL windows of this thread;
		// filtering by hwnd would drop messages WebView2 needs to initialize.
		// Controller operations are dispatched here (same thread as creation).
		var msg win32.MSG
		for {
			// Non-blocking drain of pending controller ops
			for {
				select {
				case op := <-wv.opCh:
					if op != nil {
						_ = op()
					}
					continue
				default:
				}
				break
			}
			ret := win32.GetMessage(&msg, 0, 0, 0)
			if ret == 0 || ret == -1 {
				break
			}
			win32.TranslateMessage(&msg)
			win32.DispatchMessage(&msg)
		}
		// Drain remaining ops after loop ends
		for {
			select {
			case op := <-wv.opCh:
				if op != nil {
					_ = op()
				}
			default:
				return
			}
		}
	}()

	if err := <-created; err != nil {
		wv.Close()
		return nil, err
	}
	return wv, nil
}

// hostWndProc is the window procedure for WebView host windows.
func hostWndProc(hwnd win32.HWND, msg uint32, wparam, lparam uintptr) uintptr {
	switch msg {
	case win32.WM_DESTROY:
		// Each WebView runs its own thread + message pump; quitting the
		// thread's message queue is safe here.
		win32.PostQuitMessage(0)
		return 0
	case win32.WM_SIZE:
		// The WebView2 controller resizes its child window automatically;
		// notify it about the size change.
		win32.DefWindowProc(hwnd, msg, win32.WPARAM(wparam), win32.LPARAM(lparam))
		return 0
	}
	return win32.DefWindowProc(hwnd, msg, win32.WPARAM(wparam), win32.LPARAM(lparam))
}

// startWebView2 begins async WebView2 initialization. Callbacks fire on
// WebView2 worker threads; ready is closed when fully initialized.
func startWebView2(wv *WebView, url string) {
	envHandler := newEnvCompletedHandler(func(err error, env *ICoreWebView2Environment) {
		if err != nil {
			wv.readyErr = fmt.Errorf("create env: %w", err)
			close(wv.ready)
			return
		}
		ctrlHandler := newControllerCompletedHandler(func(err error, controller *ICoreWebView2Controller) {
			if err != nil {
				wv.readyErr = fmt.Errorf("create controller: %w", err)
				close(wv.ready)
				return
			}
			wv.controller = controller
			controller.AddRef() // hold our own reference

			// ---- Thread-bound init: run on the controller creation thread ----
			var cr win32.RECT
			win32.GetClientRect(wv.hwnd, &cr)
			if err := controller.put_Bounds(cr.Left, cr.Top, cr.Right, cr.Bottom); err != nil {
			} else {
			}
			if err := controller.put_IsVisible(true); err != nil {
			} else {
			}
			if err := controller.NotifyParentWindowPositionChanged(); err != nil {
			} else {
			}
			// ---------------------------------------------------------------

			webView, err := controller.get_CoreWebView2()
			if err != nil {
				wv.readyErr = fmt.Errorf("get CoreWebView2: %w", err)
				close(wv.ready)
				return
			}
			wv.webView = webView
			webView.AddRef() // hold our own reference
			if settings, err := webView.get_Settings(); err == nil {
				wv.settings = settings
				settings.AddRef()
				settings.put_AreDefaultContextMenusEnabled(false)
			}
			if err := webView.Navigates(url); err != nil {
				wv.readyErr = fmt.Errorf("navigate: %w", err)
				close(wv.ready)
				return
			}
			close(wv.ready)
		})
		err = env.CreateCoreWebView2Controller(windows.HWND(wv.hwnd), ctrlHandler)
		if err != nil {
			wv.readyErr = fmt.Errorf("CreateCoreWebView2Controller: %w", err)
			close(wv.ready)
		}
	})

	if err := loadWebView2Loader(); err != nil {
		wv.readyErr = err
		close(wv.ready)
		return
	}
	if procCreateCoreWebView2Environment == nil {
		procCreateCoreWebView2Environment = modWebView2Loader.NewProc("CreateCoreWebView2EnvironmentWithOptions")
	}
	r, _, _ := syscall.SyscallN(procCreateCoreWebView2Environment.Addr(), 0, 0, 0, uintptr(unsafe.Pointer(envHandler)))
	if r != 0 {
		wv.readyErr = fmt.Errorf("CreateCoreWebView2EnvironmentWithOptions: %w", windows.Errno(r))
		close(wv.ready)
	}
}

func (wv *WebView) WaitReady() error {
	select {
	case <-wv.ready:
		return wv.readyErr
	case <-time.After(30 * time.Second):
		return fmt.Errorf("WebView2 init timeout (30s)")
	}
}
func (wv *WebView) HWND() win32.HWND { return wv.hwnd }

func (wv *WebView) Navigate(url string) error {
	if wv.webView == nil { return fmt.Errorf("webview not initialized") }
	errCh := make(chan error, 1)
	wv.opCh <- func() error {
		err := wv.webView.Navigates(url)
		errCh <- err
		return err
	}
	return <-errCh
}

func (wv *WebView) Resize(x, y, width, height int32) error {
	if wv.controller == nil { return fmt.Errorf("controller not initialized") }
	errCh := make(chan error, 1)
	wv.opCh <- func() error {
		err := wv.controller.put_Bounds(x, y, x+width, y+height)
		errCh <- err
		return err
	}
	return <-errCh
}

func (wv *WebView) Show() error {
	if wv.controller == nil { return fmt.Errorf("controller not initialized") }
	errCh := make(chan error, 1)
	wv.opCh <- func() error {
		err := wv.controller.put_IsVisible(true)
		errCh <- err
		return err
	}
	return <-errCh
}

func (wv *WebView) Hide() error {
	if wv.controller == nil { return fmt.Errorf("controller not initialized") }
	errCh := make(chan error, 1)
	wv.opCh <- func() error {
		err := wv.controller.put_IsVisible(false)
		errCh <- err
		return err
	}
	return <-errCh
}

// Reload reloads the current page (forces re-render after reparenting).
// Must run on the thread that created the WebView2 objects.
func (wv *WebView) Reload() error {
	if wv.webView == nil { return fmt.Errorf("webview not initialized") }
	errCh := make(chan error, 1)
	wv.opCh <- func() error {
		err := wv.webView.Reload()
		errCh <- err
		return err
	}
	return <-errCh
}

// Exec runs fn on the window thread (where the HWND was created).
// Required for SetParent/SetWindowPos/SetWindowLong etc - these silently fail
// when called cross-thread.
func (wv *WebView) Exec(fn func()) {
	if fn == nil {
		return
	}
	done := make(chan struct{})
	wv.opCh <- func() error {
		fn()
		close(done)
		return nil
	}
	<-done
}

// NotifyParentWindowPositionChanged informs WebView2 the host moved/resized.
func (wv *WebView) NotifyParentWindowPositionChanged() error {
	if wv.controller == nil { return fmt.Errorf("controller not initialized") }
	errCh := make(chan error, 1)
	wv.opCh <- func() error {
		err := wv.controller.NotifyParentWindowPositionChanged()
		errCh <- err
		return err
	}
	return <-errCh
}

func (wv *WebView) Close() {
	if wv.controller != nil {
		// controller.Close() must run on the creation thread; dispatch it.
		done := make(chan struct{})
		select {
		case wv.opCh <- func() error {
			_ = wv.controller.Close()
			wv.controller.Release()
			close(done)
			return nil
		}:
			<-done
		default:
			// opCh full or no pump running - release directly
			wv.controller.Release()
		}
		wv.controller = nil
	}
	if wv.webView != nil {
		wv.webView.Release()
		wv.webView = nil
	}
	if wv.settings != nil {
		wv.settings.Release()
		wv.settings = nil
	}
	if wv.hwnd != 0 {
		win32.DestroyWindow(wv.hwnd)
		wv.hwnd = 0
	}
}

func RunMessageLoop() {
	var msg win32.MSG
	for {
		ret := win32.GetMessage(&msg, 0, 0, 0)
		if ret == 0 || ret == -1 { break }
		win32.TranslateMessage(&msg)
		win32.DispatchMessage(&msg)
	}
}
