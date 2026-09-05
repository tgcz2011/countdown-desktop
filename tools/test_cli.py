# -*- coding: utf-8 -*-
"""开发验证：命令行参数解析 / 覆盖应用 / exam_type 迁移（无需 GUI）。"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import cli, config  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("PASS", name)
    else:
        FAILS.append(name)
        print("FAIL", name, detail)


def test_parse():
    ov, probs = cli.parse_argv(
        ["prog", "player", "wallpaper", "--exam=zhongkao",
         "--wallpaper-url", "https://example.com/a", "--video-loop=off"])
    check("parse: exam", ov.get("exam") == "zhongkao", ov)
    check("parse: separated url", ov.get("wallpaper_url") == "https://example.com/a", ov)
    check("parse: bool off", ov.get("video_loop") is False, ov)
    check("parse: no problems", probs == [], probs)

    ov2, probs2 = cli.parse_argv(["prog", "--screensaver-timeout", "300"])
    check("parse: int", ov2.get("screensaver_timeout") == 300, ov2)
    check("parse: int no problems", probs2 == [], probs2)

    ov3, probs3 = cli.parse_argv(["prog", "--exam", "zhongkao"])
    check("parse: separated option value", ov3.get("exam") == "zhongkao", ov3)

    ov4, probs4 = cli.parse_argv(["prog", "--bogus-flag", "--exam=gaokao"])
    check("parse: unknown collected", "--bogus-flag" in probs4, probs4)
    check("parse: known still parsed", ov4.get("exam") == "gaokao", ov4)

    ov5, probs5 = cli.parse_argv(["prog", "--exam=bogus"])
    check("parse: bad value no crash", ov5 == {}, probs5)
    check("parse: bad value reported", len(probs5) == 1, probs5)

    ov6, probs6 = cli.parse_argv(["prog", "--help"])
    check("parse: help silent", ov6 == {} and probs6 == [], (ov6, probs6))

    ov7, probs7 = cli.parse_argv(["prog", "player", "--exam=zhongkao"])
    check("parse: player positional skipped", ov7.get("exam") == "zhongkao", ov7)


def test_serialize_roundtrip():
    ov = {"exam": "zhongkao", "video_loop": False, "screensaver_timeout": 120}
    tokens = cli.serialize(ov)
    ov2, probs = cli.parse_argv(["prog", "player", "wallpaper"] + tokens)
    check("serialize: roundtrip", ov2 == ov and probs == [], (tokens, ov2, probs))
    check("serialize: key names", "--exam=zhongkao" in tokens and "--video-loop=false" in tokens,
          tokens)


def test_apply():
    # exam=zhongkao → 壁纸/屏保统一切到中考地址
    cfg = json.loads(json.dumps(config.DEFAULTS))
    cli.apply({"exam": "zhongkao"}, cfg)
    check("apply: exam zhongkao type", cfg["exam_type"] == "zhongkao")
    check("apply: exam zhongkao wallpaper url",
          cfg["wallpaper"]["url"] == config.JUNIOR_URL, cfg["wallpaper"]["url"])
    check("apply: exam zhongkao ss url",
          cfg["screensaver"]["url"] == config.JUNIOR_URL, cfg["screensaver"]["url"])

    # 显式 URL 覆盖优先，且未带 --exam 时类型转 custom
    cfg2 = json.loads(json.dumps(config.DEFAULTS))
    cli.apply({"wallpaper_url": "https://example.com/x"}, cfg2)
    check("apply: url override wins",
          cfg2["wallpaper"]["url"] == "https://example.com/x", cfg2["wallpaper"]["url"])
    check("apply: url override sets custom", cfg2["exam_type"] == "custom", cfg2["exam_type"])
    check("apply: ss untouched",
          cfg2["screensaver"]["url"] == config.DEFAULT_URL, cfg2["screensaver"]["url"])

    # 同时给 exam + 显式 URL：exam 生效，显式 URL 用于对应源
    cfg3 = json.loads(json.dumps(config.DEFAULTS))
    cli.apply({"exam": "zhongkao", "wallpaper_url": "https://example.com/y"}, cfg3)
    check("apply: exam+url type", cfg3["exam_type"] == "zhongkao")
    check("apply: exam+url wallpaper",
          cfg3["wallpaper"]["url"] == "https://example.com/y", cfg3["wallpaper"]["url"])
    check("apply: exam+url ss junior",
          cfg3["screensaver"]["url"] == config.JUNIOR_URL, cfg3["screensaver"]["url"])

    # 其他标量覆盖
    cfg4 = json.loads(json.dumps(config.DEFAULTS))
    cli.apply({"screensaver_timeout": 300, "video_loop": False,
               "wallpaper_mute": False, "screensaver_enabled": False}, cfg4)
    check("apply: timeout", cfg4["screensaver"]["timeout"] == 300)
    check("apply: video_loop", cfg4["playback"]["video_loop"] is False)
    check("apply: mute", cfg4["wallpaper"]["mute"] is False)
    check("apply: ss enabled", cfg4["screensaver"]["enabled"] is False)

    # exam=custom 不动 URL
    cfg5 = json.loads(json.dumps(config.DEFAULTS))
    cfg5["wallpaper"]["url"] = "https://custom.example.com/w"
    cli.apply({"exam": "custom"}, cfg5)
    check("apply: custom keeps url", cfg5["wallpaper"]["url"] == "https://custom.example.com/w")


def test_config_migration():
    tmp = tempfile.mkdtemp(prefix="cd-test-")
    old_dir = config.config_dir
    config.config_dir = lambda: tmp
    try:
        # 旧版配置（无 exam_type，壁纸/屏保都是高考默认）→ gaokao
        with open(os.path.join(tmp, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"wallpaper": {"enabled": True, "url": config.DEFAULT_URL},
                       "screensaver": {"enabled": True, "url": config.DEFAULT_URL}}, f)
        cfg = config.load()
        check("migration: gaokao default", cfg["exam_type"] == "gaokao", cfg["exam_type"])

        # 旧版配置两处都是中考地址 → zhongkao
        with open(os.path.join(tmp, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"wallpaper": {"url": config.JUNIOR_URL},
                       "screensaver": {"url": config.JUNIOR_URL}}, f)
        cfg = config.load()
        check("migration: zhongkao", cfg["exam_type"] == "zhongkao", cfg["exam_type"])

        # 旧版配置曾自定义 → custom
        with open(os.path.join(tmp, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"wallpaper": {"url": "https://a.example.com"},
                       "screensaver": {"url": "https://b.example.com"}}, f)
        cfg = config.load()
        check("migration: custom", cfg["exam_type"] == "custom", cfg["exam_type"])

        # 新版配置保留 exam_type
        with open(os.path.join(tmp, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"exam_type": "zhongkao",
                       "wallpaper": {"url": config.JUNIOR_URL},
                       "screensaver": {"url": config.JUNIOR_URL}}, f)
        cfg = config.load()
        check("migration: kept zhongkao", cfg["exam_type"] == "zhongkao", cfg["exam_type"])

        # 无配置文件 → 高考默认
        os.remove(os.path.join(tmp, "config.json"))
        cfg = config.load()
        check("migration: fresh defaults", cfg["exam_type"] == "gaokao"
              and cfg["wallpaper"]["url"] == config.DEFAULT_URL, cfg)
    finally:
        config.config_dir = old_dir
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def test_effective():
    # resolve_exam 与 default_url
    cfg = json.loads(json.dumps(config.DEFAULTS))
    cfg["exam_type"] = "zhongkao"
    config.resolve_exam(cfg)
    check("resolve_exam zhongkao", cfg["wallpaper"]["url"] == config.JUNIOR_URL)
    check("default_url gaokao", config.default_url("gaokao") == config.DEFAULT_URL)
    check("default_url zhongkao", config.default_url("zhongkao") == config.JUNIOR_URL)
    check("default_url custom fallback", config.default_url("custom") == config.DEFAULT_URL)


if __name__ == "__main__":
    test_parse()
    test_serialize_roundtrip()
    test_apply()
    test_config_migration()
    test_effective()
    print("----")
    if FAILS:
        print("FAILED:", FAILS)
        sys.exit(1)
    print("ALL PASS")
