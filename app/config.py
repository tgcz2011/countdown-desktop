# -*- coding: utf-8 -*-
"""配置持久化：%APPDATA%\CountdownDesktop\config.json"""
import json
import os

DEFAULT_URL = "https://zztool.free.nf/countdown"

DEFAULTS = {
    "wallpaper": {
        "enabled": True,
        "url": DEFAULT_URL,
    },
    "screensaver": {
        "enabled": True,
        "url": DEFAULT_URL,
        "timeout": 600,
    },
    "run_at_startup": False,
}


def config_dir() -> str:
    d = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                     "CountdownDesktop")
    os.makedirs(d, exist_ok=True)
    return d


def config_path() -> str:
    return os.path.join(config_dir(), "config.json")


def load() -> dict:
    """读取配置，缺省值补齐（深合并）。"""
    cfg = json.loads(json.dumps(DEFAULTS))
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return cfg
    for section, values in data.items():
        if isinstance(values, dict) and isinstance(cfg.get(section), dict):
            cfg[section].update(values)
        else:
            cfg[section] = values
    return cfg


def save(cfg: dict) -> None:
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
