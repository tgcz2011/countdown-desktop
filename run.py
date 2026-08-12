# -*- coding: utf-8 -*-
"""入口：无参数=主程序（托盘），player <mode>=播放器进程。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "player":
        mode = sys.argv[2] if len(sys.argv) > 2 else "wallpaper"
        from app import player
        player.run(mode)
    else:
        from app import main
        sys.exit(main.run())
