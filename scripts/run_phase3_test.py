"""
階段 3 一鍵驗證（模擬 Coze HTTP，不需真實 Coze 帳號）：

1. 產生素材 + 全套 pytest
2. 啟動臨時 API（含 Token）
3. 模擬 Coze：Bearer Token + /v1/coze/convert + 多種 body
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
PORT = 18766
BASE = f"http://{HOST}:{PORT}"
TOKEN = "phase3-test-token-do-not-use-in-prod"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("\n" + "=" * 60)
    print(">", " ".join(cmd))
    print("=" * 60)
    subprocess.run(cmd, check=True, cwd=str(cwd or ROOT))


def http_json(
    method: str,
    url: str,
    body: dict | None = None,
    *,
    token: str | None = None,
) -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return e.code, payload


def wait_health(timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            code, data = http_json("GET", f"{BASE}/health")
            if code == 200 and data.get("ok"):
                print("health:", data)
                return
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.3)
    raise RuntimeError(f"服務未就緒：{last_err}")


def main() -> int:
    py = sys.executable
    run([py, str(ROOT / "scripts" / "generate_test_assets.py")])
    run([py, "-m", "pytest", "tests/", "-v"], cwd=ROOT)

    env = {**os.environ, "JY_API_TOKEN": TOKEN}
    print("\n" + "=" * 60)
    print(f"> 啟動臨時服務 {BASE} (Token 已啟用)")
    print("=" * 60)
    proc = subprocess.Popen(
        [py, "-m", "uvicorn", "src.api:app", "--host", HOST, "--port", str(PORT)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_health()

        # 1) 沒 Token 應 401
        sample = json.loads(
            (ROOT / "examples" / "sample_scene.json").read_text(encoding="utf-8")
        )
        sample["title"] = "JY助手_階段3Coze模擬"
        sample["allow_replace"] = True
        code, data = http_json(
            "POST",
            f"{BASE}/v1/coze/convert?check_files=true&base_dir={ROOT / 'examples'}",
            sample,
            token=None,
        )
        print("no token:", code, data.get("message") or data)
        assert code == 401, data

        # 2) 有 Token + 直接 Scene
        code, data = http_json(
            "POST",
            f"{BASE}/v1/coze/convert?check_files=true&base_dir={ROOT / 'examples'}",
            sample,
            token=TOKEN,
        )
        print("convert direct:", code, data.get("message"), data.get("draft_name"))
        assert code == 200 and data.get("success"), data
        assert Path(data["draft_path"]).is_dir()

        # 3) scene_json 字串（模擬 LLM 只輸出字串）
        payload = {
            "scene_json": json.dumps(
                {
                    "title": "JY助手_階段3字串格式",
                    "scenes": [
                        {
                            "path": str(ROOT / "assets" / "test_clip_a.mp4"),
                            "duration": 1.5,
                            "text": "字串格式 OK",
                        }
                    ],
                    "allow_replace": True,
                },
                ensure_ascii=False,
            )
        }
        code, data = http_json(
            "POST",
            f"{BASE}/v1/coze/convert",
            payload,
            token=TOKEN,
        )
        print("convert scene_json string:", code, data.get("draft_name"))
        assert code == 200 and data.get("ok"), data

        # 4) guide
        code, data = http_json("GET", f"{BASE}/v1/coze/guide")
        assert code == 200 and data.get("ok")

        print("\n" + "=" * 60)
        print("階段 3 自動化測試通過")
        print("完整 Coze 設定請看：docs\\COZE_INTEGRATION.md")
        print("剪映應可見草稿：JY助手_階段3Coze模擬 / JY助手_階段3字串格式")
        print("=" * 60)
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        print(f"\n測試失敗，exit={e.returncode}", file=sys.stderr)
        raise SystemExit(e.returncode)
    except Exception as e:  # noqa: BLE001
        print(f"\n測試失敗：{e}", file=sys.stderr)
        raise SystemExit(1)
