"""
階段 1 一鍵驗證：
1. 產生測試素材
2. 單元測試
3. 驗證 sample JSON
4. 實際寫入剪映草稿
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("\n" + "=" * 60)
    print(">", " ".join(cmd))
    print("=" * 60)
    subprocess.run(cmd, check=True, cwd=str(cwd or ROOT))


def main() -> int:
    py = sys.executable

    # 1) 測試素材
    run([py, str(ROOT / "scripts" / "generate_test_assets.py")])

    # 2) 單元測試（models）
    run([py, "-m", "pytest", "tests/test_models.py", "-v"], cwd=ROOT)

    # 3) validate
    run(
        [
            py,
            "-m",
            "src.cli",
            "validate",
            str(ROOT / "examples" / "sample_scene.json"),
            "--check-files",
        ],
        cwd=ROOT,
    )

    # 4) convert
    run(
        [
            py,
            "-m",
            "src.cli",
            "-v",
            "convert",
            str(ROOT / "examples" / "sample_scene.json"),
        ],
        cwd=ROOT,
    )

    # 5) converter 測試
    run([py, "-m", "pytest", "tests/test_converter.py", "-v"], cwd=ROOT)

    print("\n" + "=" * 60)
    print("✅ 階段 1 全部測試通過")
    print("請打開剪映，尋找草稿：JY助手_階段1測試")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 測試失敗，exit={e.returncode}", file=sys.stderr)
        raise SystemExit(e.returncode)
