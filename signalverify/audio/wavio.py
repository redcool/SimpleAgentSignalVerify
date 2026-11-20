"""WAV 读取与包络。只用标准库 + numpy，避免为了听一个文件装一套 DSP。"""
import wave

import numpy as np


def read_wav_mono(path):
    """返回 (float32[-1,1] 单声道数组, 采样率)。"""
    w = wave.open(str(path), "rb")
    try:
        n, sr, ch = w.getnframes(), w.getframerate(), w.getnchannels()
        raw = w.readframes(n)
    finally:
        w.close()
    x = np.frombuffer(raw, dtype=np.int16).astype("float32") / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def envelope(x, n_bands):
    """把信号切成 n_bands 段，取每段 RMS。用于和逐帧视觉信号对齐。"""
    edges = np.linspace(0, len(x), n_bands + 1).astype(int)
    return np.array([np.sqrt(np.mean(x[edges[i]:edges[i + 1]] ** 2) + 1e-9)
                     for i in range(n_bands)])


def zscore(v):
    v = np.asarray(v, float)
    if np.all(np.isnan(v)):
        return np.zeros_like(v)
    v = np.nan_to_num(v, nan=float(np.nanmean(v)))
    return (v - v.mean()) / (v.std() + 1e-8)
