package wallpaper

import (
	"fmt"
	"sync"
	"syscall"

	"golang.org/x/sys/windows"

	"github.com/tgcz2011/countdown-desktop/internal/config"
	"github.com/tgcz2011/countdown-desktop/internal/logutil"
	"github.com/tgcz2011/countdown-desktop/internal/webview"
	"github.com/tgcz2011/countdown-desktop/internal/win32"
)

// WS_EX_NOREDIRECTIONBITMAP - Progman has this style on Win11 "raised desktop".
const wsExNoRedirectionBitmap = 0x00200000

type Engine struct {
	mu         sync.Mutex
	webView    *webview.WebView
	cfg        *config.Config
	running    bool
	host       *DesktopHost
	parentHwnd win32.HWND
}

// DesktopHost holds the desktop window structure for wallpaper embedding.
type DesktopHost struct {
	progman   win32.HWND // Program Manager
	defView   win32.HWND // SHELLDLL_DefView (icons layer)
	workerW   win32.HWND // WorkerW (wallpaper layer) - Progman child on Win11 raised desktop
	raised    bool       // Win11 raised desktop (Progman has WS_EX_NOREDIRECTIONBITMAP)
}

func New(cfg *config.Config) *Engine {
	return &Engine{cfg: cfg}
}

// findDesktopHost locates the desktop structure, mirroring Lively's SetupDesktopLayer.
func findDesktopHost() (*DesktopHost, error) {
	progman, _ := windows.UTF16PtrFromString("Progman")
	hProgman := win32.FindWindow(progman, nil)
	if hProgman == 0 {
		return nil, fmt.Errorf("Progman not found")
	}

	dh := &DesktopHost{progman: hProgman}

	// Detect Win11 raised desktop (layered ShellView)
	exStyle := win32.GetWindowLongPtr(hProgman, win32.GWL_EXSTYLE)
	dh.raised = (exStyle & wsExNoRedirectionBitmap) != 0
	logutil.Log("findDesktopHost: Progman=%x raisedDesktop=%v", hProgman, dh.raised)

	// Send 0x052C with wParam=0xD lParam=0x1 to spawn the wallpaper WorkerW.
	// (plain 0,0 does not create the raised-desktop WorkerW layer)
	win32.SendMessageTimeout(hProgman, 0x052C, 0xD, 0x1, 0, 1000)
	win32.SendMessageTimeout(hProgman, 0x052C, 0xD, 0x1, 0, 1000)

	// Locate SHELLDLL_DefView: under Progman (Win11) or under a top-level WorkerW (Win10)
	defViewClass, _ := windows.UTF16PtrFromString("SHELLDLL_DefView")

	// 1. Direct child of Progman
	defView := win32.FindWindowEx(hProgman, 0, defViewClass, nil)
	if defView != 0 {
		dh.defView = defView
		logutil.Log("findDesktopHost: DefView=%x under Progman", defView)
	} else {
		// 2. Under a top-level WorkerW (classic layout)
		cb := syscall.NewCallback(func(hwnd uintptr, lparam uintptr) uintptr {
			h := win32.HWND(hwnd)
			buf := make([]uint16, 256)
			n := win32.GetClassName(h, buf)
			if n <= 0 {
				return 1
			}
			if windows.UTF16ToString(buf[:n]) == "WorkerW" {
				dv := win32.FindWindowEx(h, 0, defViewClass, nil)
				if dv != 0 {
					dh.defView = dv
					dh.workerW = h
					logutil.Log("findDesktopHost: DefView=%x under WorkerW=%x", dv, h)
					return 0
				}
			}
			return 1
		})
		win32.EnumWindows(cb, 0)
	}

	if dh.defView == 0 {
		return nil, fmt.Errorf("SHELLDLL_DefView not found (desktop icons layer missing?)")
	}

	if dh.raised {
		// Win11: find the wallpaper WorkerW child of Progman (created by 0x052C 0xD/0x1)
		workerWClass, _ := windows.UTF16PtrFromString("WorkerW")
		dh.workerW = win32.FindWindowEx(hProgman, 0, workerWClass, nil)
		logutil.Log("findDesktopHost: raised mode, Progman child WorkerW=%x", dh.workerW)
	}

	return dh, nil
}

func (e *Engine) Start() error {
	e.mu.Lock()
	defer e.mu.Unlock()

	if e.running {
		return nil
	}
	if !e.cfg.WallpaperEnabled {
		return nil
	}

	host, err := findDesktopHost()
	if err != nil {
		return fmt.Errorf("find desktop host: %w", err)
	}

	screenWidth := int32(win32.GetSystemMetrics(win32.SM_CXSCREEN))
	screenHeight := int32(win32.GetSystemMetrics(win32.SM_CYSCREEN))
	logutil.Log("Metrics: screen=%dx%d", screenWidth, screenHeight)

	wv, err := webview.CreateWebView(0, e.cfg.WallpaperURL, 0, 0, screenWidth, screenHeight)
	if err != nil {
		return fmt.Errorf("create WebView: %w", err)
	}
	if err := wv.WaitReady(); err != nil {
		wv.Close()
		return fmt.Errorf("WebView ready: %w", err)
	}

	if host.raised {
		// ---- Windows 11 raised desktop: layered child under Progman (Lively style) ----
		// 1. WS_CHILD style
		style := win32.GetWindowLongPtr(wv.HWND(), win32.GWL_STYLE)
		style |= uintptr(win32.WS_CHILD | win32.WS_VISIBLE)
		style &^= uintptr(win32.WS_POPUP | win32.WS_OVERLAPPEDWINDOW)
		win32.SetWindowLongPtr(wv.HWND(), win32.GWL_STYLE, style)

		// 2. WS_EX_LAYERED + SetLayeredWindowAttributes(bAlpha=0xFF)
		exStyle := win32.GetWindowLongPtr(wv.HWND(), win32.GWL_EXSTYLE)
		exStyle |= uintptr(win32.WS_EX_TOOLWINDOW | win32.WS_EX_NOACTIVATE | win32.WS_EX_LAYERED)
		exStyle &^= uintptr(win32.WS_EX_APPWINDOW)
		win32.SetWindowLongPtr(wv.HWND(), win32.GWL_EXSTYLE, exStyle)
		ok := win32.SetLayeredWindowAttributes(wv.HWND(), 0, 255, win32.LWA_ALPHA)
		logutil.Log("raised: SetLayeredWindowAttributes -> %v", ok)

		// 3+4. Reparent + Z-order on the window thread
		wv.Exec(func() {
			win32.SetParent(wv.HWND(), host.progman)
			e.parentHwnd = host.progman
			win32.SetWindowPos(wv.HWND(), host.defView, 0, 0, screenWidth, screenHeight,
				win32.SWP_NOACTIVATE)
		})

		// 5. Keep wallpaper WorkerW at bottom of Progman Z-order
		if host.workerW != 0 {
			win32.SetWindowPos(host.workerW, win32.HWND_BOTTOM_HWND, 0, 0, 0, 0,
				win32.SWP_NOMOVE|win32.SWP_NOSIZE|win32.SWP_NOACTIVATE)
			logutil.Log("raised: WorkerW pushed to bottom")
		}
	} else {
		// ---- Classic layout ----
		// EXPERIMENT: parent to Progman directly (Lively uses workerW; testing both)
		parent := host.progman
		if false && host.workerW != 0 {
			parent = host.workerW
		}
		// SetParent + SetWindowPos MUST run on the window creation thread,
		// otherwise they silently fail. Dispatch via wv.Exec.
		wv.Exec(func() {
			// SetParent does NOT modify WS_CHILD/WS_POPUP - set WS_CHILD explicitly
			style := win32.GetWindowLongPtr(wv.HWND(), win32.GWL_STYLE)
			style |= uintptr(win32.WS_CHILD | win32.WS_VISIBLE)
			style &^= uintptr(win32.WS_POPUP | win32.WS_OVERLAPPEDWINDOW)
			win32.SetWindowLongPtr(wv.HWND(), win32.GWL_STYLE, style)
			win32.SetWindowPos(wv.HWND(), 0, 0, 0, 0, 0, win32.SWP_FRAMECHANGED|win32.SWP_NOMOVE|win32.SWP_NOSIZE|win32.SWP_NOZORDER)

			oldParent := win32.SetParent(wv.HWND(), parent)
			logutil.Log("classic: SetParent -> %x (old %x)", parent, oldParent)
			e.parentHwnd = parent
			logutil.Log("verify: GetParent now = %x (expect %x)", win32.GetParent(wv.HWND()), parent)
			if err := win32.SetWindowPos(wv.HWND(), win32.HWND_BOTTOM_HWND, 0, 0, screenWidth, screenHeight,
				win32.SWP_NOACTIVATE); err != nil {
				logutil.Log("classic SetWindowPos FAILED: %v", err)
			}
		})
	}

	// Reparenting can reset WebView2 visibility/geometry; re-apply on creation thread.
	if err := wv.Resize(0, 0, screenWidth, screenHeight); err != nil {
		logutil.Log("post-reparent Resize failed: %v", err)
	}
	if err := wv.Show(); err != nil {
		logutil.Log("post-reparent Show failed: %v", err)
	}
	if err := wv.NotifyParentWindowPositionChanged(); err != nil {
		logutil.Log("post-reparent Notify failed: %v", err)
	}
	// Reparenting can freeze WebView2 rendering; reload forces a fresh render pass.
	if err := wv.Reload(); err != nil {
		logutil.Log("post-reparent Reload failed: %v", err)
	} else {
		logutil.Log("post-reparent Reload OK")
	}

	// ShowWindow can raise the window in Z-order; push it back to the bottom
	// ShowWindow can raise the window in Z-order; push it to the bottom of the parent
	wv.Exec(func() {
		if err := win32.SetWindowPos(wv.HWND(), win32.HWND_BOTTOM_HWND, 0, 0, screenWidth, screenHeight,
			win32.SWP_NOACTIVATE); err != nil {
			logutil.Log("Z-order re-assert FAILED: %v", err)
		} else {
			logutil.Log("Z-order re-asserted to bottom OK")
		}
	})

	// 6. Ensure visible
	wv.Exec(func() {
		win32.ShowWindow(wv.HWND(), win32.SW_SHOWNA)
		win32.UpdateWindow(wv.HWND())
		logutil.Log("Wallpaper host hwnd=%x visible=%v", wv.HWND(), win32.IsWindowVisible(wv.HWND()))
	})

	e.webView = wv
	e.host = host
	e.running = true
	p := host.progman
	if !host.raised && host.workerW != 0 {
		p = host.workerW
	}
	e.parentHwnd = p
	logutil.Log("Wallpaper started: hwnd=%x parent=%x defView=%x raised=%v url=%s",
		wv.HWND(), p, host.defView, host.raised, e.cfg.WallpaperURL)
	return nil
}

func (e *Engine) Stop() {
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.webView != nil {
		logutil.Log("Stop: parent still = %x (expected %x)", win32.GetParent(e.webView.HWND()), e.parentHwnd)
		e.webView.Close()
		e.webView = nil
	}
	e.host = nil
	e.running = false
	logutil.Log("Wallpaper stopped")
}

func (e *Engine) UpdateURL(url string) error {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.cfg.WallpaperURL = url
	if e.webView != nil {
		return e.webView.Navigate(url)
	}
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
	if e.webView != nil {
		e.webView.Close()
		e.webView = nil
		e.running = false
	}
	e.mu.Unlock()
	if wasRunning {
		return e.Start()
	}
	return nil
}
