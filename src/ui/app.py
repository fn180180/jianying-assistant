"""
剪映小助手 — Streamlit 模板設定介面（主程式）。

部署：
- 線上（推薦）：Streamlit Community Cloud，入口檔 streamlit_app.py
- 本機測試：streamlit run streamlit_app.py

階段進度：
- ✅ 階段 1：資料結構 + 頁面框架 + 全域設定（雲端可部署）
- ✅ 階段 2：分鏡管理與詳細設定表單
- ✅ 階段 3：可視化預覽 + 模板下載/上傳 JSON + 手機友善
"""

from __future__ import annotations

import sys
from pathlib import Path

# 確保可從專案根目錄 import src.*
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from src.template_models import create_default_template
from src.ui.components.global_settings_form import render_global_settings
from src.ui.components.preview import render_preview_page
from src.ui.components.shot_manager import render_shot_manager_page
from src.ui.components.template_io import render_template_io_page
from src.ui.session_state import (
    KEY_ACTIVE_SHOT,
    KEY_PAGE,
    get_template,
    init_session_state,
    set_template,
)

# 手機友善：縮小內距、按鈕更好點
_MOBILE_CSS = """
<style>
  /* 讓主內容在窄螢幕不要太擠 */
  .block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    padding-left: 1rem;
    padding-right: 1rem;
    max-width: 1100px;
  }
  /* 側邊欄文字稍大一點，手機好點 */
  section[data-testid="stSidebar"] button {
    min-height: 2.4rem;
  }
  /* metric 在手機較好讀 */
  [data-testid="stMetricValue"] {
    font-size: 1.1rem;
  }
  @media (max-width: 640px) {
    .block-container {
      padding-left: 0.6rem;
      padding-right: 0.6rem;
    }
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.25rem !important; }
    h3 { font-size: 1.1rem !important; }
  }
</style>
"""


def render_sidebar() -> str:
    """側邊欄：導覽 + 專案摘要。回傳目前選中的頁面名稱。"""
    template = get_template()
    g = template.global_settings

    st.sidebar.title("🎬 剪映小助手")
    st.sidebar.caption("線上模板設定 · 完整版 · 免費雲端")

    pages = [
        "全域設定",
        "分鏡管理",
        "可視化預覽",
        "模板下載上傳",
        "使用說明與部署",
    ]

    # 相容舊 session 頁名
    aliases = {
        "可視化預覽（階段 3）": "可視化預覽",
        "模板下載上傳（階段 3）": "模板下載上傳",
        "分鏡管理（階段 2）": "分鏡管理",
    }
    current = st.session_state.get(KEY_PAGE, pages[0])
    current = aliases.get(current, current)
    if current not in pages:
        current = pages[0]

    page = st.sidebar.radio(
        "功能選單",
        options=pages,
        index=pages.index(current),
        help="手機請點左上角「>」打開選單。",
    )
    st.session_state[KEY_PAGE] = page

    st.sidebar.divider()
    st.sidebar.markdown("### 目前專案")
    st.sidebar.write(f"**{g.project_name}**")
    st.sidebar.write(f"解析度：{g.width} × {g.height}")
    st.sidebar.write(f"分鏡數：{len(template.shots)}")
    st.sidebar.write(f"總時長：{template.total_duration():.1f} 秒")
    if template.template_id:
        st.sidebar.write(f"模板 ID：`{template.template_id}`")

    st.sidebar.divider()
    if st.sidebar.button("🆕 重設為預設專案", use_container_width=True):
        fresh = create_default_template("我的短視頻", with_hook=True)
        set_template(fresh)
        st.session_state[KEY_ACTIVE_SHOT] = (
            fresh.shots[0].id if fresh.shots else None
        )
        st.sidebar.success("已重設")
        st.rerun()

    st.sidebar.caption(
        "⚠️ 雲端不會永久存檔。請用「模板下載上傳」把 JSON 存到 Google 雲端硬碟。"
    )
    return page


def render_help_and_deploy() -> None:
    """使用說明：雲端部署、模板保存、架構白話。"""
    st.header("使用說明與部署")

    st.markdown(
        """
### 這個網站是做什麼的？

讓你在**手機或電腦瀏覽器**事先設好影片模板（解析度、BGM 參數、分鏡風格等）。  
之後再搭配 **Coze** 產出的素材，在**自己電腦**上生成剪映草稿。

### 模板怎麼保存？

1. 設好模板 → **模板下載上傳** → 下載 JSON  
2. 放到 **Google 雲端硬碟**  
3. 下次上傳載入即可  
"""
    )

    with st.expander("📦 Streamlit Community Cloud 部署", expanded=False):
        st.markdown(
            """
1. 程式已在 GitHub（見專案 README）  
2. 打開 [share.streamlit.io](https://share.streamlit.io/) 用 GitHub 登入  
3. **New app** → Main file：`streamlit_app.py`  
4. 部署後用手機開啟網址  
"""
        )

    with st.expander("🏗️ 三大部分怎麼分工？"):
        st.markdown(
            """
| 部分 | 在哪裡跑 | 負責什麼 |
|------|----------|----------|
| **本 Streamlit 介面** | 雲端免費網站 | 模板設定與管理 |
| **Coze** | 雲端工作流 | 批量產出圖、配音、字幕文字等 |
| **pyJianYingDraft** | **你的電腦** | 寫入真正的剪映草稿 |
"""
        )

    st.subheader("開發階段")
    st.markdown(
        """
1. **階段 1（完成）**：資料結構 + 頁面框架 + 全域設定 + 可雲端部署  
2. **階段 2（完成）**：分鏡管理 + 每鏡詳細設定  
3. **階段 3（完成）**：9:16 預覽 + JSON 下載/上傳 + 手機版面優化  
"""
    )

    st.subheader("目前記憶體中的模板 JSON")
    template = get_template()
    with st.expander("展開查看 JSON", expanded=False):
        st.code(template.model_dump_json_pretty(), language="json")


def main() -> None:
    """Streamlit 應用入口（本機與雲端共用）。"""
    st.set_page_config(
        page_title="剪映小助手",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="auto",
    )
    st.markdown(_MOBILE_CSS, unsafe_allow_html=True)
    init_session_state()

    page = render_sidebar()

    if page == "全域設定":
        render_global_settings()
    elif page == "分鏡管理":
        render_shot_manager_page()
    elif page == "可視化預覽":
        render_preview_page()
    elif page == "模板下載上傳":
        render_template_io_page()
    else:
        render_help_and_deploy()
