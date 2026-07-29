"""
Scene JSON 的 Pydantic 模型（資料形狀定義 + 驗證）。

白話說明：
- Coze 最後會輸出一份 JSON
- 這份模型負責檢查「欄位對不對、型別對不對」
- 通過後，才能安全交給轉換器寫入剪映草稿
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class SceneMediaType(str, Enum):
    """單一場景的素材類型。"""

    video = "video"
    image = "image"


class BgmConfig(BaseModel):
    """背景音樂設定。"""

    path: str = Field(..., description="本地 BGM 音訊路徑（mp3/wav 等）")
    volume: float = Field(0.5, ge=0.0, le=1.0, description="音量 0~1")
    fade_in: str = Field("1s", description="淡入時長，例如 1s")
    fade_out: str = Field("1s", description="淡出時長，例如 1s")
    # 若未指定，轉換時會依整支影片時長自動裁切
    duration: Optional[float] = Field(
        None,
        gt=0,
        description="BGM 持續秒數；省略則跟整支草稿時長對齊",
    )


class SceneItem(BaseModel):
    """
    單一場景（時間軸上的一段）。

    最少需要 path；其餘可省略，由預設值補全。
    """

    id: Optional[str] = Field(None, description="場景 ID，方便除錯")
    type: Optional[SceneMediaType] = Field(
        None,
        description="video 或 image；省略時依副檔名自動判斷",
    )
    path: str = Field(..., description="本地影片或圖片路徑")
    duration: Optional[float] = Field(
        None,
        gt=0,
        description="時間軸上的持續秒數；影片可省略（用素材長度）",
    )
    source_start: float = Field(
        0.0,
        ge=0,
        description="從素材第幾秒開始取用（僅影片有意義）",
    )
    speed: float = Field(1.0, gt=0, description="播放速度，1.0 為原速")
    text: Optional[str] = Field(None, description="此段對應字幕；空字串等同沒有")
    volume: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="影片原聲音量 0~1（圖片無效）",
    )

    @field_validator("text")
    @classmethod
    def normalize_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None


class TextStyleConfig(BaseModel):
    """字幕樣式（階段 1 只做常用項）。"""

    size: float = Field(5.0, gt=0, description="字級（剪映內部單位）")
    color_r: float = Field(1.0, ge=0, le=1, description="紅 0~1")
    color_g: float = Field(1.0, ge=0, le=1, description="綠 0~1")
    color_b: float = Field(1.0, ge=0, le=1, description="藍 0~1")
    transform_y: float = Field(
        -0.8,
        description="垂直位置：0 中間，負值偏下，正值偏上",
    )
    auto_wrapping: bool = Field(True, description="是否自動換行")
    max_line_width: float = Field(0.8, gt=0, le=1, description="最大行寬佔畫面比例")


class ProjectConfig(BaseModel):
    """草稿專案層級設定。"""

    width: int = Field(1080, gt=0, description="畫布寬")
    height: int = Field(1920, gt=0, description="畫布高（預設直式短影音）")
    fps: int = Field(30, gt=0, le=120, description="幀率")


class SceneDocument(BaseModel):
    """
    完整 Scene JSON 文件根節點。

    Coze / 本地 CLI 都應輸出或讀取這個結構。
    """

    title: str = Field(..., min_length=1, description="草稿名稱（會出現在剪映列表）")
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    bgm: Optional[BgmConfig] = Field(None, description="可選背景音樂")
    text_style: TextStyleConfig = Field(default_factory=TextStyleConfig)
    scenes: list[SceneItem] = Field(..., min_length=1, description="場景列表，至少 1 個")
    # 轉換選項
    draft_folder: Optional[str] = Field(
        None,
        description="剪映草稿根目錄；省略則用環境變數或內建預設",
    )
    allow_replace: bool = Field(True, description="同名草稿是否覆寫")

    @model_validator(mode="after")
    def ensure_unique_ids_if_present(self) -> "SceneDocument":
        ids = [s.id for s in self.scenes if s.id]
        if len(ids) != len(set(ids)):
            raise ValueError("scenes 裡的 id 不可重複")
        return self


def load_scene_dict(data: dict[str, Any]) -> SceneDocument:
    """從 dict 驗證並建立 SceneDocument（不做預設值業務補全）。"""
    return SceneDocument.model_validate(data)


def load_scene_json_file(path: str | Path) -> SceneDocument:
    """從 JSON 檔讀取並驗證。"""
    import json

    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"找不到 Scene JSON：{p}")
    with p.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return load_scene_dict(raw)
