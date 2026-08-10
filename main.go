package main

import (
	"fmt"
	"os"
	"sync"

	"golang.org/x/sys/windows"

	"github.com/tgcz2011/countdown-desktop/internal/config"
	"github.com/tgcz2011/countdown-desktop/internal/screensaver"
	"github.com/tgcz2011/countdown-desktop/internal/settings"
	"github.com/tgcz2011/countdown-desktop/internal/tray"
	"github.com/tgcz2011/countdown-desktop/internal/wallpaper"
	"github.com/tgcz2011/countdown-desktop/internal/webview"
	"github.com/tgcz2011/countdown-desktop/internal/win32"
	"github.com/tgcz2011/countdown-desktop/version"
)

func main() {
	fmt.Printf("Countdown Desktop v%s\n", version.Version)

	// Single instance check
	mutexName, _ := windows.UTF16PtrFromString("CountdownDesktop_SingleInstance")
	mutex, err := windows.CreateMutex(nil, false, mutexName)
	if err != nil || windows.GetLastError() == windows.ERROR_ALREADY_EXISTS {
		fmt.Println("Another instance is already running")
		os.Exit(0)
	}
	defer windows.CloseHandle(mutex)

	// Load config
	cfg, err := config.Load()
	if err != nil {
		fmt.Printf("Failed to load config: %v\n", err)
		cfg = config.DefaultConfig()
	}

	wpEngine := wallpaper.New(cfg)
	ssEngine := screensaver.New(cfg)
	actions := make(chan tray.Action, 10)

	trayIcon, err := tray.New(actions)
	if err != nil {
		fmt.Printf("Failed to create tray icon: %v\n", err)
		os.Exit(1)
	}

	// Start wallpaper if enabled
	if cfg.WallpaperEnabled {
		if err := wpEngine.Start(); err != nil {
			fmt.Printf("Failed to start wallpaper: %v\n", err)
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
				if cfg.WallpaperEnabled { _ = wpEngine.Start() } else { wpEngine.Stop() }

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
						if cfg.WallpaperEnabled { _ = wpEngine.Refresh() } else { wpEngine.Stop() }
					},
					func() { _ = wpEngine.Refresh() },
					func() { _ = ssEngine.Start() },
				)
				if err != nil {
					fmt.Printf("Failed to create settings window: %v\n", err)
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
				wpEngine.Stop()
				ssEngine.Stop()
				trayIcon.Remove()
				os.Exit(0)
			}
		}
	}()

	// Run main message loop for tray icon
	webview.RunMessageLoop()
}
