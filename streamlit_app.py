"""
剪映小助手 — Streamlit Community Cloud 入口檔。

為什麼需要這個檔？
- 雲端部署時，Streamlit 會從「倉庫根目錄」找主程式
- 把入口放在根目錄最不容易踩坑
- 本機也可以：streamlit run streamlit_app.py

部署目標：Streamlit Community Cloud（免費）
Main file path 請填：streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 確保雲端 / 本機都能 import src
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.ui.app import main

# streamlit run 會執行本檔；只呼叫一次 main
main()
