"""
命令列入口。

用法：
  python -m src.cli validate examples/sample_scene.json
  python -m src.cli convert examples/sample_scene.json
  python -m src.cli convert examples/sample_scene.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# 允許直接 python src/cli.py 也能跑
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.converter import convert_json_file
from src.defaults import apply_defaults
from src.models import load_scene_json_file


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_validate(args: argparse.Namespace) -> int:
    """只驗證 + 補預設，不寫草稿。"""
    path = Path(args.json)
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    doc = apply_defaults(
        raw,
        base_dir=path.parent,
        check_files_exist=args.check_files,
    )
    print("✅ 驗證通過")
    print(f"  標題：{doc.title}")
    print(f"  畫布：{doc.project.width}x{doc.project.height} @ {doc.project.fps}fps")
    print(f"  場景數：{len(doc.scenes)}")
    for s in doc.scenes:
        print(
            f"    - [{s.id}] type={s.type.value if s.type else '?'} "
            f"duration={s.duration} path={s.path}"
            + (f' text="{s.text}"' if s.text else "")
        )
    if doc.bgm:
        print(f"  BGM：{doc.bgm.path} volume={doc.bgm.volume}")
    print(f"  草稿目錄：{doc.draft_folder}")

    if args.dump_normalized:
        out = path.with_suffix(".normalized.json")
        out.write_text(
            json.dumps(doc.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  已輸出補全後 JSON：{out}")
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    """驗證並寫入剪映草稿。"""
    if args.dry_run:
        # dry-run = validate + check files
        args.check_files = True
        return cmd_validate(args)

    result = convert_json_file(
        args.json,
        check_files=not args.skip_file_check,
        draft_folder_override=args.draft_folder,
    )
    print("✅ 草稿已建立")
    print(f"  名稱：{result.draft_name}")
    print(f"  路徑：{result.draft_path}")
    print(f"  場景：{result.scene_count} 個")
    print(f"  總長：{result.total_duration_sec:.2f} 秒")
    print(f"  字幕：{'有' if result.has_subtitles else '無'}")
    print(f"  BGM：{'有' if result.has_bgm else '無'}")
    print()
    print("下一步：打開剪映 → 重新整理草稿列表 → 找到同名草稿。")
    print("（若沒看到：先進入任一舊草稿再退出，或重開剪映）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="自製剪映小助手 — Scene JSON → 剪映草稿",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="顯示除錯 log")
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate", help="驗證 JSON 並補預設值")
    p_val.add_argument("json", help="Scene JSON 路徑")
    p_val.add_argument(
        "--check-files",
        action="store_true",
        help="同時檢查素材檔是否存在",
    )
    p_val.add_argument(
        "--dump-normalized",
        action="store_true",
        help="輸出補全後的 JSON 旁檔",
    )
    p_val.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="顯示除錯 log",
    )
    p_val.set_defaults(func=cmd_validate)

    p_conv = sub.add_parser("convert", help="轉成剪映草稿")
    p_conv.add_argument("json", help="Scene JSON 路徑")
    p_conv.add_argument(
        "--draft-folder",
        default=None,
        help="覆寫剪映草稿根目錄",
    )
    p_conv.add_argument(
        "--dry-run",
        action="store_true",
        help="只驗證不寫草稿",
    )
    p_conv.add_argument(
        "--skip-file-check",
        action="store_true",
        help="不檢查素材是否存在（不建議）",
    )
    p_conv.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="顯示除錯 log（也可放在子命令前：python -m src.cli -v convert ...）",
    )
    p_conv.set_defaults(func=cmd_convert)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose)
    try:
        return args.func(args)
    except Exception as e:  # noqa: BLE001
        logging.getLogger(__name__).error("%s", e)
        print(f"❌ 失敗：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
