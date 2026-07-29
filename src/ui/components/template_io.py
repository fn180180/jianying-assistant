"""
模板 JSON 下載 / 上傳。

白話：
- 雲端網站存不進你的 Google 雲端硬碟
- 所以用「下載 JSON 帶走 → 自己放 Drive → 需要時再上傳」
"""

from __future__ import annotations

import json
import re
from datetime import datetime

import streamlit as st

from src.template_models import ProjectTemplate, template_from_dict, template_to_dict
from src.ui.session_state import KEY_ACTIVE_SHOT, get_template, set_template


def _safe_filename(name: str) -> str:
    """檔名去掉不適合字元。"""
    s = re.sub(r'[\\/:*?"<>|]+', "_", (name or "template").strip())
    s = s.replace(" ", "_")
    return s[:60] or "template"


def render_template_io_page() -> None:
    """模板下載 / 上傳整頁。"""
    st.header("模板下載 / 上傳")
    st.caption("把設定帶走、下次再載入。請搭配 Google 雲端硬碟保存。")

    st.info(
        """
**建議操作流程（免費、手機也適用）**

1. 在本網站把模板設好  
2. 按下方 **「下載 JSON」**  
3. 把檔案存進 **Google 雲端硬碟** 同步資料夾  
   （例如：`我的雲端硬碟/剪映小助手模板/`）  
4. 下次在外面要用：從 Drive 找出檔案 → 按 **「上傳載入」**  

⚠️ 關掉網頁後，畫面上的設定可能消失；**只有下載的 JSON 才是永久備份**。
"""
    )

    template = get_template()

    # ------------------------------------------------------------------
    # 模板 meta
    # ------------------------------------------------------------------
    st.subheader("1. 模板資訊（下載前可改）")
    col1, col2 = st.columns(2)
    with col1:
        template_id = st.text_input(
            "模板 ID（可選）",
            value=template.template_id or "",
            placeholder="例如 A01",
            help="方便之後對應，例如 A01=心理學鈎子模板。",
        )
    with col2:
        template_name = st.text_input(
            "模板名稱",
            value=template.template_name,
            help="下載檔名也會用到。",
        )
    description = st.text_area(
        "模板說明（可選）",
        value=template.description or "",
        height=70,
        help="寫給未來的自己：這個模板用在什麼影片。",
    )

    if st.button("💾 先更新模板資訊到目前設定", use_container_width=True):
        updated = template.model_copy(
            update={
                "template_id": (template_id or "").strip() or None,
                "template_name": (template_name or "").strip() or "未命名模板",
                "description": (description or "").strip(),
            }
        )
        set_template(updated)
        st.success("模板資訊已更新")
        st.rerun()

    template = get_template()

    # ------------------------------------------------------------------
    # 下載
    # ------------------------------------------------------------------
    st.subheader("2. 下載目前設定為 JSON")
    tid = template.template_id or "T"
    fname = (
        f"{_safe_filename(tid)}_{_safe_filename(template.template_name)}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    )
    payload = template.model_dump_json_pretty().encode("utf-8")

    st.download_button(
        label="⬇️ 下載模板 JSON",
        data=payload,
        file_name=fname,
        mime="application/json",
        type="primary",
        use_container_width=True,
        help="下載後請放到 Google 雲端硬碟保存。",
    )
    st.caption(f"建議檔名：`{fname}` → 放到 Drive 的「剪映小助手模板」資料夾")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("專案", template.global_settings.project_name)
    c2.metric("分鏡數", len(template.shots))
    c3.metric("總時長", f"{template.total_duration():.1f}s")
    c4.metric("模板ID", template.template_id or "（無）")

    with st.expander("預覽將下載的 JSON", expanded=False):
        st.code(template.model_dump_json_pretty(), language="json")

    st.divider()

    # ------------------------------------------------------------------
    # 上傳
    # ------------------------------------------------------------------
    st.subheader("3. 上傳 JSON 載入模板")
    st.caption("從 Google 雲端硬碟下載到手機/電腦後，再選檔上傳。")

    uploaded = st.file_uploader(
        "選擇模板 JSON 檔",
        type=["json"],
        help="只接受 .json。會覆蓋目前畫面上的設定。",
    )

    if uploaded is not None:
        try:
            raw_text = uploaded.read().decode("utf-8")
            data = json.loads(raw_text)
            loaded = template_from_dict(data)
        except Exception as e:
            st.error(f"讀取失敗：{e}\n請確認檔案是本工具匯出的 JSON。")
            return

        st.success(
            f"檔案可讀：【{loaded.template_name}】"
            f"分鏡 {len(loaded.shots)} 個，總時長 {loaded.total_duration():.1f}s"
        )
        with st.expander("上傳檔內容摘要", expanded=False):
            st.json(template_to_dict(loaded))

        if st.button(
            "✅ 確認載入（會覆蓋目前設定）",
            type="primary",
            use_container_width=True,
        ):
            set_template(loaded)
            st.session_state[KEY_ACTIVE_SHOT] = (
                loaded.shots[0].id if loaded.shots else None
            )
            st.success("已載入模板！可到「分鏡管理」或「可視化預覽」查看。")
            st.balloons()
            st.rerun()

    st.divider()
    st.subheader("Google 雲端硬碟怎麼放？（白話）")
    st.markdown(
        """
1. 手機打開 **Google 雲端硬碟 App** 或電腦開 drive.google.com  
2. 新建資料夾，例如「**剪映小助手模板**」  
3. 把下載的 `.json` 丟進去（開同步的話，電腦資料夾也會有）  
4. 之後在外面只要：Drive → 下載/選取 → 回到本網站上傳  

這樣即使換手機、清瀏覽器，模板都還在雲端硬碟裡。
"""
    )
