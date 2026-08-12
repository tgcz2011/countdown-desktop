# -*- coding: utf-8 -*-
"""应用配置管理（JSON 持久化，exe 同目录 config.json）"""
import json
import os
import sys

DEFAULT_WALLPAPER_URL = "https://zztool.free.nf/countdown"
DEFAULT_SCREENSAVER_URL = "https://zztool.free.nf/countdown"
DEFAULT_SCREENSAVER_TIME = 600  # 秒


def app_dir() -> str:
    """返回可执行文件所在目录（开发时为脚本目录）"""
    if getattr(sys, "frozen", False):  # PyInstaller
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def config_path() -> str:
    return os.path.join(app_dir(), "config.json")


def default_config() -> dict:
    return {
        "wallpaper_url": DEFAULT_WALLPAPER_URL,
        "screensaver_url": DEFAULT_SCREENSAVER_URL,
        "screensaver_time": DEFAULT_SCREENSAVER_TIME,
        "wallpaper_enabled": False,
        "screensaver_enabled": True,
    }


def load() -> dict:
    cfg = default_config()
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in cfg:
            if k in data:
                cfg[k] = data[k]
    except FileNotFoundError:
        save(cfg)  # 首次运行生成默认配置
    except Exception as e:
        print(f"[config] load error: {e}")
    # 校验
    if not cfg.get("wallpaper_url"):
        cfg["wallpaper_url"] = DEFAULT_WALLPAPER_URL
    if not cfg.get("screensaver_url"):
        cfg["screensaver_url"] = DEFAULT_SCREENSAVER_URL
    if cfg.get("screensaver_time", 0) <= 0:
        cfg["screensaver_time"] = DEFAULT_SCREENSAVER_TIME
    return cfg


def save(cfg: dict) -> None:
    try:
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[config] save error: {e}")
