# -*- coding: utf-8 -*-
"""媒体壁纸渲染测试：对指定源启动壁纸播放器并抓取桌面宿主窗口。
用法: python tools/test_media.py <source> <out.png>
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

source = sys.argv[1]
out = sys.argv[2]

from app import config, win32

cfg = config.load()
cfg["wallpaper"]["enabled"] = True
cfg["wallpaper"]["url"] = source
config.save(cfg)

proc = subprocess.Popen([sys.executable, "run.py", "player", "wallpaper"],
                        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        creationflags=subprocess.CREATE_NO_WINDOW)
time.sleep(9)
subprocess.run([sys.executable, os.path.join("tools", "capture.py"), out, "host"],
               cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
proc.terminate()
time.sleep(1)
print("done", out)
