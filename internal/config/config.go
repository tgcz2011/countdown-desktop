package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

type Config struct {
	WallpaperURL       string `json:"wallpaper_url"`
	ScreensaverURL     string `json:"screensaver_url"`
	ScreensaverTime    int    `json:"screensaver_time"`
	WallpaperEnabled   bool   `json:"wallpaper_enabled"`
	ScreensaverEnabled bool   `json:"screensaver_enabled"`
}

func DefaultConfig() *Config {
	return &Config{
		WallpaperURL:       "https://zztool.free.nf/countdown",
		ScreensaverURL:     "https://zztool.free.nf/countdown",
		ScreensaverTime:    600,
		WallpaperEnabled:   false,
		ScreensaverEnabled: true,
	}
}

func ConfigPath() (string, error) {
	exe, err := os.Executable()
	if err != nil {
		return "", fmt.Errorf("get executable path: %w", err)
	}
	return filepath.Join(filepath.Dir(exe), "config.json"), nil
}

func Load() (*Config, error) {
	path, err := ConfigPath()
	if err != nil {
		return DefaultConfig(), nil
	}
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			cfg := DefaultConfig()
			_ = cfg.Save()
			return cfg, nil
		}
		return DefaultConfig(), fmt.Errorf("read config: %w", err)
	}
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return DefaultConfig(), fmt.Errorf("parse config: %w", err)
	}
	if cfg.WallpaperURL == "" {
		cfg.WallpaperURL = "https://zztool.free.nf/countdown"
	}
	if cfg.ScreensaverURL == "" {
		cfg.ScreensaverURL = "https://zztool.free.nf/countdown"
	}
	if cfg.ScreensaverTime <= 0 {
		cfg.ScreensaverTime = 600
	}
	return &cfg, nil
}

func (c *Config) Save() error {
	path, err := ConfigPath()
	if err != nil {
		return err
	}
	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal config: %w", err)
	}
	return os.WriteFile(path, data, 0644)
}
