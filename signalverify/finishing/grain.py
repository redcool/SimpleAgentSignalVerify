"""收尾处理：颗粒、对比、暗角，以及"颗粒到底加上没有"的度量。

为什么放在后期而不是写在提示词里：
  - 颗粒强度可以是一个数字，不是一个形容词；
  - 原片不动，随时可重来；
  - 生成一次要花钱，改颗粒不花钱；
  - 顺序正确：颗粒必须在缩放/压缩之后加，否则会被编码器吃掉。

这里的两个能力：
  apply_grain(...)    跑 ffmpeg 出片
  grain_metrics(...)  量 center_lapvar 与 temporal_noise（不要用整帧方差，暗角会把它拉低）
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np


def build_filter(strength: int = 7, mode: str = "t+u", contrast: float = 1.0,
                 saturation: float = 1.0, vignette: float = 0.0,
                 sharpen: float = 0.0) -> str:
    """把参数拼成 ffmpeg 滤镜串。纯函数，方便单测。"""
    if strength < 0:
        raise ValueError("strength must be >= 0")
    parts = ["noise=alls=%d:allf=%s" % (int(strength), mode)]
    if abs(contrast - 1.0) > 1e-6 or abs(saturation - 1.0) > 1e-6:
        parts.append("eq=contrast=%.3f:saturation=%.3f" % (contrast, saturation))
    if vignette > 0:
        parts.append("vignette=angle=PI/%.2f" % (vignette,))
    if sharpen > 0:
        parts.append("unsharp=5:5:%.2f:5:5:0" % (sharpen,))
    return ",".join(parts)


def apply_grain(input_path, output_path, strength: int = 7, mode: str = "t+u",
                contrast: float = 1.0, saturation: float = 1.0, vignette: float = 0.0,
                sharpen: float = 0.0, crf: int = 18, preset: str = "slow",
                audio_path=None) -> dict:
    vf = build_filter(strength, mode, contrast, saturation, vignette, sharpen)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(input_path)]
    if audio_path:
        cmd += ["-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0",
                "-c:a", "aac", "-b:a", "192k", "-shortest"]
    else:
        cmd += ["-map", "0:v:0", "-map", "0:a?", "-c:a", "copy"]
    cmd += ["-vf", vf, "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
            "-tune", "grain", "-pix_fmt", "yuv420p", str(output_path)]
    subprocess.run(cmd, check=True)
    return {"input": str(input_path), "output": str(output_path), "filter": vf,
            "crf": crf, "preset": preset, "audio": str(audio_path) if audio_path else "copied"}


def _grade_stats(path, samples: int = 10) -> tuple[float, float]:
    cap = cv2.VideoCapture(str(path))
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    duration = total / fps if total else 0.0
    lap, tnoise, prev = [], [], None
    for index in range(samples):
        cap.set(cv2.CAP_PROP_POS_MSEC, duration * (index + 0.5) / samples * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        crop = gray[int(height * 0.35):int(height * 0.65), int(width * 0.35):int(width * 0.65)]
        lap.append(float(cv2.Laplacian(crop, cv2.CV_64F).var()))
        current = crop.astype(np.float32)
        if prev is not None:
            tnoise.append(float(np.abs(current - prev).mean()))
        prev = current
    cap.release()
    center_lapvar = float(np.mean(lap)) if lap else float("nan")
    temporal_noise = float(np.mean(tnoise)) if tnoise else float("nan")
    return center_lapvar, temporal_noise


def grain_metrics(*paths) -> list[dict]:
    rows = []
    for path in paths:
        lap, tnoise = _grade_stats(path)
        rows.append({"path": str(path), "center_lapvar": round(lap, 2),
                     "temporal_noise": round(tnoise, 3)})
    return rows
