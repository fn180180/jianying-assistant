"""FastAPI 端點測試（使用 TestClient，不需真的開 port）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from src.api import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["service"] == "jianying-assistant"
    assert "draft_folder" in data


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_validate_minimal(client):
    body = {
        "title": "API測試_驗證",
        "scenes": [{"path": "dummy.mp4", "type": "video", "duration": 1}],
    }
    r = client.post("/v1/validate", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["data"]["title"] == "API測試_驗證"
    assert data["data"]["scene_count"] == 1


def test_validate_missing_title(client):
    r = client.post("/v1/validate", json={"scenes": [{"path": "a.mp4"}]})
    # 缺 title → 驗證錯誤
    assert r.status_code in (400, 422)
    assert r.json()["ok"] is False


def test_validate_envelope(client):
    body = {
        "scene": {
            "title": "包裝格式",
            "scenes": [{"path": "a.mp4", "type": "video", "duration": 1}],
        },
        "options": {"include_normalized": True},
    }
    r = client.post("/v1/validate?include_normalized=true", json=body)
    assert r.status_code == 200
    assert r.json()["data"]["title"] == "包裝格式"


@pytest.mark.skipif(not _assets_ready(), reason="請先產生測試素材")
def test_validate_with_files(client):
    import json

    raw = json.loads(SAMPLE.read_text(encoding="utf-8"))
    r = client.post(
        "/v1/validate",
        params={
            "check_files": True,
            "base_dir": str(SAMPLE.parent),
        },
        json=raw,
    )
    assert r.status_code == 200
    assert r.json()["data"]["scene_count"] == 3


@pytest.mark.skipif(not _assets_ready(), reason="請先產生測試素材")
def test_convert_sample(client):
    import json

    from src.defaults import default_jianying_draft_folder

    draft_root = Path(default_jianying_draft_folder())
    if not draft_root.is_dir():
        pytest.skip("剪映草稿目錄不存在")

    raw = json.loads(SAMPLE.read_text(encoding="utf-8"))
    # 避免跟手動測試草稿搶名字
    raw["title"] = "JY助手_API測試"
    raw["allow_replace"] = True

    r = client.post(
        "/v1/convert",
        params={
            "check_files": True,
            "base_dir": str(SAMPLE.parent),
        },
        json=raw,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["data"]["draft_name"] == "JY助手_API測試"
    assert data["data"]["scene_count"] == 3
    assert Path(data["data"]["draft_path"]).is_dir()


def test_convert_missing_file(client):
    body = {
        "title": "缺檔測試",
        "scenes": [
            {
                "path": "C:/definitely/not/exist/xyz_999.mp4",
                "type": "video",
                "duration": 1,
            }
        ],
        "allow_replace": True,
    }
    r = client.post("/v1/convert", json=body)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "FILE_NOT_FOUND"
