"""采样精确音频切块：MP3 一次解码为 PCM 母版，按整数采样点切，重组必须与母版逐采样一致。

为什么不能用 ffmpeg -ss 逐段切：
有损源每次 seek 都会带进编码延迟与起点误差，逐段累积后片段之间的边界会飘。
先把整首解码成一份 PCM 母版，再按采样下标切片，边界就是确定的。

硬规则：
  1. 源文件只解码一次；
  2. 母版格式固定 48kHz / 16-bit / mono；
  3. 切点是整数采样下标；
  4. 计划必须连续：前段 end_sample == 后段 start_sample，不允许 gap 或 overlap；
  5. 切块重组后必须与母版逐字节一致，否则报错。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import wave
from pathlib import Path

SAMPLE_RATE = 48000
CHANNELS = 1
SAMPLE_WIDTH = 2


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_plan(path) -> list[dict]:
    """读取切块计划，并校验连续性。计划格式：{"shots":[{"id","start","duration"}, ...]}"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    shots = data.get("shots")
    if not isinstance(shots, list) or not shots:
        raise ValueError("plan.shots must be a non-empty list")

    rows = []
    expected = 0
    for raw in shots:
        sid = str(raw["id"])
        start = float(raw["start"])
        duration = float(raw["duration"])
        first = round(start * SAMPLE_RATE)
        count = round(duration * SAMPLE_RATE)
        last = first + count
        if first != expected:
            raise ValueError(
                "non-contiguous plan at %s: expected sample %d, got %d" % (sid, expected, first)
            )
        if count <= 0:
            raise ValueError("non-positive duration: %s" % sid)
        rows.append({"id": sid, "start": start, "duration": duration,
                     "start_sample": first, "end_sample": last, "samples": count})
        expected = last
    return rows


def _write_wav(path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(CHANNELS)
        handle.setsampwidth(SAMPLE_WIDTH)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm)


def _decode_master(audio, master) -> bytes:
    """一次性完整解码。这里不用 -ss，避免逐段 seek 的起点误差。"""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-i", str(audio), "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
           "-c:a", "pcm_s16le", str(master)]
    subprocess.run(cmd, check=True)
    with wave.open(str(master), "rb") as handle:
        if (handle.getframerate(), handle.getnchannels(), handle.getsampwidth()) != (
            SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH
        ):
            raise RuntimeError("master format mismatch")
        return handle.readframes(handle.getnframes())


def slice_audio(audio, plan, out_dir) -> dict:
    audio = Path(audio).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = read_plan(plan)
    master = out_dir / "master_48k_mono_s16.wav"
    pcm = _decode_master(audio, master)

    total = len(pcm) // SAMPLE_WIDTH
    if rows[-1]["end_sample"] > total:
        raise ValueError(
            "plan exceeds master: plan ends at sample %d, master has %d"
            % (rows[-1]["end_sample"], total)
        )

    rebuilt, out_rows = [], []
    for row in rows:
        payload = pcm[row["start_sample"] * SAMPLE_WIDTH: row["end_sample"] * SAMPLE_WIDTH]
        path = out_dir / (row["id"] + ".wav")
        _write_wav(path, payload)
        rebuilt.append(payload)
        out_rows.append({**row, "path": str(path), "sha256": sha256_file(path)})

    continuous = b"".join(rebuilt)
    continuous_path = out_dir / "continuous_reassembled.wav"
    _write_wav(continuous_path, continuous)

    report = {
        "source_audio": str(audio),
        "source_sha256": sha256_file(audio),
        "master_wav": str(master),
        "master_pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        "sample_rate": SAMPLE_RATE,
        "channels": CHANNELS,
        "sample_width": SAMPLE_WIDTH,
        "decoded_samples": total,
        "continuous_reassembled": str(continuous_path),
        "continuous_pcm_sha256": hashlib.sha256(continuous).hexdigest(),
        "continuous_matches_master": continuous == pcm[: len(continuous)],
        "slices": out_rows,
    }
    if not report["continuous_matches_master"]:
        raise RuntimeError("reassembled slices do not match the master PCM")
    (out_dir / "manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report
