"""
剪映小助手 — 模板 / Streamlit 介面用的資料結構（Pydantic）。

白話說明：
- 這份模型比「Coze 簡單 Scene JSON」更細，專給本地網頁設定介面使用
- 之後可再轉成 Coze 寬鬆格式，或轉成 pyJianYingDraft 草稿
- 階段 1 先把「形狀」定好；分鏡細部 UI、預覽會在階段 2/3 接上

設計原則：
1. 能選就選：枚舉 + 預設值，少用手打
2. 欄位都有中文 description，方便介面顯示說明
3. 允許空路徑（模板可先存結構，素材之後再補）
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# 小工具：產生短 ID
# ---------------------------------------------------------------------------


def new_id(prefix: str = "id") -> str:
    """產生簡短唯一 ID，例如 media_a1b2c3。"""
    return f"{prefix}_{uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# 枚舉：下拉選單會直接用這些值
# ---------------------------------------------------------------------------


class MediaType(str, Enum):
    """素材類型。"""

    image = "image"  # 圖片
    video = "video"  # 視頻


class PositionPreset(str, Enum):
    """
    位置快捷選項（按了就自動填 x/y）。

    座標系（跟剪映類似）：
    - 畫面中心 = (0, 0)
    - x 正值往右、負值往左
    - y 正值往上、負值往下
    """

    center = "center"  # 置中
    top_center = "top_center"  # 上方置中
    bottom_center = "bottom_center"  # 底部置中
    top_left = "top_left"  # 左上
    top_right = "top_right"  # 右上
    bottom_left = "bottom_left"  # 左下
    bottom_right = "bottom_right"  # 右下
    left_center = "left_center"  # 左側置中
    right_center = "right_center"  # 右側置中
    custom = "custom"  # 自訂（用滑桿調 x/y）


class AnchorPoint(str, Enum):
    """對齊點：元素以哪個角落/中心當錨點。"""

    center = "center"
    top_left = "top_left"
    top_right = "top_right"
    bottom_left = "bottom_left"
    bottom_right = "bottom_right"


class AnimIn(str, Enum):
    """入場動畫（階段 1 先列常用項，之後可對齊剪映實際名稱）。"""

    none = "none"  # 無
    fade_in = "fade_in"  # 淡入
    zoom_in = "zoom_in"  # 放大進入
    slide_up = "slide_up"  # 上滑進入
    slide_down = "slide_down"  # 下滑進入
    slide_left = "slide_left"  # 左滑進入
    slide_right = "slide_right"  # 右滑進入
    bounce_in = "bounce_in"  # 彈入


class AnimOut(str, Enum):
    """出場動畫。"""

    none = "none"  # 無
    fade_out = "fade_out"  # 淡出
    zoom_out = "zoom_out"  # 縮小離開
    slide_up = "slide_up"  # 上滑離開
    slide_down = "slide_down"  # 下滑離開
    slide_left = "slide_left"  # 左滑離開
    slide_right = "slide_right"  # 右滑離開


# 位置快捷 → 實際座標
POSITION_PRESET_XY: dict[PositionPreset, tuple[float, float]] = {
    PositionPreset.center: (0.0, 0.0),
    PositionPreset.top_center: (0.0, 0.7),
    PositionPreset.bottom_center: (0.0, -0.7),
    PositionPreset.top_left: (-0.55, 0.7),
    PositionPreset.top_right: (0.55, 0.7),
    PositionPreset.bottom_left: (-0.55, -0.7),
    PositionPreset.bottom_right: (0.55, -0.7),
    PositionPreset.left_center: (-0.55, 0.0),
    PositionPreset.right_center: (0.55, 0.0),
    PositionPreset.custom: (0.0, 0.0),
}

# 給 Streamlit 顯示用的中文標籤
POSITION_PRESET_LABELS: dict[str, str] = {
    "center": "置中",
    "top_center": "上方置中",
    "bottom_center": "底部置中",
    "top_left": "左上",
    "top_right": "右上",
    "bottom_left": "左下",
    "bottom_right": "右下",
    "left_center": "左側置中",
    "right_center": "右側置中",
    "custom": "自訂位置",
}

ANIM_IN_LABELS: dict[str, str] = {
    "none": "無動畫",
    "fade_in": "淡入",
    "zoom_in": "放大進入",
    "slide_up": "上滑進入",
    "slide_down": "下滑進入",
    "slide_left": "左滑進入",
    "slide_right": "右滑進入",
    "bounce_in": "彈入",
}

ANIM_OUT_LABELS: dict[str, str] = {
    "none": "無動畫",
    "fade_out": "淡出",
    "zoom_out": "縮小離開",
    "slide_up": "上滑離開",
    "slide_down": "下滑離開",
    "slide_left": "左滑離開",
    "slide_right": "右滑離開",
}

MEDIA_TYPE_LABELS: dict[str, str] = {
    "image": "圖片",
    "video": "視頻",
}

ANCHOR_LABELS: dict[str, str] = {
    "center": "中心",
    "top_left": "左上角",
    "top_right": "右上角",
    "bottom_left": "左下角",
    "bottom_right": "右下角",
}

# 常用解析度（寬×高）
RESOLUTION_PRESETS: dict[str, tuple[int, int]] = {
    "直式 1080×1920（推薦短影音）": (1080, 1920),
    "直式 720×1280": (720, 1280),
    "直式 1080×2340": (1080, 2340),
    "橫式 1920×1080": (1920, 1080),
    "正方形 1080×1080": (1080, 1080),
    "自訂": (0, 0),  # 介面另外用數字輸入
}


# ---------------------------------------------------------------------------
# 共用：位置與變形
# ---------------------------------------------------------------------------


class Transform2D(BaseModel):
    """
    2D 位置與變形參數。

    白話：決定「放哪裡、多大、多透明、轉幾度」。
    """

    x: float = Field(
        0.0,
        ge=-1.5,
        le=1.5,
        description="水平位置：0=中間，正=右，負=左",
    )
    y: float = Field(
        0.0,
        ge=-1.5,
        le=1.5,
        description="垂直位置：0=中間，正=上，負=下",
    )
    scale: float = Field(
        1.0,
        gt=0.0,
        le=5.0,
        description="縮放：1.0=原大小，0.5=一半，2.0=兩倍",
    )
    opacity: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="透明度：1=完全不透明，0=完全透明",
    )
    rotation: float = Field(
        0.0,
        ge=-180.0,
        le=180.0,
        description="旋轉角度（度），正值順時針",
    )
    anchor: AnchorPoint = Field(
        AnchorPoint.center,
        description="對齊點：以元素的哪個點對齊畫面座標",
    )
    position_preset: PositionPreset = Field(
        PositionPreset.center,
        description="位置快捷；選 custom 時用 x/y 滑桿",
    )

    def apply_preset(self) -> "Transform2D":
        """若不是自訂，把 preset 對應的 x/y 寫入。"""
        if self.position_preset != PositionPreset.custom:
            px, py = POSITION_PRESET_XY[self.position_preset]
            return self.model_copy(update={"x": px, "y": py})
        return self


# ---------------------------------------------------------------------------
# 元素：圖片/視頻、字幕、音訊
# ---------------------------------------------------------------------------


class MediaElement(BaseModel):
    """
    單一圖片或視頻元素（一個分鏡裡可以有多個，例如主畫面 + 畫中畫）。
    """

    id: str = Field(default_factory=lambda: new_id("media"), description="元素 ID")
    media_type: MediaType = Field(MediaType.image, description="素材類型：圖片或視頻")
    path: str = Field(
        "",
        description="素材檔名或代號；可先留空，之後由 Coze/本機對應真實檔",
    )

    name: str = Field("", description="顯示名稱（方便在列表辨識）")
    transform: Transform2D = Field(default_factory=Transform2D)
    anim_in: AnimIn = Field(AnimIn.none, description="入場動畫")
    anim_out: AnimOut = Field(AnimOut.none, description="出場動畫")
    is_pip: bool = Field(
        False,
        description="是否為畫中畫（PIP）：小畫面疊在主畫面上方",
    )
    # 視頻專用（圖片可忽略）
    source_start: float = Field(0.0, ge=0.0, description="從素材第幾秒開始取用")
    volume: float = Field(1.0, ge=0.0, le=1.0, description="原聲音量 0~1（僅視頻）")
    speed: float = Field(1.0, gt=0.0, le=4.0, description="播放速度（僅視頻）")


class SubtitleElement(BaseModel):
    """
    單一字幕句子（一個分鏡可有多句，例如主標 + 副標）。
    """

    id: str = Field(default_factory=lambda: new_id("sub"), description="字幕 ID")
    text: str = Field("", description="字幕文字內容")
    transform: Transform2D = Field(
        default_factory=lambda: Transform2D(
            y=-0.75,
            position_preset=PositionPreset.bottom_center,
        ),
        description="位置與縮放（字級另有 font_size）",
    )
    font_size: float = Field(
        48.0,
        gt=0,
        le=200,
        description="字級（介面用像素概念；之後轉剪映會再換算）",
    )
    color: str = Field(
        "#FFFFFF",
        description="文字顏色（十六進位，例如 #FFFFFF 白）",
    )
    stroke_color: str = Field(
        "#000000",
        description="描邊顏色（讓字在亮/暗背景都看得清）",
    )
    stroke_width: float = Field(
        2.0,
        ge=0.0,
        le=20.0,
        description="描邊粗細（0=不描邊）",
    )
    anim_in: AnimIn = Field(AnimIn.none, description="入場動畫")
    anim_out: AnimOut = Field(AnimOut.none, description="出場動畫")

    @field_validator("color", "stroke_color")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        """簡單檢查顏色格式。"""
        s = (v or "").strip()
        if not s.startswith("#"):
            s = f"#{s}"
        if len(s) not in (4, 7):  # #RGB 或 #RRGGBB
            raise ValueError(f"顏色格式不對：{v}（請用 #FFFFFF 這種）")
        return s.upper()


class AudioElement(BaseModel):
    """
    配音或音效（階段 1 先留基本欄位）。
    """

    id: str = Field(default_factory=lambda: new_id("audio"), description="音訊 ID")
    path: str = Field("", description="音訊檔名或素材代號（mp3/wav 等）")

    name: str = Field("", description="顯示名稱")
    volume: float = Field(1.0, ge=0.0, le=1.0, description="音量 0~1")
    start_offset: float = Field(
        0.0,
        ge=0.0,
        description="相對此分鏡開始後延遲幾秒再播放",
    )
    fade_in: float = Field(0.0, ge=0.0, description="淡入秒數")
    fade_out: float = Field(0.0, ge=0.0, description="淡出秒數")


# ---------------------------------------------------------------------------
# 分鏡
# ---------------------------------------------------------------------------


class Shot(BaseModel):
    """
    一個分鏡（時間軸上的一段）。

    白話：影片由很多分鏡串起來；第一個通常是「開頭鈎子」。
    """

    id: str = Field(default_factory=lambda: new_id("shot"), description="分鏡 ID")
    name: str = Field("未命名分鏡", description="分鏡名稱")
    duration: float = Field(
        3.0,
        gt=0.0,
        le=120.0,
        description="此分鏡時長（秒），常見 2～4 秒",
    )
    is_hook: bool = Field(
        False,
        description="是否為開頭鈎子（通常只有第一個分鏡為 True）",
    )
    media: list[MediaElement] = Field(
        default_factory=list,
        description="圖片/視頻元素列表",
    )
    subtitles: list[SubtitleElement] = Field(
        default_factory=list,
        description="字幕列表",
    )
    audio: list[AudioElement] = Field(
        default_factory=list,
        description="配音/音效列表",
    )


# ---------------------------------------------------------------------------
# 全域設定
# ---------------------------------------------------------------------------


class GlobalSettings(BaseModel):
    """
    整支影片共用的設定（專案名稱、解析度、BGM、底圖、封面）。
    """

    project_name: str = Field(
        "未命名專案",
        min_length=1,
        description="專案名稱（之後也會當草稿名稱用）",
    )
    width: int = Field(1080, gt=0, le=7680, description="畫布寬度（像素）")
    height: int = Field(1920, gt=0, le=7680, description="畫布高度（像素）")
    fps: int = Field(30, gt=0, le=120, description="幀率（每秒幾格）")

    # 背景音樂（線上版填檔名/代號；本機生成草稿時再對應真實檔案）
    bgm_path: str = Field(
        "",
        description="BGM 檔名或素材代號（可留空；非本機絕對路徑）",
    )
    bgm_volume: float = Field(
        0.35,
        ge=0.0,
        le=1.0,
        description="BGM 音量：建議 0.2～0.5，避免蓋過配音",
    )
    bgm_fade_in: float = Field(0.5, ge=0.0, le=10.0, description="BGM 淡入秒數")
    bgm_fade_out: float = Field(0.5, ge=0.0, le=10.0, description="BGM 淡出秒數")

    # 背景底圖（整支影片底下那層）
    background_image: str = Field(
        "",
        description="底圖檔名或素材代號（可留空）",
    )
    background_opacity: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="背景底圖透明度：1=完全顯示",
    )

    # 封面
    cover_image: str = Field(
        "",
        description="封面檔名或素材代號（可留空）",
    )

    cover_duration: float = Field(
        0.5,
        ge=0.1,
        le=5.0,
        description="封面停留秒數（短影音常見約 0.5 秒）",
    )

    @property
    def resolution_label(self) -> str:
        """回傳接近的預設解析度標籤，找不到就回「自訂」。"""
        for label, (w, h) in RESOLUTION_PRESETS.items():
            if label == "自訂":
                continue
            if w == self.width and h == self.height:
                return label
        return "自訂"


# ---------------------------------------------------------------------------
# 完整模板文件（可存 JSON）
# ---------------------------------------------------------------------------


class ProjectTemplate(BaseModel):
    """
    完整專案模板：全域設定 + 所有分鏡。

    可存成 JSON，之後用 template_id（例如 A01）快速套用。
    """

    schema_version: str = Field(
        "1.0",
        description="模板格式版本，方便之後升級相容",
    )
    template_id: Optional[str] = Field(
        None,
        description="模板短代號，例如 A01；可選",
    )
    template_name: str = Field(
        "未命名模板",
        description="模板顯示名稱",
    )
    description: str = Field("", description="模板說明（可選）")
    global_settings: GlobalSettings = Field(default_factory=GlobalSettings)
    shots: list[Shot] = Field(
        default_factory=list,
        description="分鏡列表（可為空，階段 2 再大量新增）",
    )

    @model_validator(mode="after")
    def ensure_unique_shot_ids(self) -> "ProjectTemplate":
        ids = [s.id for s in self.shots]
        if len(ids) != len(set(ids)):
            raise ValueError("分鏡 id 不可重複")
        return self

    def total_duration(self) -> float:
        """所有分鏡時長加總（不含封面）。"""
        return sum(s.duration for s in self.shots)

    def model_dump_json_pretty(self) -> str:
        """輸出漂亮縮排的 JSON 字串（UTF-8 友善）。"""
        return self.model_dump_json(indent=2, exclude_none=False)


# ---------------------------------------------------------------------------
# 工廠：建立預設空白專案 / 開頭鈎子分鏡
# ---------------------------------------------------------------------------


def create_default_hook_shot() -> Shot:
    """建立一個預設的「開頭鈎子」分鏡。"""
    media = MediaElement(
        name="鈎子主畫面",
        media_type=MediaType.image,
        transform=Transform2D(position_preset=PositionPreset.center).apply_preset(),
        anim_in=AnimIn.zoom_in,
        anim_out=AnimOut.fade_out,
    )
    subtitle = SubtitleElement(
        text="這裡填開頭鈎子文案",
        transform=Transform2D(
            y=-0.75,
            position_preset=PositionPreset.bottom_center,
        ).apply_preset(),
        font_size=56.0,
        anim_in=AnimIn.fade_in,
    )
    return Shot(
        name="開頭鈎子",
        duration=3.0,
        is_hook=True,
        media=[media],
        subtitles=[subtitle],
        audio=[],
    )


def create_empty_shot(index: int = 1, *, is_hook: bool = False) -> Shot:
    """建立一般空白分鏡。"""
    name = "開頭鈎子" if is_hook else f"分鏡 {index}"
    media = MediaElement(
        name=f"{name}-主畫面",
        media_type=MediaType.image,
        transform=Transform2D().apply_preset(),
    )
    subtitle = SubtitleElement(
        text="",
        transform=Transform2D(
            y=-0.75,
            position_preset=PositionPreset.bottom_center,
        ).apply_preset(),
    )
    return Shot(
        name=name,
        duration=3.0,
        is_hook=is_hook,
        media=[media],
        subtitles=[subtitle],
        audio=[],
    )


def create_default_template(
    project_name: str = "未命名專案",
    *,
    with_hook: bool = True,
) -> ProjectTemplate:
    """
    建立一份可直接在 Streamlit 使用的預設模板。

    with_hook=True 時會自動放一個開頭鈎子分鏡，方便使用者立刻改。
    """
    shots: list[Shot] = []
    if with_hook:
        shots.append(create_default_hook_shot())

    return ProjectTemplate(
        template_name=f"{project_name} 模板",
        global_settings=GlobalSettings(project_name=project_name),
        shots=shots,
    )


def template_from_dict(data: dict[str, Any]) -> ProjectTemplate:
    """從 dict 驗證並建立模板（寬鬆入口，之後接 Coze 也可先走這層）。"""
    return ProjectTemplate.model_validate(data)


def template_to_dict(template: ProjectTemplate) -> dict[str, Any]:
    """模板 → 一般 dict（方便 session_state / JSON 存檔）。"""
    return template.model_dump(mode="json")
