"""Pydantic 模型與預設值補全單元測試（不依賴剪映）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.defaults import apply_defaults, detect_media_type  # noqa: E402
from src.models import SceneDocument, SceneMediaType, load_scene_dict  # noqa: E402


def test_minimal_valid():
    doc = load_scene_dict(
        {
            "title": "t",
            "scenes": [{"path": "a.mp4"}],
        }
    )
    assert doc.title == "t"
    assert len(doc.scenes) == 1
    assert doc.project.width == 1080


def test_empty_scenes_rejected():
    with pytest.raises(ValidationError):
        load_scene_dict({"title": "t", "scenes": []})


def test_duplicate_ids_rejected():
    with pytest.raises(ValidationError):
        load_scene_dict(
            {
                "title": "t",
                "scenes": [
                    {"id": "x", "path": "a.mp4"},
                    {"id": "x", "path": "b.mp4"},
                ],
            }
        )


def test_detect_media_type():
    assert detect_media_type("x.MP4") == SceneMediaType.video
    assert detect_media_type("y.PNG") == SceneMediaType.image
    with pytest.raises(ValueError):
        detect_media_type("z.unknown")


def test_apply_defaults_fills_id_type_image_duration(tmp_path: Path):
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"fake")
    raw = {
        "title": "  demo  ",
        "scenes": [{"path": str(img)}],
    }
    doc = apply_defaults(raw, base_dir=tmp_path, check_files_exist=True)
    assert doc.title == "demo"
    assert doc.scenes[0].id == "scene_001"
    assert doc.scenes[0].type == SceneMediaType.image
    assert doc.scenes[0].duration == 3.0
    assert doc.draft_folder  # 應補上預設草稿目錄


def test_missing_file_when_check(tmp_path: Path):
    raw = {
        "title": "t",
        "scenes": [{"path": "not_exist.mp4", "type": "video"}],
    }
    with pytest.raises(FileNotFoundError):
        apply_defaults(raw, base_dir=tmp_path, check_files_exist=True)


def test_sample_json_validates():
    sample = ROOT / "examples" / "sample_scene.json"
    if not sample.is_file():
        pytest.skip("sample 不存在")
    data = json.loads(sample.read_text(encoding="utf-8"))
    # 不檢查檔案，只看結構
    doc = apply_defaults(data, base_dir=sample.parent, check_files_exist=False)
    assert isinstance(doc, SceneDocument)
    assert len(doc.scenes) == 3
