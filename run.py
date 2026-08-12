# -*- coding: utf-8 -*-
"""开发入口 / PyInstaller 入口"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import main  # noqa: E402

if __name__ == "__main__":
    main()
