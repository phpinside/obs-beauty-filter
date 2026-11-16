"""PyInstaller 入口。打包时把 src 加入搜索路径即可直接 import beautycam。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from beautycam.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
