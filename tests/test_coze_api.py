"""階段 3：Coze 端點、Token、多種 body 格式。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ASSETS = ROOT / "assets"
SAMPLE = ROOT / "examples" / "sample_scene.json"


def _assets_ready() -> bool:
    return (ASSETS / "test_clip_a.mp4").is_file()


@pytest.fixture()
def client(monkeypatch):
    # 預設測試不啟用 Token
    monkeypatch.delenv("JY_API_TOKEN", raising=False)
    # 重新載入 auth 狀態：verify 讀的是 os.getenv，每次請求當下讀即可
    from fastapi.testclient import TestClient

    from src.api import app

    with TestClient(app) as c:
        yield c


def test_coze_guide(client):
    r = client.get("/v1/coze/guide")
    assert r.status_code == 200
    assert r.json()["recommended_url_path"] == "/v1/coze/convert"


def test_coze_validate_flat(client):
    body = {
        "title": "coze_val",
        "scenes": [{"path": "a.mp4", "type": "video", "duration": 1}],
    }
    r = client.post("/v1/coze/validate", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["success"] is True
    assert data["title"] == "coze_val"
    assert data["scene_count"] == 1


def test_scene_json_string_body(client):
    body = {
        "scene_json": json.dumps(
            {
                "title": "string_wrap",
                "scenes": [{"path": "a.mp4", "type": "video", "duration": 1}],
            },
            ensure_ascii=False,
        )
    }
    r = client.post("/v1/coze/validate", json=body)
    assert r.status_code == 200
    assert r.json()["title"] == "string_wrap"


def test_data_wrapper_body(client):
    body = {
        "data": {
            "title": "data_wrap",
            "scenes": [{"path": "a.mp4", "type": "video", "duration": 1}],
        }
    }
    r = client.post("/v1/coze/validate", json=body)
    assert r.status_code == 200
    assert r.json()["title"] == "data_wrap"


def test_token_required_blocks(monkeypatch):
    monkeypatch.setenv("JY_API_TOKEN", "secret-test-token-123")
    from fastapi.testclient import TestClient

    from src.api import app

    with TestClient(app) as c:
        r = c.post(
            "/v1/coze/validate",
            json={
                "title": "x",
                "scenes": [{"path": "a.mp4", "type": "video", "duration": 1}],
            },
        )
        assert r.status_code == 401

        r2 = c.post(
            "/v1/coze/validate",
            headers={"Authorization": "Bearer secret-test-token-123"},
            json={
                "title": "x",
                "scenes": [{"path": "a.mp4", "type": "video", "duration": 1}],
            },
        )
        assert r2.status_code == 200

        r3 = c.post(
            "/v1/coze/validate",
            headers={"X-API-Key": "secret-test-token-123"},
            json={
                "title": "x",
                "scenes": [{"path": "a.mp4", "type": "video", "duration": 1}],
            },
        )
        assert r3.status_code == 200


@pytest.mark.skipif(not _assets_ready(), reason="缺測試素材")
def test_coze_convert(client):
    from src.defaults import default_jianying_draft_folder

    if not Path(default_jianying_draft_folder()).is_dir():
        pytest.skip("無剪映草稿目錄")

    raw = json.loads(SAMPLE.read_text(encoding="utf-8"))
    raw["title"] = "JY助手_Coze端點測試"
    raw["allow_replace"] = True

    r = client.post(
        "/v1/coze/convert",
        params={"check_files": True, "base_dir": str(SAMPLE.parent)},
        json={"scene": raw},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["success"] is True
    assert data["draft_name"] == "JY助手_Coze端點測試"
    assert "draft_path" in data
    assert Path(data["draft_path"]).is_dir()
