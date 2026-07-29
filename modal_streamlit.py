"""
用 Modal 免費/低成本 CPU 託管 Streamlit（線上公開網址）。

成本說明（白話）：
- 用 CPU，不用 GPU
- 沒人用時會自動縮到 0（省錢）
- 輕量 streamlit + pydantic，預估閒置近乎 $0；
  偶爾用手機開模板，通常遠低於每月 $30 免費額度

部署：
    modal deploy modal_streamlit.py

本機測試入口仍可用：
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import subprocess

import modal

APP_NAME = "jianying-assistant-ui"

app = modal.App(APP_NAME)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "streamlit>=1.32",
        "pydantic>=2.0",
    )
    .add_local_dir(
        ".",
        remote_path="/app",
        ignore=[
            ".git",
            ".git/**",
            "**/__pycache__",
            "**/*.pyc",
            ".venv",
            "venv",
            "assets",
            "assets/**",
            "tests",
            "tests/**",
            ".streamlit/secrets.toml",
            "ltx-*",
            "*.mp4",
            "*.mp3",
            "*.wav",
        ],
    )
)


@app.function(
    image=image,
    timeout=600,
    # 沒流量約 1 分鐘後縮掉，省錢
    scaledown_window=60,
)
@modal.concurrent(max_inputs=40)
@modal.web_server(port=8501, startup_timeout=180)
def ui() -> None:
    """啟動 Streamlit 網頁服務。"""
    subprocess.Popen(
        [
            "streamlit",
            "run",
            "/app/streamlit_app.py",
            "--server.port",
            "8501",
            "--server.address",
            "0.0.0.0",
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd="/app",
    )
