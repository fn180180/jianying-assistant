"""
表單小工具：下拉選單標籤轉換、位置/動畫元件。

白話：很多地方都要「中文顯示、英文存值」，集中寫一次避免重複。
"""

from __future__ import annotations

from typing import Callable, TypeVar

import streamlit as st

from src.template_models import (
    ANCHOR_LABELS,
    ANIM_IN_LABELS,
    ANIM_OUT_LABELS,
    MEDIA_TYPE_LABELS,
    POSITION_PRESET_LABELS,
    POSITION_PRESET_XY,
    AnchorPoint,
    AnimIn,
    AnimOut,
    MediaType,
    PositionPreset,
    Transform2D,
)

E = TypeVar("E")


def label_options(labels: dict[str, str]) -> list[str]:
    """回傳 value 列表（順序固定）。"""
    return list(labels.keys())


def format_label(labels: dict[str, str]) -> Callable[[str], str]:
    """給 selectbox 的 format_func。"""

    def _fmt(key: str) -> str:
        return labels.get(key, key)

    return _fmt


def safe_index(options: list[str], value: str, default: int = 0) -> int:
    try:
        return options.index(value)
    except ValueError:
        return default


def render_transform_controls(
    transform: Transform2D,
    *,
    key_prefix: str,
    show_scale: bool = True,
    show_opacity: bool = True,
    show_rotation: bool = True,
) -> Transform2D:
    """
    渲染位置快捷 + 變形滑桿，回傳更新後的 Transform2D。

    key_prefix 必須唯一（例如 media_xxx），避免 Streamlit widget 衝突。
    """
    preset_keys = label_options(POSITION_PRESET_LABELS)
    current_preset = (
        transform.position_preset.value
        if isinstance(transform.position_preset, PositionPreset)
        else str(transform.position_preset)
    )

    preset = st.selectbox(
        "位置快捷",
        options=preset_keys,
        index=safe_index(preset_keys, current_preset),
        format_func=format_label(POSITION_PRESET_LABELS),
        key=f"{key_prefix}_pos_preset",
        help="選一個大概位置就好；要微調請選「自訂位置」再用滑桿。",
    )

    # 快捷按鈕列（手機也可點）
    st.caption("快速按鈕（等同上面下拉）：")
    quick = [
        ("center", "置中"),
        ("top_center", "上中"),
        ("bottom_center", "下中"),
        ("top_right", "右上"),
        ("bottom_right", "右下"),
    ]
    cols = st.columns(len(quick))
    for i, (val, lab) in enumerate(quick):
        with cols[i]:
            if st.button(lab, key=f"{key_prefix}_qb_{val}", use_container_width=True):
                # 寫入 selectbox 的 session key，下一輪畫面會同步
                st.session_state[f"{key_prefix}_pos_preset"] = val
                st.rerun()


    if preset != PositionPreset.custom.value:
        x, y = POSITION_PRESET_XY[PositionPreset(preset)]
    else:
        c1, c2 = st.columns(2)
        with c1:
            x = st.slider(
                "水平 X（負左正右）",
                min_value=-1.5,
                max_value=1.5,
                value=float(transform.x),
                step=0.05,
                key=f"{key_prefix}_x",
                help="0=畫面正中間，正值往右，負值往左。",
            )
        with c2:
            y = st.slider(
                "垂直 Y（負下正上）",
                min_value=-1.5,
                max_value=1.5,
                value=float(transform.y),
                step=0.05,
                key=f"{key_prefix}_y",
                help="0=畫面正中間，正值往上，負值往下。",
            )

    anchor_keys = label_options(ANCHOR_LABELS)
    current_anchor = (
        transform.anchor.value
        if isinstance(transform.anchor, AnchorPoint)
        else str(transform.anchor)
    )
    anchor = st.selectbox(
        "對齊點",
        options=anchor_keys,
        index=safe_index(anchor_keys, current_anchor),
        format_func=format_label(ANCHOR_LABELS),
        key=f"{key_prefix}_anchor",
        help="元素用哪個點對齊畫面座標。一般用「中心」即可。",
    )

    scale = float(transform.scale)
    opacity = float(transform.opacity)
    rotation = float(transform.rotation)

    if show_scale:
        scale = st.slider(
            "縮放",
            min_value=0.1,
            max_value=3.0,
            value=min(max(float(transform.scale), 0.1), 3.0),
            step=0.05,
            key=f"{key_prefix}_scale",
            help="1.0=原大小，0.5=一半，2.0=兩倍。",
        )
    if show_opacity:
        opacity = st.slider(
            "透明度",
            min_value=0.0,
            max_value=1.0,
            value=float(transform.opacity),
            step=0.05,
            key=f"{key_prefix}_opacity",
            help="1=完全不透明，0=完全透明。",
        )
    if show_rotation:
        rotation = st.slider(
            "旋轉（度）",
            min_value=-180.0,
            max_value=180.0,
            value=float(transform.rotation),
            step=1.0,
            key=f"{key_prefix}_rot",
            help="正值順時針旋轉。",
        )

    return Transform2D(
        x=float(x),
        y=float(y),
        scale=float(scale),
        opacity=float(opacity),
        rotation=float(rotation),
        anchor=AnchorPoint(anchor),
        position_preset=PositionPreset(preset),
    )


def render_anim_selects(
    anim_in: AnimIn | str,
    anim_out: AnimOut | str,
    *,
    key_prefix: str,
) -> tuple[AnimIn, AnimOut]:
    """入場 / 出場動畫下拉。"""
    in_keys = label_options(ANIM_IN_LABELS)
    out_keys = label_options(ANIM_OUT_LABELS)
    in_val = anim_in.value if isinstance(anim_in, AnimIn) else str(anim_in)
    out_val = anim_out.value if isinstance(anim_out, AnimOut) else str(anim_out)

    c1, c2 = st.columns(2)
    with c1:
        new_in = st.selectbox(
            "入場動畫",
            options=in_keys,
            index=safe_index(in_keys, in_val),
            format_func=format_label(ANIM_IN_LABELS),
            key=f"{key_prefix}_anin",
            help="元素出現時的動畫效果。",
        )
    with c2:
        new_out = st.selectbox(
            "出場動畫",
            options=out_keys,
            index=safe_index(out_keys, out_val),
            format_func=format_label(ANIM_OUT_LABELS),
            key=f"{key_prefix}_anout",
            help="元素消失時的動畫效果。",
        )
    return AnimIn(new_in), AnimOut(new_out)


def render_media_type_select(media_type: MediaType | str, *, key: str) -> MediaType:
    keys = label_options(MEDIA_TYPE_LABELS)
    val = media_type.value if isinstance(media_type, MediaType) else str(media_type)
    chosen = st.selectbox(
        "素材類型",
        options=keys,
        index=safe_index(keys, val),
        format_func=format_label(MEDIA_TYPE_LABELS),
        key=key,
        help="圖片或視頻。",
    )
    return MediaType(chosen)
