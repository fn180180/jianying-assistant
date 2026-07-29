"""
SceneDocument → 剪映草稿（pyJianYingDraft）。

白話說明：
- 讀完整 Scene JSON
- 建立影片軌道 / 字幕軌道 / BGM 軌道
- 依 scenes 順序把素材排上時間軸
- 寫進剪映本機草稿資料夾，之後用剪映打開即可
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pyJianYingDraft as draft
from pyJianYingDraft import ClipSettings, TextStyle, trange

from .defaults import apply_defaults
from .models import SceneDocument, SceneMediaType, SceneItem

logger = logging.getLogger(__name__)


@dataclass
class ConvertResult:
    """轉換結果摘要。"""

    draft_name: str
    draft_folder: str
    draft_path: str
    scene_count: int
    total_duration_sec: float
    has_bgm: bool
    has_subtitles: bool


def _sec_to_trange_start(start_sec: float, duration_sec: float):
    """秒 → pyJianYingDraft trange（字串秒，避免浮點誤差問題）。"""
    # trange 第二參數是「持續時長」不是結束時間
    return trange(f"{start_sec:.3f}s", f"{duration_sec:.3f}s")


def _probe_video_duration_sec(path: str) -> float:
    """讀取影片素材時長（秒）。"""
    mat = draft.VideoMaterial(path)
    return mat.duration / draft.SEC


def _resolve_scene_duration(scene: SceneItem) -> float:
    """
    決定場景在時間軸上的秒數。

    - 有指定 duration：用指定值
    - 影片未指定：用素材剩餘長度 / speed
    - 圖片：defaults 已保證有 duration
    """
    if scene.duration is not None:
        return float(scene.duration)

    if scene.type == SceneMediaType.image:
        # 理論上 defaults 已補；防禦性再給一次
        return 3.0

    full = _probe_video_duration_sec(scene.path)
    remaining = max(0.1, full - scene.source_start)
    # 速度越快，時間軸越短
    return remaining / max(scene.speed, 0.01)


def convert_document(
    doc: SceneDocument,
    *,
    check_files: bool = True,
) -> ConvertResult:
    """
    把已補全的 SceneDocument 寫成剪映草稿。
    """
    if check_files:
        # 再跑一次 apply_defaults 只為檔案存在檢查也可；這裡直接檢查
        for s in doc.scenes:
            if not Path(s.path).is_file():
                raise FileNotFoundError(f"素材不存在：{s.path} (scene={s.id})")
        if doc.bgm and not Path(doc.bgm.path).is_file():
            raise FileNotFoundError(f"BGM 不存在：{doc.bgm.path}")

    draft_root = doc.draft_folder
    if not draft_root:
        raise ValueError("draft_folder 為空，請設定 JIANYING_DRAFT_FOLDER 或 JSON 內 draft_folder")

    root_path = Path(draft_root)
    if not root_path.is_dir():
        raise FileNotFoundError(
            f"剪映草稿根目錄不存在：{root_path}\n"
            "請在剪映「全局设置 → 草稿位置」確認路徑，"
            "並寫入環境變數 JIANYING_DRAFT_FOLDER。"
        )

    logger.info("建立草稿：name=%s, size=%dx%d, fps=%d",
                doc.title, doc.project.width, doc.project.height, doc.project.fps)

    folder = draft.DraftFolder(str(root_path))
    script = folder.create_draft(
        doc.title,
        doc.project.width,
        doc.project.height,
        fps=doc.project.fps,
        allow_replace=doc.allow_replace,
    )

    # 軌道：從背景到前景
    track_specs = [
        draft.TrackSpec(draft.TrackType.video, "main"),
        draft.TrackSpec(draft.TrackType.text, "subtitle"),
    ]
    if doc.bgm:
        track_specs.insert(0, draft.TrackSpec(draft.TrackType.audio, "bgm"))
    script.append_tracks(track_specs)

    cursor = 0.0  # 時間軸游標（秒）
    has_subtitles = False
    style = doc.text_style

    for scene in doc.scenes:
        # 確保 type 有值
        media_type = scene.type or SceneMediaType.video
        duration = _resolve_scene_duration(scene)
        target = _sec_to_trange_start(cursor, duration)

        logger.info(
            "加入場景 %s type=%s duration=%.2fs path=%s",
            scene.id,
            media_type.value,
            duration,
            scene.path,
        )

        if media_type == SceneMediaType.video:
            source = trange(
                f"{scene.source_start:.3f}s",
                f"{duration * scene.speed:.3f}s",
            )
            seg = draft.VideoSegment(
                scene.path,
                target,
                source_timerange=source,
                speed=scene.speed,
                volume=scene.volume,
            )
        else:
            # 圖片：用 VideoSegment + 指定時長（庫會把靜圖當影片素材）
            seg = draft.VideoSegment(scene.path, target)

        script.add_segment(seg, "main")

        # 字幕
        if scene.text:
            has_subtitles = True
            text_seg = draft.TextSegment(
                scene.text,
                target,
                style=TextStyle(
                    size=style.size,
                    color=(style.color_r, style.color_g, style.color_b),
                    auto_wrapping=style.auto_wrapping,
                    max_line_width=style.max_line_width,
                    align=1,  # 置中
                ),
                clip_settings=ClipSettings(transform_y=style.transform_y),
            )
            script.add_segment(text_seg, "subtitle")

        cursor += duration

    total_duration = cursor

    # BGM：從頭鋪到整支結束（不可超過音訊素材真實長度）
    if doc.bgm and total_duration > 0:
        audio_mat = draft.AudioMaterial(doc.bgm.path)
        material_sec = audio_mat.duration / draft.SEC
        bgm_dur = doc.bgm.duration if doc.bgm.duration else total_duration
        bgm_dur = min(bgm_dur, total_duration, material_sec)
        if bgm_dur <= 0:
            logger.warning("BGM 可用時長為 0，略過 BGM")
        else:
            if material_sec + 1e-6 < total_duration:
                logger.warning(
                    "BGM 素材僅 %.2fs，短於成片 %.2fs，將只鋪前 %.2fs（不循環）",
                    material_sec,
                    total_duration,
                    bgm_dur,
                )
            audio_seg = draft.AudioSegment(
                doc.bgm.path,
                trange("0s", f"{bgm_dur:.3f}s"),
                volume=doc.bgm.volume,
            )
            # 淡入淡出（字串時間）
            try:
                audio_seg.add_fade(doc.bgm.fade_in, doc.bgm.fade_out)
            except Exception as e:  # noqa: BLE001 — 淡入失敗不應擋整支草稿
                logger.warning("BGM 淡入淡出設定失敗（已略過）：%s", e)
            script.add_segment(audio_seg, "bgm")
            logger.info("已加入 BGM，時長=%.2fs volume=%.2f", bgm_dur, doc.bgm.volume)

    script.save()

    draft_path = str(root_path / doc.title)
    result = ConvertResult(
        draft_name=doc.title,
        draft_folder=str(root_path),
        draft_path=draft_path,
        scene_count=len(doc.scenes),
        total_duration_sec=total_duration,
        has_bgm=doc.bgm is not None,
        has_subtitles=has_subtitles,
    )
    logger.info(
        "草稿已儲存：%s（%.2fs, %d scenes）",
        draft_path,
        total_duration,
        len(doc.scenes),
    )
    return result


def convert_from_dict(
    raw: dict,
    *,
    base_dir: Optional[str | Path] = None,
    check_files: bool = True,
    draft_folder_override: Optional[str] = None,
) -> ConvertResult:
    """
    從 dict（HTTP body / 已載入 JSON）一條龍：補預設 → 轉草稿。

    供 FastAPI 與 CLI 共用。
    """
    data = dict(raw)  # 淺拷貝，避免改到呼叫端
    if draft_folder_override:
        data["draft_folder"] = draft_folder_override

    doc = apply_defaults(
        data,
        base_dir=base_dir,
        check_files_exist=check_files,
    )
    return convert_document(doc, check_files=check_files)


def convert_json_file(
    json_path: str | Path,
    *,
    check_files: bool = True,
    draft_folder_override: Optional[str] = None,
) -> ConvertResult:
    """
    從 Scene JSON 檔一條龍：讀檔 → 補預設 → 轉草稿。
    """
    path = Path(json_path)
    if not path.is_file():
        raise FileNotFoundError(f"找不到 JSON：{path}")

    import json

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    return convert_from_dict(
        raw,
        base_dir=path.parent,
        check_files=check_files,
        draft_folder_override=draft_folder_override,
    )
