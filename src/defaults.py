"""
預設值補全（規則層）。

白話說明：
- Coze 可能只給「半成品」JSON（很多欄位省略）
- 這裡用規則把缺的欄位補齊，讓轉換器一定拿到完整資料
- 階段 1 不做 LLM；之後 Hybrid 的智能層可插在這之後
"""

from __future__ import annotations

import copy
import logging
import os
from pathlib import Path
from typing import Any, Optional

from .models import SceneDocument, SceneMediaType, load_scene_dict

logger = logging.getLogger(__name__)

# 圖片預設停留秒數
DEFAULT_IMAGE_DURATION_SEC = 3.0

# 常見副檔名 → 媒體類型
_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv"}
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def default_jianying_draft_folder() -> str:
    """
    取得本機剪映草稿根目錄。

    優先順序：
    1. 環境變數 JIANYING_DRAFT_FOLDER
    2. Windows 常見預設路徑
    """
    env = os.getenv("JIANYING_DRAFT_FOLDER", "").strip()
    if env:
        return env

    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        candidate = Path(local) / "JianyingPro" / "User Data" / "Projects" / "com.lveditor.draft"
        if candidate.is_dir():
            return str(candidate)

    # 最後退回常見路徑字串（即使資料夾尚不存在，也給出明確位置）
    home = Path.home()
    return str(
        home
        / "AppData"
        / "Local"
        / "JianyingPro"
        / "User Data"
        / "Projects"
        / "com.lveditor.draft"
    )


def detect_media_type(path: str) -> SceneMediaType:
    """依副檔名判斷 video / image。"""
    ext = Path(path).suffix.lower()
    if ext in _VIDEO_EXTS:
        return SceneMediaType.video
    if ext in _IMAGE_EXTS:
        return SceneMediaType.image
    raise ValueError(
        f"無法從副檔名判斷素材類型：{path}。"
        f"請在 scene 加上 type=video 或 type=image，"
        f"或使用常見副檔名（mp4/mov/jpg/png...）"
    )


def resolve_path(path: str, base_dir: Optional[Path] = None) -> str:
    """
    把相對路徑轉成絕對路徑。

    - 已是絕對路徑：原樣返回（正規化）
    - 相對路徑：相對 base_dir（或目前工作目錄）
    """
    p = Path(path)
    if p.is_absolute():
        return str(p.resolve())
    base = base_dir if base_dir is not None else Path.cwd()
    return str((base / p).resolve())


def apply_defaults(
    data: dict[str, Any] | SceneDocument,
    *,
    base_dir: Optional[str | Path] = None,
    check_files_exist: bool = False,
) -> SceneDocument:
    """
    補全預設值並回傳完整的 SceneDocument。

    參數：
    - data: 原始 dict 或已驗證的模型
    - base_dir: 解析相對路徑的基準目錄（通常是 JSON 所在資料夾）
    - check_files_exist: True 時若素材檔不存在就報錯（正式轉換建議開）
    """
    if isinstance(data, SceneDocument):
        raw = data.model_dump()
    else:
        # 先做一層淺拷貝，避免改到呼叫端資料
        raw = copy.deepcopy(data)

    base = Path(base_dir) if base_dir else Path.cwd()

    # 草稿目錄
    if not raw.get("draft_folder"):
        raw["draft_folder"] = default_jianying_draft_folder()
        logger.info("使用預設草稿目錄：%s", raw["draft_folder"])

    # allow_replace 環境變數可覆寫
    env_replace = os.getenv("ALLOW_REPLACE_DRAFT", "").strip().lower()
    if env_replace in {"true", "1", "yes"}:
        raw["allow_replace"] = True
    elif env_replace in {"false", "0", "no"}:
        raw["allow_replace"] = False

    # project 預設由 Pydantic 補；這裡確保 key 存在
    raw.setdefault("project", {})
    raw.setdefault("text_style", {})

    scenes = raw.get("scenes") or []
    for idx, scene in enumerate(scenes):
        # id
        if not scene.get("id"):
            scene["id"] = f"scene_{idx + 1:03d}"

        # 路徑絕對化
        if scene.get("path"):
            scene["path"] = resolve_path(scene["path"], base)

        # type 自動判斷
        if not scene.get("type"):
            scene["type"] = detect_media_type(scene["path"]).value
            logger.debug("scene %s 自動判斷 type=%s", scene["id"], scene["type"])

        # 圖片若沒 duration，補預設秒數
        if scene.get("type") == SceneMediaType.image.value and not scene.get("duration"):
            scene["duration"] = DEFAULT_IMAGE_DURATION_SEC
            logger.info(
                "scene %s 是圖片且未給 duration，使用預設 %.1fs",
                scene["id"],
                DEFAULT_IMAGE_DURATION_SEC,
            )

        # 數值預設
        scene.setdefault("source_start", 0.0)
        scene.setdefault("speed", 1.0)
        scene.setdefault("volume", 1.0)

        if check_files_exist:
            p = Path(scene["path"])
            if not p.is_file():
                raise FileNotFoundError(
                    f"場景 {scene['id']} 素材不存在：{p}\n"
                    f"請確認 Coze/本機路徑是否為真實本地檔案。"
                )

    # BGM 路徑
    bgm = raw.get("bgm")
    if bgm and bgm.get("path"):
        bgm["path"] = resolve_path(bgm["path"], base)
        bgm.setdefault("volume", 0.5)
        bgm.setdefault("fade_in", "1s")
        bgm.setdefault("fade_out", "1s")
        if check_files_exist and not Path(bgm["path"]).is_file():
            raise FileNotFoundError(f"BGM 檔案不存在：{bgm['path']}")

    # 標題修剪
    if isinstance(raw.get("title"), str):
        raw["title"] = raw["title"].strip() or "未命名草稿"

    doc = load_scene_dict(raw)
    logger.info(
        "預設值補全完成：title=%s, scenes=%d, has_bgm=%s",
        doc.title,
        len(doc.scenes),
        doc.bgm is not None,
    )
    return doc
