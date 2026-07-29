"""
產生階段 1 測試用素材（不依賴真實攝影素材）。

需要本機有 ffmpeg。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def run(cmd: list[str]) -> None:
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)

    clip_a = ASSETS / "test_clip_a.mp4"
    clip_b = ASSETS / "test_clip_b.mp4"
    image = ASSETS / "test_image.jpg"
    bgm = ASSETS / "test_bgm.mp3"

    # 藍色 2 秒影片 + 音訊
    if not clip_a.exists():
        run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0x1E90FF:s=1080x1920:d=2",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=2",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(clip_a),
            ]
        )

    # 綠色 2 秒影片
    if not clip_b.exists():
        run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0x32CD32:s=1080x1920:d=2",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=660:duration=2",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(clip_b),
            ]
        )

    # 紅色靜圖
    if not image.exists():
        run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0xDC143C:s=1080x1920",
                "-frames:v",
                "1",
                str(image),
            ]
        )

    # BGM 10 秒（需長過 sample 成片 6.5s，避免轉換時被裁短）
    if not bgm.exists():
        run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=220:duration=10",
                "-c:a",
                "libmp3lame",
                str(bgm),
            ]
        )

    print("✅ 測試素材就緒：", ASSETS)
    for p in (clip_a, clip_b, image, bgm):
        print("  -", p.name, f"({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError:
        print("❌ 找不到 ffmpeg，請先安裝並加入 PATH", file=sys.stderr)
        raise SystemExit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ ffmpeg 失敗：{e}", file=sys.stderr)
        raise SystemExit(1)
