package screensaver

import (
	"fmt"
	"sync"
	"time"
	"unsafe"

	"github.com/tgcz2011/countdown-desktop/internal/config"
	"github.com/tgcz2011/countdown-desktop/internal/webview"
	"github.com/tgcz2011/countdown-desktop/internal/win32"
)

type Engine struct {
	mu      sync.Mutex
	webView *webview.WebView
	cfg     *config.Config
	running bool
	stopCh  chan struct{}
}

func New(cfg *config.Config) *Engine {
	return &Engine{cfg: cfg}
}

func getLastInputTime() uint32 {
	var lii win32.LASTINPUTINFO
	lii.CbSize = uint32(unsafe.Sizeof(lii))
	win32.GetLastInputInfo(&lii)
	return lii.DwTime
}

func (e *Engine) Start() error {
	e.mu.Lock()
	defer e.mu.Unlock()

	if e.running { return nil }
	if !e.cfg.ScreensaverEnabled && e.cfg.ScreensaverURL == "" { return nil }

	url := e.cfg.ScreensaverURL
	if url == "" { url = "https://zztool.free.nf/countdown" }

	screenWidth := int32(win32.GetSystemMetrics(win32.SM_CXSCREEN))
	screenHeight := int32(win32.GetSystemMetrics(win32.SM_CYSCREEN))

	wv, err := webview.CreateWebView(0, url, 0, 0, screenWidth, screenHeight)
	if err != nil { return fmt.Errorf("create screensaver WebView: %w", err) }
	if err := wv.WaitReady(); err != nil { wv.Close(); return fmt.Errorf("screensaver WebView ready: %w", err) }

	hwnd := wv.HWND()
	win32.SetWindowPos(hwnd, win32.HWND_TOPMOST_HWND, 0, 0, screenWidth, screenHeight,
		win32.SWP_SHOWWINDOW|win32.SWP_NOACTIVATE)

	win32.ShowCursor(false)

	e.webView = wv
	e.running = true
	e.stopCh = make(chan struct{})
	go e.monitorInput()
	fmt.Println("Screensaver started")
	return nil
}

func (e *Engine) monitorInput() {
	time.Sleep(500 * time.Millisecond)
	e.mu.Lock()
	lastInput := getLastInputTime()
	e.mu.Unlock()

	for {
		select {
		case <-e.stopCh:
			return
		default:
		}
		time.Sleep(100 * time.Millisecond)

		e.mu.Lock()
		if !e.running { e.mu.Unlock(); return }
		e.mu.Unlock()

		currentInput := getLastInputTime()
		if currentInput != lastInput { e.Stop(); return }
		lastInput = currentInput

		for vk := int32(0x01); vk <= 0xFE; vk++ {
			if uint16(win32.GetAsyncKeyState(vk))&0x8000 != 0 { e.Stop(); return }
		}
		for vk := int32(0x01); vk <= 0x06; vk++ {
			if uint16(win32.GetAsyncKeyState(vk))&0x8000 != 0 { e.Stop(); return }
		}
	}
}

func (e *Engine) Stop() {
	e.mu.Lock()
	defer e.mu.Unlock()
	if !e.running { return }
	if e.stopCh != nil { close(e.stopCh); e.stopCh = nil }
	if e.webView != nil { e.webView.Close(); e.webView = nil }
	win32.ShowCursor(true)
	e.running = false
	fmt.Println("Screensaver stopped")
}

func (e *Engine) IsRunning() bool {
	e.mu.Lock()
	defer e.mu.Unlock()
	return e.running
}

func (e *Engine) UpdateURL(url string) error {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.cfg.ScreensaverURL = url
	if e.webView != nil { return e.webView.Navigate(url) }
	return nil
}

func IdleTime() int {
	lastInput := getLastInputTime()
	tickCount := win32.GetTickCount()
	if tickCount < lastInput { return 0 }
	return int((tickCount - lastInput) / 1000)
}

func (e *Engine) StartIdleMonitor(cfg *config.Config) {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()
	for range ticker.C {
		e.mu.Lock()
		running := e.running
		e.mu.Unlock()
		if running { continue }
		if !cfg.ScreensaverEnabled { continue }
		if IdleTime() >= cfg.ScreensaverTime {
			fmt.Printf("Idle for %ds, starting screensaver\n", IdleTime())
			e.Start()
		}
	}
}
