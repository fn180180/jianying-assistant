"""GitHub Actions Douyin cloud video -> OCR + ASR + contact sheets.
Raw MP4, WAV and one-frame-per-second JPGs are never committed or uploaded.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urljoin, urlsplit, quote
import requests
from PIL import Image, ImageOps, ImageDraw
import pytesseract

DOUYIN_PATTERN = re.compile(r"https?://(?:[a-z0-9-]+\.)?(?:douyin\.com|iesdouyin\.com)/[^\s<>\"']+", re.I)
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.I)
ALLOWED = ("douyin.com", "iesdouyin.com", "snssdk.com",
           "zjcdn.com", "365yg.com", "douyinvod.com",
           "bytecdn.cn", "bytecdn.net", "toutiao.com", "z.gao.gs")
LIMIT = 180 * 1024 * 1024


def safe_media_url(url: str) -> bool:
    p = urlsplit(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        return False
    host = p.hostname.lower().rstrip(".")
    if host == "z.gao.gs":
        return p.path == "/proxy.php"
    return any(host == d or host.endswith("." + d) for d in ALLOWED if d != "z.gao.gs")


def extract_link(text: str) -> str:
    match = URL_PATTERN.search(text)
    if not match:
        raise ValueError("沒有找到網址，請貼抖音分享連結或 MP4 直鏈")
    url = match.group(0).rstrip("。，；;！!）)]}")
    if not (safe_media_url(url) or DOUYIN_PATTERN.fullmatch(url)):
        raise ValueError("只接受抖音分享連結或可信抖音 CDN 的 HTTPS 網址")
    return url


def resolve(url: str) -> dict:
    if safe_media_url(url) and not DOUYIN_PATTERN.fullmatch(url):
        return {"title": "AnyToCopy / CDN 直鏈", "author": "", "media": url}
    r = requests.post("https://z.gao.gs/api.php",
        json={"url": url}, timeout=(12, 35),
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://z.gao.gs/"})
    r.raise_for_status()
    obj = r.json()
    if obj.get("success") is not True or obj.get("data", {}).get("type") != "video":
        raise RuntimeError("抖音解析失敗：" + str(obj.get("message", "unknown")))
    d = obj["data"]
    media = d.get("video_url", "")
    if not safe_media_url(media):
        raise RuntimeError("解析結果包含未允許的下載地址")
    return {"title": d.get("title", ""), "author": d.get("author", ""),
            "media": media}


def download(media: str, destination: Path) -> tuple[int, str]:
    headers = {"User-Agent": "Mozilla/5.0",
               "Referer": "https://www.douyin.com/"}
    with requests.Session() as session:
        url = media
        for _ in range(8):
            if not safe_media_url(url):
                raise RuntimeError("阻止不受信任的 CDN 或重導向 URL")
            with session.get(url, stream=True, allow_redirects=False,
                             headers=headers, timeout=(12, 75)) as r:
                if r.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, r.headers.get("Location", ""))
                    continue
                r.raise_for_status()
                ctype = r.headers.get("Content-Type", "").lower()
                if "html" in ctype or "json" in ctype or "xml" in ctype:
                    raise RuntimeError("伺服器返回的不是影片：" + ctype)
                length = 0
                with destination.open("wb") as f:
                    for block in r.iter_content(512 * 1024):
                        if not block:
                            continue
                        length += len(block)
                        if length > LIMIT:
                            raise RuntimeError("MP4 超過 180MB 上限")
                        f.write(block)
                if length < 64 * 1024:
                    raise RuntimeError("影片檔案異常小")
                return length, ctype
    raise RuntimeError("影片重導向超過 8 次")


def cmd(args: list[str], timeout: int = 180) -> str:
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(args[0] + " 錯誤：" + p.stderr[-600:])
    return p.stdout


def extract_frames(video: Path, directory: Path) -> tuple[float, list[Path]]:
    info = json.loads(cmd(["ffprobe", "-v", "error",
         "-show_entries", "format=duration", "-of", "json", str(video)]))
    seconds = float(info["format"]["duration"])
    if not 1 <= seconds <= 1200:
        raise ValueError("影片長度需介於 1 秒與 20 分鐘")
    directory.mkdir()
    cmd(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(video), "-vf", "fps=1,scale=min(900\\,iw):-2",
         "-q:v", "4", str(directory / "frame_%04d.jpg")], timeout=180)
    return seconds, sorted(directory.glob("frame_*.jpg"))


def read_ocr(frames: list[Path]) -> list[dict]:
    rows = []
    keywords = re.compile(r"\d|六哥|六一|早餐|午餐|晚餐|低脂|低碳|克|kg|饺|餃|肉|汤|湯|貝|贝|體重|体重")
    for second, file in enumerate(frames):
        try:
            with Image.open(file) as im:
                prepared = ImageOps.autocontrast(im.convert("L"))
                txt = pytesseract.image_to_string(prepared, lang="chi_sim+eng",
                         config="--psm 11", timeout=8)
            lines = [x.strip() for x in txt.splitlines() if x.strip()]
            lines = [x for x in lines if keywords.search(x)]
            if lines:
                rows.append({"second": second, "lines": lines[:22]})
        except Exception as exc:
            if second < 3:
                print("OCR warning:", type(exc).__name__, str(exc)[:90], flush=True)
    return rows


def transcribe(video: Path, directory: Path) -> tuple[str, str]:
    audio = directory / "audio.wav"
    try:
        cmd(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
             str(video), "-vn", "-ar", "16000", "-ac", "1", str(audio)], 120)
        from faster_whisper import WhisperModel
        model = os.getenv("WHISPER_MODEL", "base")
        if model == "none":
            return "", "WHISPER_MODEL=none，已停用語音轉寫"
        segments, info = WhisperModel(model, device="cpu", compute_type="int8").transcribe(
            str(audio), language="zh", beam_size=3, vad_filter=True)
        return "\n".join(f"[{s.start:.1f}-{s.end:.1f}s] {s.text.strip()}" for s in segments), ""
    except Exception as exc:
        return "", f"ASR 失敗：{type(exc).__name__}: {str(exc)[:180]}"


def pick_evidence(frames: list[Path], ocr: list[dict]) -> list[tuple[int, Path]]:
    if not frames:
        return []
    weights = {}
    for item in ocr:
        joined = " ".join(item["lines"])
        score = len(joined) // 50
        if re.search(r"\d+\s*(?:g|克|ml|kg|斤|个|顆|颗)", joined, re.I):
            score += 6
        if re.search(r"早餐|午餐|晚餐|低脂|六哥|体重|體重", joined):
            score += 4
        weights[item["second"]] = score
    selected = []
    for part in range(4):
        a, b = len(frames) * part // 4, len(frames) * (part + 1) // 4
        selected_part = []
        for index in sorted(range(a, b), key=lambda n: weights.get(n, 0), reverse=True):
            if all(abs(index - other) >= 3 for other in selected_part):
                selected_part.append(index)
                if len(selected_part) == 4:
                    break
        selected.extend(selected_part)
    return [(i, frames[i]) for i in sorted(selected)]


def make_sheets(frames: list[Path], ocr: list[dict], out: Path) -> list[str]:
    folder = out / "visual_evidence"
    folder.mkdir(exist_ok=True)
    choices = [("timeline", [(i, f) for i, f in enumerate(frames) if i % 4 == 0]),
               ("keyframes", pick_evidence(frames, ocr))]
    files = []
    for kind, picks in choices:
        for start in range(0, len(picks), 9):
            group = picks[start:start + 9]
            w, h, cols = 430, 800, 3
            height = ((len(group) + cols - 1) // cols) * h
            sheet = Image.new("RGB", (w * cols, height), "#f6f6f6")
            painter = ImageDraw.Draw(sheet)
            for j, (sec, filename) in enumerate(group):
                with Image.open(filename) as original:
                    frame = original.convert("RGB")
                    frame.thumbnail((w - 10, h - 42))
                    x = j % cols * w + (w - frame.width) // 2
                    y = j // cols * h + 32
                    sheet.paste(frame, (x, y))
                painter.text((j % cols * w + 10, j // cols * h + 8),
                             f"{sec // 60:02d}:{sec % 60:02d}", fill="#222222")
            dst = folder / f"{kind}_{start // 9 + 1:02d}.jpg"
            sheet.save(dst, "JPEG", quality=78, optimize=True)
            files.append("visual_evidence/" + dst.name)
    return files


def report_text(data: dict) -> str:
    lines = ["# 抖音影片雲端分析素材包", "",
        "**來源：** " + data.get("source", ""),
        "**標題：** " + data.get("title", ""),
        "**影片長度：** " + str(data.get("duration", "?")) + " 秒", "",
        "## 狀態", "",
        "本報告包含 OCR、中文語音轉寫與供 ChatGPT 逐張核對的 JPG 分鏡圖。**無需 Gemini API Key。**",
        "OCR 和 Whisper 都可能出錯，不能把左右人物食材混淆；尚未自行判定食材重量或熱量。", "",
        "## JPG 分鏡圖（Artifact 內）", ""]
    lines.extend("- " + path for path in data.get("sheets", []))
    lines += ["", "## 影片旁白逐字稿", "",
              data.get("transcript", "") or "尚未辨識到語音。", "",
              "## 畫面中文文字 OCR（按秒）", ""]
    for row in data.get("ocr", []):
        lines.append(f"**{row['second']:03d}s** " + " | ".join(row["lines"]))
    if data.get("warnings"):
        lines += ["", "## 不確定與執行錯誤", ""]
        lines.extend("- " + s for s in data["warnings"])
    lines += ["", "**資料保留：** MP4、WAV 和原始影格只在一次性 GitHub Runner 中；本次 Artifact 內僅存文字和分鏡圖，1 天後由 GitHub 清除。"]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", default="output")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    data = {"source": "", "title": "", "duration": None, "bytes": 0,
            "sheets": [], "ocr": [], "transcript": "", "warnings": []}
    code = 0
    try:
        data["source"] = extract_link(args.url)
        with tempfile.TemporaryDirectory(prefix="douyin-actions-") as tmp:
            directory = Path(tmp)
            video = directory / "temporary.mp4"
            meta = resolve(data["source"])
            data["title"] = meta["title"]
            try:
                data["bytes"], _ = download(meta["media"], video)
            except Exception as first:
                # Some Douyin CDNs reject the GitHub runner address; use parsing
                # service proxy as a fallback only, still a bounded HTTPS stream.
                if "z.gao.gs/proxy.php" in meta["media"]:
                    raise
                proxy = "https://z.gao.gs/proxy.php?url=" + quote(meta["media"], safe="")
                data["warnings"].append("原始 CDN 下載失敗，使用代理：" + type(first).__name__)
                data["bytes"], _ = download(proxy, video)
            duration, frames = extract_frames(video, directory / "frames")
            data["duration"] = round(duration, 2)
            print("DOWNLOAD_OK", data["bytes"], "FRAMES", len(frames), flush=True)
            data["ocr"] = read_ocr(frames)
            data["sheets"] = make_sheets(frames, data["ocr"], out)
            data["transcript"], warning = transcribe(video, directory)
            if warning:
                data["warnings"].append(warning)
            print("EVIDENCE_IMAGES", len(data["sheets"]), "OCR_FRAMES",
                  len(data["ocr"]), flush=True)
    except Exception as exc:
        data["warnings"].append(type(exc).__name__ + ": " + str(exc)[:320])
        print("ANALYSIS_ERROR", type(exc).__name__, str(exc)[:250], flush=True)
        code = 1
    finally:
        # TemporaryDirectory has already deleted MP4, WAV and source frames.
        (out / "report.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "ocr.json").write_text(json.dumps(data["ocr"], ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "transcript.txt").write_text(data["transcript"], encoding="utf-8")
        (out / "report.md").write_text(report_text(data), encoding="utf-8")
        print("TEMPORARY_MP4_AND_WAV_REMOVED", flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
