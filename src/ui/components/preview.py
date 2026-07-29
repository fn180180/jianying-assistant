"""
9:16 可視化預覽。

白話：
- 不求 100% 等於剪映，只幫你看「圖大概在哪、字幕大概在哪」
- 用 HTML/CSS 畫，不需額外套件，雲端也好部署
"""

from __future__ import annotations

import html
import streamlit as st

from src.template_models import ProjectTemplate, Shot
from src.ui.session_state import KEY_ACTIVE_SHOT, get_template


def _xy_to_css_percent(x: float, y: float) -> tuple[float, float]:
    """
    剪映式座標 → CSS 百分比（以中心為錨）。

    x: 0 中、正右、負左
    y: 0 中、正上、負下
    """
    # 約略對應：±1 ≈ 靠近邊緣
    left = 50.0 + float(x) * 42.0
    top = 50.0 - float(y) * 42.0
    left = max(2.0, min(98.0, left))
    top = max(2.0, min(98.0, top))
    return left, top


def _build_shot_preview_html(
    shot: Shot,
    *,
    canvas_w: int,
    canvas_h: int,
    max_display_h: int = 520,
) -> str:
    """組出單一預覽畫面的 HTML。"""
    # 依比例縮放顯示高度
    aspect = canvas_w / max(canvas_h, 1)
    display_h = max_display_h
    display_w = int(display_h * aspect)
    # 直式時寬度不要太寬（手機友善）
    if display_w > 320:
        display_w = 320
        display_h = int(display_w / aspect)

    layers: list[str] = []

    # 背景格線
    layers.append(
        """
        <div style="
          position:absolute; inset:0;
          background:
            linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px) 0 0 / 100% 10%,
            linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px) 0 0 / 10% 100%,
            #1a1d24;
        "></div>
        """
    )

    # 媒體區塊
    for i, m in enumerate(shot.media):
        left, top = _xy_to_css_percent(m.transform.x, m.transform.y)
        scale = max(0.15, min(2.5, float(m.transform.scale)))
        opacity = max(0.15, min(1.0, float(m.transform.opacity)))
        rot = float(m.transform.rotation)
        w = 38 * scale if m.is_pip else 70 * min(scale, 1.4)
        h = 22 * scale if m.is_pip else 40 * min(scale, 1.4)
        label = html.escape(m.name or m.path or f"素材{i+1}")
        pip = "PIP " if m.is_pip else ""
        kind = "視頻" if m.media_type.value == "video" else "圖片"
        layers.append(
            f"""
            <div title="{label}" style="
              position:absolute;
              left:{left}%; top:{top}%;
              width:{w}%; height:{h}%;
              transform: translate(-50%, -50%) rotate({rot}deg);
              opacity:{opacity};
              background: {'#3d5a80' if m.is_pip else '#4a5568'};
              border: 2px solid {'#ffd166' if m.is_pip else '#a0aec0'};
              border-radius: 8px;
              display:flex; align-items:center; justify-content:center;
              color:#f7fafc; font-size:11px; text-align:center;
              padding:4px; box-sizing:border-box;
              box-shadow: 0 2px 8px rgba(0,0,0,0.35);
            ">{pip}{kind}<br/>{label[:18]}</div>
            """
        )

    # 字幕
    for i, s in enumerate(shot.subtitles):
        left, top = _xy_to_css_percent(s.transform.x, s.transform.y)
        text = html.escape((s.text or f"字幕{i+1}").strip() or f"字幕{i+1}")
        color = html.escape(s.color or "#FFFFFF")
        stroke = html.escape(s.stroke_color or "#000000")
        sw = float(s.stroke_width or 0)
        # 字級映射到預覽字體
        fs = max(10, min(28, float(s.font_size) * 0.35))
        shadow = (
            f"-1px -1px 0 {stroke}, 1px -1px 0 {stroke}, -1px 1px 0 {stroke}, 1px 1px 0 {stroke}"
            if sw > 0
            else "none"
        )
        layers.append(
            f"""
            <div style="
              position:absolute;
              left:{left}%; top:{top}%;
              transform: translate(-50%, -50%);
              max-width: 88%;
              color:{color};
              font-size:{fs}px;
              font-weight:700;
              text-align:center;
              line-height:1.25;
              text-shadow:{shadow};
              padding:2px 6px;
              word-break: break-word;
            ">{text}</div>
            """
        )

    if not shot.media and not shot.subtitles:
        layers.append(
            """
            <div style="
              position:absolute; left:50%; top:50%;
              transform:translate(-50%,-50%);
              color:#a0aec0; font-size:13px; text-align:center;
            ">此分鏡尚無素材或字幕<br/>請先到「分鏡管理」新增</div>
            """
        )

    hook = "🪝 開頭鈎子 · " if shot.is_hook else ""
    title = html.escape(f"{hook}{shot.name} · {shot.duration:.1f}s")

    return f"""
    <div style="width:100%; display:flex; flex-direction:column; align-items:center;">
      <div style="color:#cbd5e0; font-size:13px; margin-bottom:8px; text-align:center;">
        {title}<br/>
        <span style="opacity:0.75">畫布 {canvas_w}×{canvas_h}（示意，非剪映實況）</span>
      </div>
      <div style="
        position:relative;
        width:{display_w}px;
        height:{display_h}px;
        max-width:100%;
        border-radius:12px;
        overflow:hidden;
        border:2px solid #4a5568;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35);
      ">
        {''.join(layers)}
      </div>
    </div>
    """


def render_preview_page() -> None:
    """可視化預覽整頁。"""
    st.header("可視化預覽")
    st.caption(
        "以直式 9:16 為主，粗略顯示目前分鏡的圖片與字幕位置。"
        "目的是幫你判斷排版是否合理，不必跟剪映一模一樣。"
    )

    template = get_template()
    g = template.global_settings

    if not template.shots:
        st.warning("還沒有分鏡。請先到「分鏡管理」新增。")
        return

    # 分鏡選擇
    labels = []
    id_by_label = {}
    for i, s in enumerate(template.shots):
        tag = "🪝 " if s.is_hook else ""
        lab = f"{i+1}. {tag}{s.name}（{s.duration:.1f}s）"
        labels.append(lab)
        id_by_label[lab] = s.id

    active = st.session_state.get(KEY_ACTIVE_SHOT)
    default_idx = 0
    for i, s in enumerate(template.shots):
        if s.id == active:
            default_idx = i
            break

    chosen = st.selectbox(
        "預覽哪個分鏡？",
        options=labels,
        index=default_idx,
        help="可切換查看不同分鏡的排版。",
    )
    shot_id = id_by_label[chosen]
    st.session_state[KEY_ACTIVE_SHOT] = shot_id
    shot = next(s for s in template.shots if s.id == shot_id)

    # 全域資訊小卡
    c1, c2, c3 = st.columns(3)
    c1.metric("專案", g.project_name)
    c2.metric("解析度", f"{g.width}×{g.height}")
    c3.metric("總時長", f"{template.total_duration():.1f}s")

    st.divider()
    html_block = _build_shot_preview_html(
        shot, canvas_w=g.width, canvas_h=g.height
    )
    st.markdown(html_block, unsafe_allow_html=True)

    with st.expander("圖例說明", expanded=False):
        st.markdown(
            """
- **灰色大方塊**：主畫面圖片/視頻  
- **黃邊較小方塊**：畫中畫（PIP）  
- **下方文字**：字幕（顏色/描邊大致反映設定）  
- 座標：畫面中心為 (0,0)，右為正 X，上為正 Y  
"""
        )

    # 簡易清單對照
    st.subheader("此分鏡元素清單")
    if shot.media:
        for m in shot.media:
            st.write(
                f"- 📷 **{m.name or m.id}** | "
                f"{'畫中畫' if m.is_pip else '主畫面'} | "
                f"位置快捷={m.transform.position_preset.value} | "
                f"scale={m.transform.scale:.2f}"
            )
    else:
        st.write("- （無圖片/視頻）")
    if shot.subtitles:
        for s in shot.subtitles:
            preview_text = (s.text or "（空）")[:40]
            st.write(
                f"- 💬 **{preview_text}** | "
                f"字級={s.font_size:.0f} | 色={s.color}"
            )
    else:
        st.write("- （無字幕）")
