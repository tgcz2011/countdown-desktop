package wallpaper

import (
	"fmt"
	"sync"
	"syscall"

	"golang.org/x/sys/windows"

	"github.com/tgcz2011/countdown-desktop/internal/config"
	"github.com/tgcz2011/countdown-desktop/internal/webview"
	"github.com/tgcz2011/countdown-desktop/internal/win32"
)

type Engine struct {
	mu      sync.Mutex
	webView *webview.WebView
	cfg     *config.Config
	running bool
}

func New(cfg *config.Config) *Engine {
	return &Engine{cfg: cfg}
}

func findWorkerW() (win32.HWND, error) {
	progman, _ := windows.UTF16PtrFromString("Progman")
	hProgman := win32.FindWindow(progman, nil)
	if hProgman == 0 {
		return 0, fmt.Errorf("Progman not found")
	}

	// Send 0x052C to spawn WorkerW
	win32.SendMessage(hProgman, 0x052C, 0, 0)

	var result win32.HWND
	workerWClass, _ := windows.UTF16PtrFromString("WorkerW")
	defViewClass, _ := windows.UTF16PtrFromString("SHELLDLL_DefView")

	callback := syscall.NewCallback(func(hwnd win32.HWND, lparam uintptr) uintptr {
		buf := make([]uint16, 256)
		win32.GetClassName(hwnd, buf)
		if windows.UTF16PtrToString(&buf[0]) == windows.UTF16PtrToString(workerWClass) {
			defView := win32.FindWindowEx(hwnd, 0, defViewClass, nil)
			if defView != 0 {
				result = hwnd
				return 0
			}
		}
		return 1
	})

	win32.EnumWindows(callback, 0)
	if result == 0 {
		return 0, fmt.Errorf("WorkerW with SHELLDLL_DefView not found")
	}
	return result, nil
}

func (e *Engine) Start() error {
	e.mu.Lock()
	defer e.mu.Unlock()

	if e.running { return nil }
	if !e.cfg.WallpaperEnabled { return nil }

	workerW, err := findWorkerW()
	if err != nil { return fmt.Errorf("find WorkerW: %w", err) }

	screenWidth := int32(win32.GetSystemMetrics(win32.SM_CXSCREEN))
	screenHeight := int32(win32.GetSystemMetrics(win32.SM_CYSCREEN))

	wv, err := webview.CreateWebView(0, e.cfg.WallpaperURL, 0, 0, screenWidth, screenHeight)
	if err != nil { return fmt.Errorf("create WebView: %w", err) }
	if err := wv.WaitReady(); err != nil { wv.Close(); return fmt.Errorf("WebView ready: %w", err) }

	// Reparent to WorkerW
	win32.SetParent(wv.HWND(), workerW)

	// Position at bottom
	win32.SetWindowPos(wv.HWND(), win32.HWND_BOTTOM_HWND, 0, 0, 0, 0,
		win32.SWP_NOSIZE|win32.SWP_NOMOVE|win32.SWP_NOACTIVATE|win32.SWP_NOSENDCHANGING)

	// Set window styles
	style := win32.GetWindowLongPtr(wv.HWND(), win32.GWL_EXSTYLE)
	style |= win32.WS_EX_TOOLWINDOW | win32.WS_EX_NOACTIVATE
	style &^= win32.WS_EX_APPWINDOW
	win32.SetWindowLongPtr(wv.HWND(), win32.GWL_EXSTYLE, style)

	e.webView = wv
	e.running = true
	fmt.Println("Wallpaper started")
	return nil
}

func (e *Engine) Stop() {
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.webView != nil { e.webView.Close(); e.webView = nil }
	e.running = false
}

func (e *Engine) UpdateURL(url string) error {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.cfg.WallpaperURL = url
	if e.webView != nil { return e.webView.Navigate(url) }
	return nil
}

func (e *Engine) IsRunning() bool {
	e.mu.Lock()
	defer e.mu.Unlock()
	return e.running
}

func (e *Engine) Refresh() error {
	e.mu.Lock()
	wasRunning := e.running
	if e.webView != nil { e.webView.Close(); e.webView = nil; e.running = false }
	e.mu.Unlock()
	if wasRunning { return e.Start() }
	return nil
}
