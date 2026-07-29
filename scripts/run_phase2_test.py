"""
階段 2 一鍵驗證：
1. 確保測試素材存在
2. 跑單元 + API 測試
3. 真的啟動 uvicorn，用 HTTP 打 health / validate / convert
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
PORT = 18765  # 測試用 port，避免跟手動服務衝突
BASE = f"http://{HOST}:{PORT}"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("\n" + "=" * 60)
    print(">", " ".join(cmd))
    print("=" * 60)
    subprocess.run(cmd, check=True, cwd=str(cwd or ROOT))


def http_json(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return e.code, payload


def wait_health(timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            code, data = http_json("GET", f"{BASE}/health")
            if code == 200 and data.get("ok"):
                print("health ok:", data)
                return
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.3)
    raise RuntimeError(f"服務未就緒：{last_err}")


def main() -> int:
    py = sys.executable

    # 0) 素材
    run([py, str(ROOT / "scripts" / "generate_test_assets.py")])

    # 1) pytest（含 API TestClient）
    run([py, "-m", "pytest", "tests/", "-v"], cwd=ROOT)

    # 2) 真 HTTP 服務
    env = {
        **dict(**{k: v for k, v in __import__("os").environ.items()}),
        "JY_API_HOST": HOST,
        "JY_API_PORT": str(PORT),
    }
    print("\n" + "=" * 60)
    print(f"> 啟動臨時服務 {BASE}")
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

        # validate
        sample = json.loads(
            (ROOT / "examples" / "sample_scene.json").read_text(encoding="utf-8")
        )
        code, data = http_json(
            "POST",
            f"{BASE}/v1/validate?check_files=true&base_dir={ROOT / 'examples'}",
            sample,
        )
        print("validate:", code, data.get("message") or data)
        assert code == 200 and data.get("ok"), data

        # convert
        sample["title"] = "JY助手_階段2HTTP測試"
        sample["allow_replace"] = True
        code, data = http_json(
            "POST",
            f"{BASE}/v1/convert?check_files=true&base_dir={ROOT / 'examples'}",
            sample,
        )
        print("convert:", code, data.get("message") or data)
        assert code == 200 and data.get("ok"), data
        draft_path = Path(data["data"]["draft_path"])
        assert draft_path.is_dir(), draft_path
        print("draft_path:", draft_path)

        print("\n" + "=" * 60)
        print("階段 2 全部測試通過")
        print(f"草稿名稱：{sample['title']}")
        print("手動啟動服務：python -m src.api")
        print("或：.\\\\scripts\\\\start_server.ps1")
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
