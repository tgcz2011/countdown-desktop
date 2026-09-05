# -*- coding: utf-8 -*-
"""入口：无参数=主程序（托盘），player <mode>=播放器进程。

播放器 mode 取「player」后的第一个非选项参数（wallpaper / screensaver），
其余选项参数（--exam 等，单次有效）由 app/cli 统一解析。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "player":
        mode = "wallpaper"
        for a in args[1:]:
            if not a.startswith("-"):
                mode = a
                break
        from app import player
        player.run(mode)
    else:
        from app import main
        sys.exit(main.run())
