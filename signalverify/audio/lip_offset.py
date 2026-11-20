"""口型偏移：画面嘴部运动 vs 参考音频包络，找最优滞后 + 相关系数。

判据（重要）：
  best_lag_sec > 0  画面上的嘴相对音频滞后
  best_lag_sec < 0  提前
  best_corr < 0.3   画面嘴部动作和这段音频关系很弱
                    → 通常是模型自己重唱了一段，而不是跟着参考音频对口型
                    → 此时裁帧治不了，必须回到上游（整句音频 / 写明时间码）
"""
import numpy as np
import cv2

from .wavio import read_wav_mono, envelope, zscore


def mouth_signals(video):
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    edge, diff, hits, prev = [], [], 0, None
    while True:
        ok, im = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        faces = cas.detectMultiScale(gray, 1.08, 5, minSize=(96, 96))
        if len(faces) == 0:
            edge.append(np.nan)
            diff.append(np.nan)
            continue
        hits += 1
        x, y, w, h = max(faces, key=lambda q: q[2] * q[3])
        roi = gray[int(y + h * 0.55):int(y + h * 0.95), int(x + w * 0.22):int(x + w * 0.78)]
        edge.append(float(cv2.Laplacian(roi, cv2.CV_64F).var()))
        if prev is not None and prev.shape == roi.shape:
            diff.append(float(np.abs(roi.astype(np.int16) - prev.astype(np.int16)).mean()))
        else:
            diff.append(np.nan)
        prev = roi.copy()
    cap.release()
    return np.array(edge, float), np.array(diff, float), fps, hits


def _best_lag(a, b, max_lag_frames, fps):
    res = {"corr_at_0": float(np.corrcoef(zscore(a), zscore(b))[0, 1]),
           "best_corr": -9.0, "best_lag_frames": None, "best_lag_sec": None}
    for lag in range(-max_lag_frames, max_lag_frames + 1):
        if lag < 0:
            x, y = a[:lag], b[-lag:]
        elif lag > 0:
            x, y = a[lag:], b[:-lag]
        else:
            x, y = a, b
        if len(x) < 8:
            continue
        c = float(np.corrcoef(zscore(x), zscore(y))[0, 1])
        if c > res["best_corr"]:
            res["best_corr"] = round(c, 4)
            res["best_lag_frames"] = lag
            res["best_lag_sec"] = round(lag / fps, 3)
    return res


def lip_offset(video, audio, max_lag_sec=2.0):
    edge, diff, fps, hits = mouth_signals(video)
    x, sr = read_wav_mono(audio)
    n = len(edge)
    if n == 0:
        raise ValueError("no frames decoded from %s" % video)
    env = envelope(x, sr, n)
    max_lag = int(round(max_lag_sec * fps))
    signals = {}
    for name, sig in (("lower_face_edge", edge), ("lower_face_diff", diff)):
        r = _best_lag(env, sig, max_lag, fps)
        r["fps"] = fps
        signals[name] = r
    return {
        "video": str(video), "audio": str(audio), "fps": fps,
        "frames": n, "face_detected_frames": hits,
        "signals": signals,
        "interpretation": (
            "best_lag_sec > 0 表示画面上的嘴相对参考音频【滞后】；< 0 表示【提前】。"
            "best_corr < 0.3 说明画面嘴部动作与这段音频关系很弱——常见原因是模型自己重唱了一段，"
            "此时不要裁帧，要先解决「音频是否真的驱动了口型」。"
        ),
    }
