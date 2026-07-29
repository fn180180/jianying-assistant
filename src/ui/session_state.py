"""
Streamlit session_state 初始化與讀寫小工具。

白話說明：
- Streamlit 每次互動都會重新跑一遍腳本
- 所以「目前專案設定」必須存在 st.session_state 裡，才不會一改就不見
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.template_models import (
    ProjectTemplate,
    create_default_template,
    template_from_dict,
    template_to_dict,
)

# session_state 用的 key 常數（集中管理，避免拼錯字）
KEY_TEMPLATE = "jy_template"  # 目前編輯中的模板（dict）
KEY_ACTIVE_SHOT = "jy_active_shot_id"  # 目前選中的分鏡 id
KEY_PAGE = "jy_page"  # 側邊欄頁面


def init_session_state() -> None:
    """第一次進入頁面時，放入預設模板。"""
    if KEY_TEMPLATE not in st.session_state:
        default = create_default_template("我的短視頻", with_hook=True)
        st.session_state[KEY_TEMPLATE] = template_to_dict(default)

    if KEY_ACTIVE_SHOT not in st.session_state:
        shots = st.session_state[KEY_TEMPLATE].get("shots") or []
        st.session_state[KEY_ACTIVE_SHOT] = shots[0]["id"] if shots else None

    if KEY_PAGE not in st.session_state:
        st.session_state[KEY_PAGE] = "全域設定"


def get_template() -> ProjectTemplate:
    """從 session_state 取出並驗證成 ProjectTemplate。"""
    raw: dict[str, Any] = st.session_state[KEY_TEMPLATE]
    return template_from_dict(raw)


def set_template(template: ProjectTemplate) -> None:
    """把模板寫回 session_state。"""
    st.session_state[KEY_TEMPLATE] = template_to_dict(template)


def update_global_settings(**kwargs: Any) -> ProjectTemplate:
    """
    只更新全域設定的部分欄位，其餘維持不變。

    用法：update_global_settings(project_name="新名字", width=1080)
    """
    template = get_template()
    new_global = template.global_settings.model_copy(update=kwargs)
    updated = template.model_copy(update={"global_settings": new_global})
    set_template(updated)
    return updated
