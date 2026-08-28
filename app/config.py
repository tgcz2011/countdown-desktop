# -*- coding: utf-8 -*-
r"""配置持久化：%APPDATA%\CountdownDesktop\config.json"""
import json
import os

DEFAULT_URL = "https://zztool.free.nf/countdown"

# 图片/视频画幅模式：cover=铺满裁剪 | contain=完整显示留黑边 | fill=拉伸铺满
FIT_MODES = ("cover", "contain", "fill")
FIT_LABELS = {"cover": "铺满全屏（裁剪）", "contain": "保留原内容（黑边）", "fill": "铺满全屏（拉伸）"}

DEFAULTS = {
    "wallpaper": {
        "enabled": True,
        "url": DEFAULT_URL,
        "fit": "cover",   # 仅对图片/视频源生效
        "mute": True,     # 壁纸默认静音
    },
    "screensaver": {
        "enabled": True,
        "url": DEFAULT_URL,
        "timeout": 600,
        "fit": "cover",
        "mute": True,     # 屏保默认静音
    },
    "playback": {
        "video_loop": True,   # 视频循环播放
    },
    "auto_check_update": True,  # 启动时自动检查更新（仅查询提示）
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
