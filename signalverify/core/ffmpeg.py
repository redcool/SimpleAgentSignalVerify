"""ffmpeg/ffprobe 的最小封装。只做三件事：能不能用、跑一次、读元信息。"""
import json
import shutil
import subprocess
from pathlib import Path


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def run_ffmpeg(args, check=True):
    """args 不带可执行名，例如 run_ffmpeg(['-i', 'a.mp4', 'b.wav'])"""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", *map(str, args)]
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def probe(path):
    """返回 ffprobe 的 format + streams 摘要（不含具体数据包）。"""
    cmd = ["ffprobe", "-v", "error", "-show_format", "-show_streams",
           "-of", "json", str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    return {
        "path": str(Path(path)),
        "duration": float(data.get("format", {}).get("duration", 0.0) or 0.0),
        "size": int(data.get("format", {}).get("size", 0) or 0),
        "video": None if not video else {
            "codec": video.get("codec_name"),
            "width": int(video.get("width", 0)),
            "height": int(video.get("height", 0)),
            "fps": _fps(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"),
            "frames": int(video.get("nb_frames", 0) or 0),
        },
        "audio": None if not audio else {
            "codec": audio.get("codec_name"),
            "sample_rate": int(audio.get("sample_rate", 0) or 0),
            "channels": int(audio.get("channels", 0) or 0),
        },
    }


def _fps(expr):
    try:
        num, den = expr.split("/")
        return round(float(num) / float(den), 3) if float(den) else 0.0
    except Exception:
        return 0.0
