"""草稿轉換整合測試（需要 pyJianYingDraft + 測試素材）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.converter import convert_json_file  # noqa: E402
from src.defaults import default_jianying_draft_folder  # noqa: E402

ASSETS = ROOT / "assets"
SAMPLE = ROOT / "examples" / "sample_scene.json"


def _assets_ready() -> bool:
    needed = [
        ASSETS / "test_clip_a.mp4",
        ASSETS / "test_clip_b.mp4",
        ASSETS / "test_image.jpg",
        ASSETS / "test_bgm.mp3",
    ]
    return all(p.is_file() for p in needed)


@pytest.mark.skipif(not _assets_ready(), reason="請先跑 scripts/generate_test_assets.py")
def test_convert_sample_to_draft():
    draft_root = Path(default_jianying_draft_folder())
    if not draft_root.is_dir():
        pytest.skip(f"剪映草稿目錄不存在：{draft_root}")

    result = convert_json_file(SAMPLE, check_files=True)
    assert result.scene_count == 3
    assert result.total_duration_sec > 0
    assert result.has_bgm is True
    assert result.has_subtitles is True

    draft_dir = Path(result.draft_path)
    assert draft_dir.is_dir(), f"草稿資料夾應存在：{draft_dir}"

    # 剪映草稿核心檔至少要有 draft_content 或 draft_info 之類
    content_files = list(draft_dir.glob("draft_content*")) + list(draft_dir.glob("*.json"))
    assert content_files, f"草稿目錄內找不到內容檔：{list(draft_dir.iterdir())}"
