"""
剪映小助手 — Streamlit 模板設定介面（主程式）。

部署：
- 線上（推薦）：Streamlit Community Cloud，入口檔 streamlit_app.py
- 本機測試：streamlit run streamlit_app.py

階段進度：
- ✅ 階段 1：資料結構 + 頁面框架 + 全域設定（雲端可部署）
- ✅ 階段 2：分鏡管理與詳細設定表單
- ⏳ 階段 3：可視化預覽 + 模板下載/上傳 JSON + 手機友善
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
from src.ui.components.shot_manager import render_shot_manager_page
from src.ui.session_state import (
    KEY_ACTIVE_SHOT,
    KEY_PAGE,
    get_template,
    init_session_state,
    set_template,
)



def render_sidebar() -> str:
    """側邊欄：導覽 + 專案摘要。回傳目前選中的頁面名稱。"""
    template = get_template()
    g = template.global_settings

    st.sidebar.title("🎬 剪映小助手")
    st.sidebar.caption("線上模板設定 · 階段 1+2 · 免費雲端版")


    pages = [
        "全域設定",
        "分鏡管理",
        "可視化預覽（階段 3）",
        "模板下載上傳（階段 3）",
        "使用說明與部署",
    ]

    current = st.session_state.get(KEY_PAGE, pages[0])
    if current not in pages:
        current = pages[0]

    page = st.sidebar.radio(
        "功能選單",
        options=pages,
        index=pages.index(current),
        help="階段 1 請先把「全域設定」弄好；其他頁面是預告。",
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
        "⚠️ 雲端不會永久存檔。關掉網頁後設定可能消失。"
        "階段 3 會提供「下載 JSON → 放到 Google 雲端硬碟」的保存方式。"
    )
    return page


def render_placeholder(title: str, phase: str, bullets: list[str]) -> None:
    """尚未實作的頁面預告。"""
    st.header(title)
    st.warning(f"此功能安排在 **{phase}**，目前僅作預告。")
    st.markdown("預計會有：")
    for b in bullets:
        st.markdown(f"- {b}")
    st.info("請先完成「全域設定」，確認沒問題後再告訴我繼續下一階段。")


def render_help_and_deploy() -> None:
    """使用說明：雲端部署、模板保存、架構白話。"""
    st.header("使用說明與部署")

    st.markdown(
        """
### 這個網站是做什麼的？

讓你在**手機或電腦瀏覽器**事先設好影片模板（解析度、BGM 參數、分鏡風格等）。  
之後再搭配 **Coze** 產出的素材，在**自己電腦**上生成剪映草稿。

### 為什麼是「線上」而不是「只裝在電腦」？

你常常人在外面只有手機。部署到 **Streamlit Community Cloud（免費）** 後，  
用手機瀏覽器就能開網址改模板。

### 模板怎麼保存？（很重要）

雲端網站**不能**直接寫入你的 Google 雲端硬碟或電腦資料夾。

建議流程（階段 3 會做成按鈕）：

1. 在網頁把模板設好  
2. 按 **下載 JSON 檔**  
3. 把檔案放到有同步的 **Google 雲端硬碟** 資料夾  
4. 下次要改：從雲端硬碟取出 → 網頁 **上傳 JSON** 載入  

階段 1 可先在下方預覽 JSON 結構；正式下載/上傳在階段 3。
"""
    )

    with st.expander("📦 怎麼免費部署到 Streamlit Cloud？", expanded=True):
        st.markdown(
            """
1. 把本專案推到 **GitHub**  
2. 打開 [share.streamlit.io](https://share.streamlit.io/) 用 GitHub 登入  
3. **New app**，選擇你的倉庫  
4. **Main file path** 填：`streamlit_app.py`  
5. 部署完成後用手機打開給你的網址  

更細的步驟與常見問題：專案裡的 `docs/STREAMLIT_CLOUD_DEPLOY.md`
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

> 剪映草稿資料夾只在你 Windows 電腦裡，所以「生成草稿」一定要本機做；  
> 雲端只負責「人在外面也能改模板」。
"""
        )

    st.subheader("開發階段")
    st.markdown(
        """
1. **階段 1（完成）**：資料結構 + 頁面框架 + 全域設定 + 可雲端部署  
2. **階段 2（完成）**：分鏡管理 + 每鏡詳細設定  
3. **階段 3（下一步）**：9:16 預覽 + JSON 下載/上傳 + 手機版面再優化  

"""
    )

    st.subheader("目前記憶體中的模板 JSON（除錯 / 先複製用）")
    st.caption(
        "階段 1 可暫時全選複製存成 .json；階段 3 會改成正式下載按鈕。"
    )
    template = get_template()
    with st.expander("展開查看 JSON", expanded=False):
        st.code(template.model_dump_json_pretty(), language="json")


def main() -> None:
    """Streamlit 應用入口（本機與雲端共用）。"""
    st.set_page_config(
        page_title="剪映小助手",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="auto",  # 手機自動收合側邊欄
    )
    init_session_state()

    page = render_sidebar()

    if page == "全域設定":
        render_global_settings()
    elif page == "分鏡管理":
        render_shot_manager_page()

    elif page == "可視化預覽（階段 3）":
        render_placeholder(
            "可視化預覽",
            "階段 3",
            [
                "9:16 直式預覽框",
                "大致顯示目前分鏡的圖片與字幕位置",
                "幫助判斷排版是否合理（不必 100% 等於剪映）",
            ],
        )
    elif page == "模板下載上傳（階段 3）":
        render_placeholder(
            "模板下載 / 上傳",
            "階段 3",
            [
                "一鍵下載目前設定為 JSON 檔",
                "上傳 JSON 載入模板",
                "介面說明：下載後請放到 Google 雲端硬碟",
                "可選模板 ID（例如 A01）方便之後對應",
            ],
        )
    else:
        render_help_and_deploy()
