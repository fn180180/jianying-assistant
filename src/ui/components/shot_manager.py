"""
分鏡管理頁：列表操作 + 單一開詳細設定。

白話：
- 左邊/上方管「有哪些分鏡、順序、鈎子」
- 選中某一鏡後，下方編輯圖片/字幕/音訊細節
"""

from __future__ import annotations

import streamlit as st

from src.template_models import (
    AudioElement,
    MediaElement,
    MediaType,
    PositionPreset,
    ProjectTemplate,
    Shot,
    SubtitleElement,
    Transform2D,
    create_empty_shot,
)
from src.ui.components.form_helpers import (
    render_anim_selects,
    render_media_type_select,
    render_transform_controls,
)
from src.ui.session_state import KEY_ACTIVE_SHOT, get_template, set_template


# ---------------------------------------------------------------------------
# 分鏡列表操作
# ---------------------------------------------------------------------------


def _ensure_active_shot(template: ProjectTemplate) -> str | None:
    """保證 active shot id 有效，回傳目前 id。"""
    shots = template.shots
    if not shots:
        st.session_state[KEY_ACTIVE_SHOT] = None
        return None
    active = st.session_state.get(KEY_ACTIVE_SHOT)
    ids = {s.id for s in shots}
    if active not in ids:
        st.session_state[KEY_ACTIVE_SHOT] = shots[0].id
    return st.session_state[KEY_ACTIVE_SHOT]


def _replace_shot(template: ProjectTemplate, shot: Shot) -> ProjectTemplate:
    new_shots = [shot if s.id == shot.id else s for s in template.shots]
    return template.model_copy(update={"shots": new_shots})


def _move_shot(template: ProjectTemplate, shot_id: str, delta: int) -> ProjectTemplate:
    """delta=-1 上移，+1 下移。"""
    shots = list(template.shots)
    idx = next((i for i, s in enumerate(shots) if s.id == shot_id), None)
    if idx is None:
        return template
    new_idx = idx + delta
    if new_idx < 0 or new_idx >= len(shots):
        return template
    shots[idx], shots[new_idx] = shots[new_idx], shots[idx]
    return template.model_copy(update={"shots": shots})


def _delete_shot(template: ProjectTemplate, shot_id: str) -> ProjectTemplate:
    shots = [s for s in template.shots if s.id != shot_id]
    return template.model_copy(update={"shots": shots})


def _set_hook(template: ProjectTemplate, shot_id: str, is_hook: bool) -> ProjectTemplate:
    """
    標記鈎子。若設為 True，其他分鏡的 is_hook 清成 False（通常只有一個開頭鈎子）。
    """
    new_shots: list[Shot] = []
    for s in template.shots:
        if s.id == shot_id:
            new_shots.append(s.model_copy(update={"is_hook": is_hook}))
        elif is_hook:
            new_shots.append(s.model_copy(update={"is_hook": False}))
        else:
            new_shots.append(s)
    return template.model_copy(update={"shots": new_shots})


def render_shot_list_panel() -> None:
    """分鏡列表：新增、刪除、上下移、選取。"""
    template = get_template()
    st.subheader("分鏡列表")
    st.caption(
        "一支影片由很多分鏡串起來。可新增數十個；"
        "建議第一個設成「開頭鈎子」。"
    )

    c_add, c_info = st.columns([1, 2])
    with c_add:
        if st.button("➕ 新增分鏡", type="primary", use_container_width=True):
            idx = len(template.shots) + 1
            is_first = len(template.shots) == 0
            new_shot = create_empty_shot(idx, is_hook=is_first)
            shots = list(template.shots) + [new_shot]
            set_template(template.model_copy(update={"shots": shots}))
            st.session_state[KEY_ACTIVE_SHOT] = new_shot.id
            st.success(f"已新增：{new_shot.name}")
            st.rerun()
    with c_info:
        total = template.total_duration()
        st.info(f"目前 **{len(template.shots)}** 個分鏡，總時長約 **{total:.1f}** 秒")

    if not template.shots:
        st.warning("還沒有分鏡。請按「新增分鏡」開始。")
        return

    active_id = _ensure_active_shot(template)

    for i, shot in enumerate(template.shots):
        is_active = shot.id == active_id
        hook_tag = " 🪝鈎子" if shot.is_hook else ""
        label = f"{'▶ ' if is_active else ''}{i + 1}. {shot.name}{hook_tag}（{shot.duration:.1f}s）"

        with st.container(border=True):
            r1, r2, r3, r4, r5 = st.columns([3, 1, 1, 1, 1])
            with r1:
                if st.button(
                    label,
                    key=f"sel_{shot.id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state[KEY_ACTIVE_SHOT] = shot.id
                    st.rerun()
            with r2:
                if st.button("⬆", key=f"up_{shot.id}", disabled=i == 0, help="上移"):
                    set_template(_move_shot(template, shot.id, -1))
                    st.rerun()
            with r3:
                if st.button(
                    "⬇",
                    key=f"dn_{shot.id}",
                    disabled=i == len(template.shots) - 1,
                    help="下移",
                ):
                    set_template(_move_shot(template, shot.id, 1))
                    st.rerun()
            with r4:
                if st.button("🗑", key=f"del_{shot.id}", help="刪除"):
                    if len(template.shots) <= 1:
                        st.toast("至少保留 1 個分鏡", icon="⚠️")
                    else:
                        updated = _delete_shot(template, shot.id)
                        set_template(updated)
                        if st.session_state.get(KEY_ACTIVE_SHOT) == shot.id:
                            st.session_state[KEY_ACTIVE_SHOT] = (
                                updated.shots[0].id if updated.shots else None
                            )
                        st.rerun()
            with r5:
                st.caption(f"{len(shot.media)}圖 {len(shot.subtitles)}字")


# ---------------------------------------------------------------------------
# 單一媒體 / 字幕 / 音訊表單
# ---------------------------------------------------------------------------


def _render_media_editor(media: MediaElement, *, key_prefix: str) -> MediaElement:
    st.markdown(f"**圖片/視頻元素** `{media.id[-8:]}`")

    name = st.text_input(
        "顯示名稱",
        value=media.name,
        key=f"{key_prefix}_name",
        help="只是方便你辨識，例如「主畫面」「右上小圖」。",
    )
    media_type = render_media_type_select(
        media.media_type, key=f"{key_prefix}_type"
    )
    path = st.text_input(
        "素材檔名或代號",
        value=media.path,
        key=f"{key_prefix}_path",
        placeholder="例如 scene01_main.png（線上版不必填本機路徑）",
        help="雲端填代號即可；真正檔案之後由 Coze 或本機對應。",
    )
    is_pip = st.checkbox(
        "畫中畫（PIP）",
        value=media.is_pip,
        key=f"{key_prefix}_pip",
        help="勾選後通常會縮小疊在主畫面某一角。",
    )

    transform = render_transform_controls(
        media.transform, key_prefix=f"{key_prefix}_tf"
    )
    anim_in, anim_out = render_anim_selects(
        media.anim_in, media.anim_out, key_prefix=f"{key_prefix}_anim"
    )

    source_start = media.source_start
    volume = media.volume
    speed = media.speed
    if media_type == MediaType.video:
        st.caption("視頻專用參數")
        source_start = st.slider(
            "從素材第幾秒開始",
            min_value=0.0,
            max_value=60.0,
            value=float(media.source_start),
            step=0.1,
            key=f"{key_prefix}_ss",
            help="例如只要原片 2 秒以後的畫面。",
        )
        volume = st.slider(
            "原聲音量",
            min_value=0.0,
            max_value=1.0,
            value=float(media.volume),
            step=0.05,
            key=f"{key_prefix}_vol",
        )
        speed = st.slider(
            "播放速度",
            min_value=0.25,
            max_value=4.0,
            value=float(media.speed),
            step=0.05,
            key=f"{key_prefix}_spd",
            help="1.0=原速。",
        )

    return MediaElement(
        id=media.id,
        media_type=media_type,
        path=path.strip(),
        name=name.strip(),
        transform=transform,
        anim_in=anim_in,
        anim_out=anim_out,
        is_pip=is_pip,
        source_start=float(source_start),
        volume=float(volume),
        speed=float(speed),
    )


def _render_subtitle_editor(sub: SubtitleElement, *, key_prefix: str) -> SubtitleElement:
    st.markdown(f"**字幕** `{sub.id[-8:]}`")

    text = st.text_area(
        "字幕文字",
        value=sub.text,
        key=f"{key_prefix}_text",
        height=80,
        help="這句話會顯示在畫面上。可留空稍後再填。",
    )

    # 顏色：用下拉常用色 + 可自訂
    color_presets = {
        "白色": "#FFFFFF",
        "黑色": "#000000",
        "黃色": "#FFE66D",
        "紅色": "#FF4B4B",
        "青色": "#4ECDC4",
        "自訂": "custom",
    }
    inv = {v: k for k, v in color_presets.items() if v != "custom"}
    cur_color = (sub.color or "#FFFFFF").upper()
    color_label = inv.get(cur_color, "自訂")
    color_choice = st.selectbox(
        "文字顏色",
        options=list(color_presets.keys()),
        index=list(color_presets.keys()).index(color_label),
        key=f"{key_prefix}_color_sel",
        help="常用色直接選；要其他顏色選「自訂」。",
    )
    if color_choice == "自訂":
        color = st.text_input(
            "自訂顏色（#RRGGBB）",
            value=cur_color,
            key=f"{key_prefix}_color_custom",
        )
    else:
        color = color_presets[color_choice]

    stroke_presets = {
        "黑色描邊": "#000000",
        "白色描邊": "#FFFFFF",
        "無描邊": "none",
        "自訂": "custom",
    }
    cur_stroke = (sub.stroke_color or "#000000").upper()
    if float(sub.stroke_width) <= 0:
        stroke_label = "無描邊"
    else:
        stroke_label = {
            "#000000": "黑色描邊",
            "#FFFFFF": "白色描邊",
        }.get(cur_stroke, "自訂")
    stroke_choice = st.selectbox(
        "描邊",
        options=list(stroke_presets.keys()),
        index=list(stroke_presets.keys()).index(stroke_label),
        key=f"{key_prefix}_stroke_sel",
        help="描邊讓字在亮/暗背景都看得清楚。",
    )
    if stroke_choice == "無描邊":
        stroke_color = "#000000"
        stroke_width = 0.0
    elif stroke_choice == "自訂":
        stroke_color = st.text_input(
            "描邊顏色",
            value=cur_stroke,
            key=f"{key_prefix}_stroke_custom",
        )
        stroke_width = st.slider(
            "描邊粗細",
            0.0,
            12.0,
            float(sub.stroke_width) if sub.stroke_width > 0 else 2.0,
            0.5,
            key=f"{key_prefix}_sw",
        )
    else:
        stroke_color = stroke_presets[stroke_choice]
        stroke_width = st.slider(
            "描邊粗細",
            0.0,
            12.0,
            float(sub.stroke_width) if sub.stroke_width > 0 else 2.0,
            0.5,
            key=f"{key_prefix}_sw",
        )

    font_size = st.slider(
        "字級",
        min_value=16.0,
        max_value=120.0,
        value=min(max(float(sub.font_size), 16.0), 120.0),
        step=2.0,
        key=f"{key_prefix}_fs",
        help="數字越大字越大。短影音標題常用 48～72。",
    )

    # 字幕預設偏下方，scale 意義較小，仍保留位置
    transform = render_transform_controls(
        sub.transform,
        key_prefix=f"{key_prefix}_tf",
        show_scale=False,
        show_opacity=True,
        show_rotation=False,
    )
    anim_in, anim_out = render_anim_selects(
        sub.anim_in, sub.anim_out, key_prefix=f"{key_prefix}_anim"
    )

    # 正規化顏色
    color = color.strip().upper()
    if not color.startswith("#"):
        color = f"#{color}"
    stroke_color = stroke_color.strip().upper()
    if not stroke_color.startswith("#"):
        stroke_color = f"#{stroke_color}"

    return SubtitleElement(
        id=sub.id,
        text=text,
        transform=transform,
        font_size=float(font_size),
        color=color,
        stroke_color=stroke_color,
        stroke_width=float(stroke_width),
        anim_in=anim_in,
        anim_out=anim_out,
    )


def _render_audio_editor(audio: AudioElement, *, key_prefix: str) -> AudioElement:
    st.markdown(f"**配音/音效** `{audio.id[-8:]}`")
    name = st.text_input(
        "顯示名稱",
        value=audio.name,
        key=f"{key_prefix}_name",
        help="例如「旁白」「誰音效」。",
    )
    path = st.text_input(
        "音訊檔名或代號",
        value=audio.path,
        key=f"{key_prefix}_path",
        placeholder="例如 vo_01.mp3",
        help="線上版填代號即可。",
    )
    volume = st.slider(
        "音量",
        0.0,
        1.0,
        float(audio.volume),
        0.05,
        key=f"{key_prefix}_vol",
    )
    start_offset = st.slider(
        "延遲開始（秒）",
        0.0,
        10.0,
        float(audio.start_offset),
        0.1,
        key=f"{key_prefix}_off",
        help="此分鏡開始後幾秒才播這段音訊。",
    )
    c1, c2 = st.columns(2)
    with c1:
        fade_in = st.slider(
            "淡入（秒）",
            0.0,
            3.0,
            float(audio.fade_in),
            0.1,
            key=f"{key_prefix}_fi",
        )
    with c2:
        fade_out = st.slider(
            "淡出（秒）",
            0.0,
            3.0,
            float(audio.fade_out),
            0.1,
            key=f"{key_prefix}_fo",
        )
    return AudioElement(
        id=audio.id,
        path=path.strip(),
        name=name.strip(),
        volume=float(volume),
        start_offset=float(start_offset),
        fade_in=float(fade_in),
        fade_out=float(fade_out),
    )


# ---------------------------------------------------------------------------
# 分鏡詳細設定
# ---------------------------------------------------------------------------


def render_shot_detail_panel() -> None:
    """編輯目前選中的分鏡。"""
    template = get_template()
    active_id = _ensure_active_shot(template)
    if not active_id:
        return

    shot = next((s for s in template.shots if s.id == active_id), None)
    if shot is None:
        st.warning("找不到選中的分鏡。")
        return

    st.subheader(f"編輯分鏡：{shot.name}")
    st.caption(f"分鏡 ID：`{shot.id}`（系統用，不用背）")

    # --- 基本 ---
    with st.expander("① 基本設定", expanded=True):
        name = st.text_input(
            "分鏡名稱",
            value=shot.name,
            key=f"shot_{shot.id}_name",
            help="方便辨識，例如「開頭鈎子」「痛點1」。",
        )
        duration = st.slider(
            "時長（秒）",
            min_value=0.5,
            max_value=15.0,
            value=min(max(float(shot.duration), 0.5), 15.0),
            step=0.1,
            key=f"shot_{shot.id}_dur",
            help="常見短影音分鏡約 2～4 秒。",
        )
        is_hook = st.checkbox(
            "標記為「開頭鈎子」",
            value=shot.is_hook,
            key=f"shot_{shot.id}_hook",
            help="通常整支影片只有一個鈎子分鏡；勾選後會自動取消其他分鏡的鈎子標記。",
        )

    # --- 媒體 ---
    media_list = list(shot.media)
    with st.expander(f"② 圖片 / 視頻（{len(media_list)} 個）", expanded=True):
        st.caption("一個分鏡可以有多張圖，例如主畫面 + 畫中畫。")
        if st.button("➕ 新增圖片/視頻", key=f"add_media_{shot.id}"):
            media_list.append(
                MediaElement(
                    name=f"素材{len(media_list) + 1}",
                    media_type=MediaType.image,
                    transform=Transform2D(
                        position_preset=PositionPreset.center
                    ).apply_preset(),
                )
            )
            updated_shot = shot.model_copy(update={"media": media_list})
            set_template(_replace_shot(template, updated_shot))
            st.rerun()

        new_media: list[MediaElement] = []
        for m in media_list:
            with st.container(border=True):
                edited = _render_media_editor(m, key_prefix=f"m_{m.id}")
                if st.button("🗑 刪除此素材", key=f"rm_m_{m.id}"):
                    kept = [x for x in media_list if x.id != m.id]
                    set_template(
                        _replace_shot(template, shot.model_copy(update={"media": kept}))
                    )
                    st.rerun()
                new_media.append(edited)

    # --- 字幕 ---
    sub_list = list(shot.subtitles)
    with st.expander(f"③ 字幕（{len(sub_list)} 句）", expanded=True):
        st.caption("可多句，例如主標 + 副標。")
        if st.button("➕ 新增字幕", key=f"add_sub_{shot.id}"):
            sub_list.append(
                SubtitleElement(
                    text="",
                    transform=Transform2D(
                        y=-0.75,
                        position_preset=PositionPreset.bottom_center,
                    ).apply_preset(),
                )
            )
            updated_shot = shot.model_copy(update={"subtitles": sub_list})
            set_template(_replace_shot(template, updated_shot))
            st.rerun()

        new_subs: list[SubtitleElement] = []
        for s in sub_list:
            with st.container(border=True):
                edited = _render_subtitle_editor(s, key_prefix=f"s_{s.id}")
                if st.button("🗑 刪除此字幕", key=f"rm_s_{s.id}"):
                    kept = [x for x in sub_list if x.id != s.id]
                    set_template(
                        _replace_shot(
                            template, shot.model_copy(update={"subtitles": kept})
                        )
                    )
                    st.rerun()
                new_subs.append(edited)

    # --- 音訊 ---
    audio_list = list(shot.audio)
    with st.expander(f"④ 配音 / 音效（{len(audio_list)} 個）", expanded=False):
        st.caption("先做基本欄位；之後可再加強。")
        if st.button("➕ 新增配音/音效", key=f"add_au_{shot.id}"):
            audio_list.append(AudioElement(name=f"音訊{len(audio_list) + 1}"))
            updated_shot = shot.model_copy(update={"audio": audio_list})
            set_template(_replace_shot(template, updated_shot))
            st.rerun()

        new_audio: list[AudioElement] = []
        for a in audio_list:
            with st.container(border=True):
                edited = _render_audio_editor(a, key_prefix=f"a_{a.id}")
                if st.button("🗑 刪除此音訊", key=f"rm_a_{a.id}"):
                    kept = [x for x in audio_list if x.id != a.id]
                    set_template(
                        _replace_shot(template, shot.model_copy(update={"audio": kept}))
                    )
                    st.rerun()
                new_audio.append(edited)


    # --- 套用 ---
    st.divider()
    if st.button("💾 套用此分鏡設定", type="primary", use_container_width=True):
        updated_shot = Shot(
            id=shot.id,
            name=(name or "").strip() or "未命名分鏡",
            duration=float(duration),
            is_hook=bool(is_hook),
            media=new_media,
            subtitles=new_subs,
            audio=new_audio,
        )
        updated = _replace_shot(template, updated_shot)
        if is_hook:
            updated = _set_hook(updated, shot.id, True)
        else:
            updated = _set_hook(updated, shot.id, False)
        set_template(updated)
        st.success(f"已套用分鏡：{updated_shot.name}")
        st.rerun()


def render_shot_manager_page() -> None:
    """分鏡管理整頁入口。"""
    st.header("分鏡管理")
    st.caption(
        "先在列表選分鏡，再在下方改細節。"
        "改完記得按「套用此分鏡設定」。"
    )
    render_shot_list_panel()
    st.divider()
    render_shot_detail_panel()
