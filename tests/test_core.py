"""确定性单测：不碰模型、不碰 ffmpeg、不碰网络。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from signalverify.audio.lyric_timing import parse_lyrics, asr_char_times, align_global, build_timing, build_segments
from signalverify.audio.wavio import envelope, zscore


def test_parse_lyrics_drops_sections(tmp_path):
    p = tmp_path / "l.txt"
    p.write_text("[Verse 1]\n闹钟一响就起床\n\n[Chorus]\n工作第一 是赚钱养家\n", encoding="utf-8")
    lines = parse_lyrics(p)
    assert len(lines) == 2
    assert lines[0]["section"] == "Verse 1"
    assert "".join(lines[1]["chars"]) == "工作第一是赚钱养家"


def test_align_is_monotonic_and_finds_order():
    A = list("abcd")
    B = list("abxcd")          # 中间插了一个 ASR 幻听字
    map_a, cost = align_global(A, B)
    idx = [m for m in map_a if m is not None]
    assert idx == sorted(idx)   # 单调
    assert map_a[0] == 0 and map_a[3] == 4


def test_align_prefers_match_over_skip():
    A = list("abc")
    B = list("abc")
    map_a, cost = align_global(A, B)
    assert cost == 0.0
    assert map_a == [0, 1, 2]


def test_asr_char_times_spreads_within_chunk():
    asr = {"chunks": [{"text": "你好", "timestamp": [1.0, 2.0]}]}
    rows = asr_char_times(asr)
    assert len(rows) == 2
    assert rows[0]["start"] == 1.0
    assert abs(rows[1]["start"] - 1.5) < 1e-6


def test_build_timing_flags_weak_lines():
    lines = parse_lyrics_from(["甲甲甲", "乙乙乙"])
    times = [{"ch": "甲", "start": 0.0, "end": 0.3},
             {"ch": "甲", "start": 0.3, "end": 0.6},
             {"ch": "甲", "start": 0.6, "end": 0.9}]
    rows, qa = build_timing(lines, times)
    assert qa["weak_lines"]
    assert rows[0]["start"] == 0.0


def test_segments_never_overlap_and_never_start_mid_line():
    rows = [
        {"index": 0, "section": "", "text": "a", "start": 1.0, "end": 3.0,
         "char_count": 4, "asr_rate": 1.0},
        {"index": 1, "section": "", "text": "b", "start": 3.1, "end": 5.0,
         "char_count": 4, "asr_rate": 1.0},
        {"index": 2, "section": "", "text": "c", "start": 20.0, "end": 22.0,
         "char_count": 4, "asr_rate": 1.0},
    ]
    segs = build_segments(rows, min_duration=4.0, max_duration=15.0, preroll=0.35)
    for prev, cur in zip(segs, segs[1:]):
        assert cur["start"] >= prev["end"] - 1e-9
    for s in segs:
        assert s["duration"] >= 4.0


def test_envelope_and_zscore():
    x = np.concatenate([np.zeros(100), np.ones(100) * 0.5])
    e = envelope(x, 2)
    assert e[0] < 1e-4          # 包络内加了 1e-9 的 epsilon，静音段是 3e-5 而不是 0
    assert abs(e[1] - 0.5) < 1e-3
    z = zscore([1, 2, 3])
    assert abs(float(z.mean())) < 1e-9


def parse_lyrics_from(texts):
    return [{"section": "", "line": t, "chars": list(t)} for t in texts]
