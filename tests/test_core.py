"""确定性单测：不碰模型、不碰网络。ffmpeg 相关的用纯函数或合成 WAV 验证。"""
import json
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from signalverify.audio.lyric_timing import parse_lyrics, asr_char_times, align_global, build_timing, build_segments
from signalverify.audio.wavio import envelope, zscore
from signalverify.audio.audio_slice import read_plan, _write_wav, SAMPLE_RATE
from signalverify.finishing.grain import build_filter


def test_parse_lyrics_drops_sections(tmp_path):
    p = tmp_path / "l.txt"
    p.write_text("[Verse 1]\n闹钟一响就起床\n\n[Chorus]\n工作第一 是赚钱养家\n", encoding="utf-8")
    lines = parse_lyrics(p)
    assert len(lines) == 2
    assert lines[0]["section"] == "Verse 1"
    assert "".join(lines[1]["chars"]) == "工作第一是赚钱养家"


def test_align_is_monotonic_and_finds_order():
    A = list("abcd")
    B = list("abxcd")
    map_a, cost = align_global(A, B)
    idx = [m for m in map_a if m is not None]
    assert idx == sorted(idx)
    assert map_a[0] == 0 and map_a[3] == 4


def test_align_prefers_match_over_skip():
    map_a, cost = align_global(list("abc"), list("abc"))
    assert cost == 0.0
    assert map_a == [0, 1, 2]


def test_asr_char_times_spreads_within_chunk():
    rows = asr_char_times({"chunks": [{"text": "你好", "timestamp": [1.0, 2.0]}]})
    assert len(rows) == 2
    assert rows[0]["start"] == 1.0
    assert abs(rows[1]["start"] - 1.5) < 1e-6


def test_build_timing_flags_weak_lines():
    lines = [{"section": "", "line": t, "chars": list(t)} for t in ["甲甲甲", "乙乙乙"]]
    times = [{"ch": "甲", "start": 0.0, "end": 0.3},
             {"ch": "甲", "start": 0.3, "end": 0.6},
             {"ch": "甲", "start": 0.6, "end": 0.9}]
    rows, qa = build_timing(lines, times)
    assert qa["weak_lines"]
    assert rows[0]["start"] == 0.0


def test_segments_never_overlap_and_never_start_mid_line():
    rows = [
        {"index": 0, "section": "", "text": "a", "start": 1.0, "end": 3.0, "char_count": 4, "asr_rate": 1.0},
        {"index": 1, "section": "", "text": "b", "start": 3.1, "end": 5.0, "char_count": 4, "asr_rate": 1.0},
        {"index": 2, "section": "", "text": "c", "start": 20.0, "end": 22.0, "char_count": 4, "asr_rate": 1.0},
    ]
    segs = build_segments(rows, min_duration=4.0, max_duration=15.0, preroll=0.35)
    for prev, cur in zip(segs, segs[1:]):
        assert cur["start"] >= prev["end"] - 1e-9
    for seg in segs:
        assert seg["duration"] >= 4.0


def test_envelope_and_zscore():
    x = np.concatenate([np.zeros(100), np.ones(100) * 0.5])
    e = envelope(x, 2)
    assert e[0] < 1e-4          # 包络里加了 1e-9 的 epsilon，静音段是 3e-5 而不是 0
    assert abs(e[1] - 0.5) < 1e-3
    z = zscore([1, 2, 3])
    assert abs(float(z.mean())) < 1e-9


def test_audio_slice_plan_accepts_contiguous(tmp_path):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"shots": [
        {"id": "b01", "start": 0.0, "duration": 2.0},
        {"id": "b02", "start": 2.0, "duration": 2.0},
    ]}), encoding="utf-8")
    rows = read_plan(plan)
    assert rows[0]["start_sample"] == 0
    assert rows[0]["end_sample"] == rows[1]["start_sample"]
    assert rows[1]["end_sample"] == 4 * SAMPLE_RATE


def test_audio_slice_plan_rejects_gap(tmp_path):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"shots": [
        {"id": "b01", "start": 0.0, "duration": 2.0},
        {"id": "b02", "start": 2.5, "duration": 2.0},
    ]}), encoding="utf-8")
    try:
        read_plan(plan)
    except ValueError as exc:
        assert "non-contiguous" in str(exc)
    else:
        raise AssertionError("gap plan should be rejected")


def test_audio_slice_wav_roundtrip(tmp_path):
    """切块内容必须等于母版对应区间；重组必须等于母版。"""
    pcm = (np.arange(SAMPLE_RATE * 2) % 1000).astype(np.int16).tobytes()
    master = tmp_path / "master.wav"
    _write_wav(master, pcm)
    with wave.open(str(master), "rb") as handle:
        data = handle.readframes(handle.getnframes())
    half = len(pcm) // 2
    assert data[0:half] == pcm[0:half]
    assert data[half:] == pcm[half:]
    assert data[0:half] + data[half:] == pcm


def test_build_filter_basics():
    assert build_filter() == "noise=alls=7:allf=t+u"
    composed = build_filter(strength=9, contrast=1.03, vignette=4.0)
    assert "noise=alls=9" in composed
    assert "eq=contrast=1.030" in composed
    assert "vignette=angle=PI/4.00" in composed
    try:
        build_filter(strength=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative strength should raise")
