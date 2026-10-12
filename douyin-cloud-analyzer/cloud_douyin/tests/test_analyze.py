import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze import safe_media_url, extract_link, pick_evidence


def test_douyin_share_link():
    assert extract_link("複製打開抖音 https://v.douyin.com/dViHSoerNs0/ 其他") == "https://v.douyin.com/dViHSoerNs0/"


def test_anytocopy_direct_mp4():
    url = "https://v26-default.365yg.com/video/abcd?a=1&b=2"
    assert extract_link(url) == url
    assert safe_media_url(url)


def test_reject_untrusted_domains():
    assert not safe_media_url("http://localhost/video.mp4")
    assert not safe_media_url("https://evil.365yg.com.attacker.org/video")
    assert not safe_media_url("https://z.gao.gs/admin")
    assert not safe_media_url("https://user:pass@aweme.snssdk.com/video")


def test_evidence_sampler():
    frames = [Path(f"frame_{i}.jpg") for i in range(20)]
    picks = pick_evidence(frames, [{"second": 4, "lines": ["早餐 貝果 200g"]}])
    assert any(i == 4 for i, _ in picks)
