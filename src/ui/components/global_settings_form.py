"""
全域設定表單（線上版）。

白話說明：
- 這裡管「整支影片共用」的東西：名稱、解析度、BGM、底圖、封面
- 部署在 Streamlit Cloud 時無法讀你電腦路徑，所以素材用「檔名/代號」註記
- 真正的檔案之後由 Coze 產出，或在本機對應路徑再接剪映
"""

from __future__ import annotations

import streamlit as st

from src.template_models import RESOLUTION_PRESETS, GlobalSettings
from src.ui.session_state import get_template, set_template


def _asset_hint(value: str, kind: str) -> str:
    """素材欄位的白話提示（不做本機檔案檢查）。"""
    if not value or not str(value).strip():
        return f"尚未填寫{kind}（可先空白，之後再補）"
    return f"已記錄{kind}代號：`{value.strip()}`（實際檔案之後再對應）"


def render_global_settings() -> None:
    """渲染「全域設定」整頁。"""
    template = get_template()
    g: GlobalSettings = template.global_settings

    st.header("全域設定")
    st.caption(
        "設定整支影片共用的參數。"
        "資料暫存在這次瀏覽器連線中；正式保存靠之後「下載 JSON → Google 雲端硬碟」。"
    )

    st.info(
        "📱 **線上版說明**：網站跑在雲端，讀不到你手機/電腦的資料夾。"
        "BGM、底圖、封面請填「檔名或素材代號」（例如 `bgm_心理學01.mp3`），"
        "真正檔案之後由 Coze 產出或本機對應。"
    )

    # ------------------------------------------------------------------
    # 1. 專案基本
    # ------------------------------------------------------------------
    st.subheader("1. 專案基本")

    project_name = st.text_input(
        "專案名稱",
        value=g.project_name,
        help="會顯示在介面標題，之後也會當剪映草稿名稱。建議用好辨識的中文。",
    )

    labels = list(RESOLUTION_PRESETS.keys())
    current_label = g.resolution_label
    if current_label not in labels:
        current_label = "自訂"
    try:
        default_idx = labels.index(current_label)
    except ValueError:
        default_idx = 0

    res_label = st.selectbox(
        "解析度（畫面大小）",
        options=labels,
        index=default_idx,
        help="短影音最常用「直式 1080×1920」。選「自訂」可自己填寬高。",
    )

    if res_label == "自訂":
        col_w, col_h = st.columns(2)
        with col_w:
            width = st.number_input(
                "寬度（像素）",
                min_value=1,
                max_value=7680,
                value=int(g.width),
                step=2,
                help="畫面有多寬，單位是像素。",
            )
        with col_h:
            height = st.number_input(
                "高度（像素）",
                min_value=1,
                max_value=7680,
                value=int(g.height),
                step=2,
                help="畫面有多高。直式短影音高度會大於寬度。",
            )
    else:
        width, height = RESOLUTION_PRESETS[res_label]
        st.info(f"目前解析度：**{width} × {height}**")

    fps = st.select_slider(
        "幀率 FPS（每秒幾格畫面）",
        options=[24, 25, 30, 50, 60],
        value=g.fps if g.fps in (24, 25, 30, 50, 60) else 30,
        help="一般短影音用 30 就夠。越高越順，但檔案也越大。",
    )

    # ------------------------------------------------------------------
    # 2. 背景音樂
    # ------------------------------------------------------------------
    st.subheader("2. 背景音樂（BGM）")
    st.caption("整支影片底下的音樂參數。音量建議比配音小，才不會搶戲。")

    use_bgm = st.checkbox(
        "使用背景音樂",
        value=bool(g.bgm_path),
        help="關掉後會清空 BGM 代號（可再重新開啟填寫）。",
    )

    bgm_path = g.bgm_path
    bgm_volume = g.bgm_volume
    bgm_fade_in = g.bgm_fade_in
    bgm_fade_out = g.bgm_fade_out

    if use_bgm:
        bgm_path = st.text_input(
            "BGM 檔名或素材代號",
            value=g.bgm_path,
            placeholder="例如 bgm_心理學01.mp3 或 materials/bgm/01.mp3",
            help=(
                "線上版請填「之後會用的檔名/代號」，不是電腦 C:\\ 路徑。"
                "真正檔案由 Coze 或本機素材資料夾提供。"
            ),
        )
        st.caption(_asset_hint(bgm_path, "BGM"))

        bgm_volume = st.slider(
            "BGM 音量",
            min_value=0.0,
            max_value=1.0,
            value=float(g.bgm_volume),
            step=0.05,
            help="0=靜音，1=最大。配音旁白時建議 0.2～0.4。",
        )

        c1, c2 = st.columns(2)
        with c1:
            bgm_fade_in = st.slider(
                "淡入（秒）",
                min_value=0.0,
                max_value=5.0,
                value=float(g.bgm_fade_in),
                step=0.1,
                help="開頭音樂慢慢變大聲的時間。",
            )
        with c2:
            bgm_fade_out = st.slider(
                "淡出（秒）",
                min_value=0.0,
                max_value=5.0,
                value=float(g.bgm_fade_out),
                step=0.1,
                help="結尾音樂慢慢變小聲的時間。",
            )
    else:
        bgm_path = ""

    # ------------------------------------------------------------------
    # 3. 背景底圖
    # ------------------------------------------------------------------
    st.subheader("3. 背景底圖")
    st.caption("整支影片最底下一層的圖（可選）。分鏡圖片會疊在它上面。")

    use_bg = st.checkbox(
        "使用背景底圖",
        value=bool(g.background_image),
        help="例如純色、漸層或品牌底圖。",
    )

    background_image = g.background_image
    background_opacity = g.background_opacity

    if use_bg:
        background_image = st.text_input(
            "底圖檔名或素材代號",
            value=g.background_image,
            placeholder="例如 bg_dark.png 或 materials/bg/default.png",
            help="線上版填檔名/代號即可，不必是本機完整路徑。",
        )
        st.caption(_asset_hint(background_image, "底圖"))

        background_opacity = st.slider(
            "底圖透明度",
            min_value=0.0,
            max_value=1.0,
            value=float(g.background_opacity),
            step=0.05,
            help="1=完全清楚，0=完全看不見。",
        )
    else:
        background_image = ""

    # ------------------------------------------------------------------
    # 4. 封面
    # ------------------------------------------------------------------
    st.subheader("4. 封面")
    st.caption("影片最前面那一瞬間的封面圖（短影音常見約 0.5 秒）。")

    use_cover = st.checkbox(
        "使用封面",
        value=bool(g.cover_image),
        help="有封面時，草稿開頭會先顯示這張圖。",
    )

    cover_image = g.cover_image
    cover_duration = g.cover_duration

    if use_cover:
        cover_image = st.text_input(
            "封面檔名或素材代號",
            value=g.cover_image,
            placeholder="例如 cover_01.png",
            help="建議之後實際圖片尺寸與解析度一致（例如 1080×1920）。",
        )
        st.caption(_asset_hint(cover_image, "封面"))

        cover_duration = st.slider(
            "封面時長（秒）",
            min_value=0.1,
            max_value=3.0,
            value=float(g.cover_duration),
            step=0.1,
            help="封面要停留多久。0.5 秒很常見。",
        )
    else:
        cover_image = ""

    # ------------------------------------------------------------------
    # 儲存到 session
    # ------------------------------------------------------------------
    st.divider()

    col_save, col_reset = st.columns(2)
    with col_save:
        if st.button("💾 套用全域設定", type="primary", use_container_width=True):
            name = (project_name or "").strip() or "未命名專案"
            new_global = GlobalSettings(
                project_name=name,
                width=int(width),
                height=int(height),
                fps=int(fps),
                bgm_path=bgm_path.strip() if use_bgm else "",
                bgm_volume=float(bgm_volume),
                bgm_fade_in=float(bgm_fade_in),
                bgm_fade_out=float(bgm_fade_out),
                background_image=background_image.strip() if use_bg else "",
                background_opacity=float(background_opacity),
                cover_image=cover_image.strip() if use_cover else "",
                cover_duration=float(cover_duration),
            )
            updated = template.model_copy(
                update={
                    "global_settings": new_global,
                    "template_name": f"{name} 模板",
                }
            )
            set_template(updated)
            st.success(f"已套用全域設定：【{name}】{width}×{height} @ {fps}fps")
            st.rerun()

    with col_reset:
        if st.button("↩ 重新整理表單", use_container_width=True):
            st.rerun()

    # ------------------------------------------------------------------
    # 目前狀態摘要
    # ------------------------------------------------------------------
    st.divider()
    st.subheader("目前已套用的全域設定（摘要）")
    tg = get_template().global_settings
    c1, c2, c3 = st.columns(3)
    c1.metric("專案名稱", tg.project_name)
    c2.metric("解析度", f"{tg.width}×{tg.height}")
    c3.metric("FPS", str(tg.fps))

    c4, c5, c6 = st.columns(3)
    c4.metric("BGM", "有" if tg.bgm_path else "無")
    c5.metric("底圖", "有" if tg.background_image else "無")
    c6.metric("封面", f"{tg.cover_duration}s" if tg.cover_image else "無")
