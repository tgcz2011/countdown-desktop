package main

import (
	"os"
	"sync"
	"time"

	"golang.org/x/sys/windows"

	"github.com/tgcz2011/countdown-desktop/internal/config"
	"github.com/tgcz2011/countdown-desktop/internal/logutil"
	"github.com/tgcz2011/countdown-desktop/internal/screensaver"
	"github.com/tgcz2011/countdown-desktop/internal/settings"
	"github.com/tgcz2011/countdown-desktop/internal/tray"
	"github.com/tgcz2011/countdown-desktop/internal/wallpaper"
	"github.com/tgcz2011/countdown-desktop/internal/webview"
	"github.com/tgcz2011/countdown-desktop/internal/win32"
	"github.com/tgcz2011/countdown-desktop/version"
)

func main() {
	// Must be before any window creation to avoid DPI virtualization
	win32.SetProcessDpiAwareness()

	_ = logutil.Init()
	defer logutil.Close()
	logutil.Log("Countdown Desktop v%s starting (args=%v)", version.Version, os.Args)

	// CLI test modes (debugging without tray interaction)
	testMode := ""
	for _, a := range os.Args[1:] {
		switch a {
		case "--test-wallpaper":
			testMode = "wallpaper"
		case "--test-screensaver":
			testMode = "screensaver"
		case "--test-settings":
			testMode = "settings"
		case "--test-standalone":
			testMode = "standalone"
		}
	}

	// Single instance check
	mutexName, _ := windows.UTF16PtrFromString("CountdownDesktop_SingleInstance")
	mutex, err := windows.CreateMutex(nil, false, mutexName)
	if err != nil || windows.GetLastError() == windows.ERROR_ALREADY_EXISTS {
		logutil.Log("Another instance is already running")
		os.Exit(0)
	}
	defer windows.CloseHandle(mutex)

	// Load config
	cfg, err := config.Load()
	if err != nil {
		logutil.Log("Failed to load config: %v", err)
		cfg = config.DefaultConfig()
	}
	logutil.Log("Config: wp=%v ss=%v timeout=%ds", cfg.WallpaperEnabled, cfg.ScreensaverEnabled, cfg.ScreensaverTime)

	wpEngine := wallpaper.New(cfg)
	ssEngine := screensaver.New(cfg)

	// Test mode: run feature directly, exit after N seconds
	if testMode != "" {
		runTestMode(testMode, cfg, wpEngine, ssEngine)
		return
	}

	actions := make(chan tray.Action, 10)
	trayIcon, err := tray.New(actions)
	if err != nil {
		logutil.Log("Failed to create tray icon: %v", err)
		os.Exit(1)
	}
	logutil.Log("Tray icon created")

	// Start wallpaper if enabled
	if cfg.WallpaperEnabled {
		if err := wpEngine.Start(); err != nil {
			logutil.Log("Failed to start wallpaper: %v", err)
		}
	}

	// Start screensaver idle monitor
	go ssEngine.StartIdleMonitor(cfg)

	var settingsWnd *settings.Window
	var settingsMu sync.Mutex

	go func() {
		for action := range actions {
			switch action {
			case tray.ActionToggleWallpaper:
				cfg.WallpaperEnabled = !cfg.WallpaperEnabled
				_ = cfg.Save()
				if cfg.WallpaperEnabled {
					if err := wpEngine.Start(); err != nil {
						logutil.Log("Start wallpaper failed: %v", err)
					}
				} else {
					wpEngine.Stop()
				}

			case tray.ActionToggleScreensaver:
				cfg.ScreensaverEnabled = !cfg.ScreensaverEnabled
				_ = cfg.Save()

			case tray.ActionOpenSettings:
				settingsMu.Lock()
				if settingsWnd != nil {
					win32.SetForegroundWindow(settingsWnd.HWND())
					settingsMu.Unlock()
					continue
				}
				settingsMu.Unlock()

				editCfg := *cfg
				w, err := settings.New(&editCfg,
					func(newCfg *config.Config) {
						*cfg = *newCfg
						_ = cfg.Save()
						if cfg.WallpaperEnabled {
							if err := wpEngine.Refresh(); err != nil {
								logutil.Log("Refresh wallpaper failed: %v", err)
							}
						} else {
							wpEngine.Stop()
						}
					},
					func() {
						logutil.Log("Test wallpaper from settings")
						if err := wpEngine.Refresh(); err != nil {
							logutil.Log("Test wallpaper failed: %v", err)
						}
					},
					func() {
						logutil.Log("Test screensaver from settings")
						if err := ssEngine.Start(); err != nil {
							logutil.Log("Test screensaver failed: %v", err)
						}
					},
				)
				if err != nil {
					logutil.Log("Failed to create settings window: %v", err)
					continue
				}

				settingsMu.Lock()
				settingsWnd = w
				settingsMu.Unlock()

				go func() {
					webview.RunMessageLoop()
					settingsMu.Lock()
					settingsWnd = nil
					settingsMu.Unlock()
				}()

			case tray.ActionExit:
				logutil.Log("Exit requested")
				wpEngine.Stop()
				ssEngine.Stop()
				trayIcon.Remove()
				os.Exit(0)
			}
		}
	}()

	logutil.Log("Entering main message loop")
	webview.RunMessageLoop()
	logutil.Log("Message loop exited")
}

// runTestMode runs a single feature in isolation for automated testing.
func runTestMode(mode string, cfg *config.Config, wpEngine *wallpaper.Engine, ssEngine *screensaver.Engine) {
	logutil.Log("TEST MODE: %s", mode)

	switch mode {
	case "wallpaper":
		cfg.WallpaperEnabled = true
		if err := wpEngine.Start(); err != nil {
			logutil.Log("TEST wallpaper FAILED: %v", err)
			os.Exit(2)
		}
		logutil.Log("TEST wallpaper started, running 25s")
		time.Sleep(25 * time.Second)
		wpEngine.Stop()
		logutil.Log("TEST wallpaper stopped")

	case "screensaver":
		if err := ssEngine.Start(); err != nil {
			logutil.Log("TEST screensaver FAILED: %v", err)
			os.Exit(2)
		}
		logutil.Log("TEST screensaver started, running 15s")
		time.Sleep(15 * time.Second)
		ssEngine.Stop()
		logutil.Log("TEST screensaver stopped")

	case "standalone":
		// Plain top-level WebView2 window at 200,100 800x600 - no reparenting.
		// Diagnostic: if this renders, the issue is in Progman embedding.
		wv, err := webview.CreateWebView(0, cfg.ScreensaverURL, 200, 100, 800, 600)
		if err != nil {
			logutil.Log("TEST standalone FAILED: %v", err)
			os.Exit(2)
		}
		if err := wv.WaitReady(); err != nil {
			logutil.Log("TEST standalone ready FAILED: %v", err)
			os.Exit(2)
		}
		logutil.Log("TEST standalone window created hwnd=%x", wv.HWND())
		time.Sleep(15 * time.Second)
		wv.Close()
		logutil.Log("TEST standalone closed")

	case "settings":
		editCfg := *cfg
		w, err := settings.New(&editCfg, nil, nil, nil)
		if err != nil {
			logutil.Log("TEST settings FAILED: %v", err)
			os.Exit(2)
		}
		logutil.Log("TEST settings window opened, hwnd=%x", w.HWND())
		// Run message loop for 15s, then destroy
		go func() {
			time.Sleep(15 * time.Second)
			w.Close()
		}()
		webview.RunMessageLoop()
		logutil.Log("TEST settings closed")
	}
	logutil.Log("TEST MODE %s complete", mode)
}
