"""signalverify —— 命令行入口。每个子命令都能 --json 落盘。

说明：stdout 只输出 JSON 产物（这是交付物，不是日志）；
诊断信息一律走 logging，遵循"生产环境禁止用 print 打日志"的纪律。
"""
import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from .core.ffmpeg import probe, ffmpeg_available
from .core.report import Report, write_report
from .audio import read_wav_mono, envelope

LOGGER = logging.getLogger("signalverify")
from .audio.lyric_timing import parse_lyrics, asr_char_times, build_timing, build_segments
from .audio.lip_offset import lip_offset
from .visual.frame_sheet import build_frame_sheet


def _emit(report, json_path):
    """把报告打到 stdout；--json 时同时落盘。"""
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if json_path:
        write_report(report, json_path)
    print(text)


def cmd_lip_offset(a):
    r = lip_offset(a.video, a.audio, a.max_lag_sec)
    rep = Report("lip-offset").method(
        "Haar 正脸 -> 下半脸 ROI 拉普拉斯方差/帧差，对参考音频 RMS 包络做互相关并搜索最优滞后"
    ).input("video", a.video).input("audio", a.audio)
    for k, v in r.items():
        rep.result(k, v)
    rep.limitation("Haar 检测在侧脸/遮挡时会丢帧；丢帧率见 face_detected_frames。")
    rep.limitation("这是启发式筛查，不能证明每个字的口型正确；逐字正确性只能人耳+人眼。")
    rep.limitation("frame_diff 在固定机位慢推镜头里噪声大，优先看 lower_face_edge。")
    _emit(rep, a.json)


def cmd_frame_sheet(a):
    times = [float(t) for t in a.times.split(",")] if a.times else None
    info = build_frame_sheet(a.video, a.out, times=times, count=a.count,
                             cols=a.cols, tile_width=a.tile_width)
    rep = Report("frame-sheet").method(
        "ffmpeg/OpenCV 按时间点抽帧，等比缩放到统一宽度，逐格叠加时间码后拼贴"
    ).input("video", a.video)
    for k, v in info.items():
        rep.result(k, v)
    rep.limitation("时间码是请求时间，实际帧可能偏一帧，不要在 ±0.05s 上做文章。")
    _emit(rep, a.json)


def cmd_probe(a):
    rep = Report("probe").method("ffprobe").input("path", a.path)
    for k, v in probe(a.path).items():
        rep.result(k, v)
    rep.limitation("只读容器/流头信息，不解码内容。")
    _emit(rep, a.json)


# ---------------------------------------------------------------- lyric-timing
def cmd_lyric_separate(a):
    out = Path(a.out) / "stems"
    out.mkdir(parents=True, exist_ok=True)
    cmd = [a.demucs_python, "-m", "demucs", "-n", a.demucs_model,
           "--two-stems=vocals", "-o", str(out)]
    if a.device:
        cmd += ["--device", a.device]
    cmd.append(str(a.audio))
    env = dict(os.environ)
    if a.torch_home:
        env["TORCH_HOME"] = a.torch_home
    subprocess.run(cmd, check=True, env=env)
    vocals = out / a.demucs_model / Path(a.audio).stem / "vocals.wav"
    rep = Report("lyric-timing/separate").method("demucs --two-stems=vocals").input("audio", a.audio)
    rep.result("vocals", str(vocals)).result("exists", vocals.exists())
    rep.limitation("分离质量影响 ASR 命中率；不要拿混音直接做 ASR。")
    _emit(rep, None)


def cmd_lyric_transcribe(a):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    import torch
    from scipy.signal import resample_poly
    from transformers import pipeline

    tmp = Path(a.out) / "_asr_16k.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(a.wav),
                    "-ac", "1", "-ar", "16000", str(tmp)], check=True)
    x, sr = read_wav_mono(tmp)
    if sr != 16000:
        x = resample_poly(x, 16000, sr).astype("float32")
    torch.set_num_threads(a.threads)
    pipe = pipeline("automatic-speech-recognition", model=a.whisper_model,
                    device=-1, dtype=torch.float32)
    res = pipe({"array": x, "sampling_rate": 16000}, return_timestamps="word",
               generate_kwargs={"language": a.language, "task": "transcribe"})
    payload = {"source": str(a.wav), "model": a.whisper_model, "language": a.language,
               "text": res["text"], "chunks": res.get("chunks", []),
               "warning": "ASR 只提供时间证据；错字由 align 阶段用权威歌词纠正。"}
    out = Path(a.out) / "asr.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    rep = Report("lyric-timing/transcribe").method("transformers Whisper word-level timestamps")
    rep.result("chunks", len(payload["chunks"])).result("out", str(out))
    rep.limitation("歌词演唱场景 ASR 认字率可能只有六成；不要据此纠正歌词。")
    _emit(rep, None)


def cmd_lyric_align(a):
    asr = json.loads(Path(a.asr).read_text(encoding="utf-8"))
    lines = parse_lyrics(a.lyrics)
    rows, qa = build_timing(lines, asr_char_times(asr))
    out = Path(a.out) / "lyric_timing.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"method": "权威歌词字符级单调全局对齐", "qa": qa, "lines": rows},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    rep = Report("lyric-timing/align").method("歌词字符级单调全局对齐 + 时长先验收紧")
    rep.result("lines", len(rows)).result("qa", qa).result("out", str(out))
    rep.limitation("逐字时间是 chunk 内等分插值，精度只到句级。")
    rep.limitation("qa.weak_lines 内的句子必须人工复核后再采信。")
    _emit(rep, None)


def cmd_lyric_segments(a):
    d = json.loads(Path(a.timing).read_text(encoding="utf-8"))
    segs = build_segments(d["lines"], min_duration=a.min_duration, max_duration=a.max_duration,
                          preroll=a.preroll, postroll=a.postroll, max_gap=a.max_gap)
    out = Path(a.out) / "segments.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"policy": {"min": a.min_duration, "max": a.max_duration,
                                          "preroll": a.preroll, "postroll": a.postroll,
                                          "max_gap": a.max_gap},
                               "segments": segs}, ensure_ascii=False, indent=2), encoding="utf-8")
    rep = Report("lyric-timing/segments").method("按整句切段，段首留 preroll，禁止重叠")
    rep.result("segments", len(segs)).result("out", str(out)).result("detail", segs)
    rep.limitation("段长受目标模型的时长区间约束；视频模型最长帧数会把段切碎。")
    _emit(rep, None)


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="signalverify", description="SimpleAgentSignalVerify")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("lip-offset", help="口型偏移与相关度")
    s.add_argument("--video", required=True)
    s.add_argument("--audio", required=True)
    s.add_argument("--max-lag-sec", type=float, default=2.0)
    s.add_argument("--json")
    s.set_defaults(func=cmd_lip_offset)

    s = sub.add_parser("frame-sheet", help="按时间码拼联络单")
    s.add_argument("--video", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--times")
    s.add_argument("--count", type=int, default=12)
    s.add_argument("--cols", type=int, default=4)
    s.add_argument("--tile-width", type=int, default=480)
    s.add_argument("--json")
    s.set_defaults(func=cmd_frame_sheet)

    s = sub.add_parser("probe", help="读容器/流信息")
    s.add_argument("--path", required=True)
    s.add_argument("--json")
    s.set_defaults(func=cmd_probe)

    lt = sub.add_parser("lyric-timing", help="歌词逐句时间码")
    lts = lt.add_subparsers(dest="ltcmd", required=True)
    x = lts.add_parser("separate"); x.set_defaults(func=cmd_lyric_separate)
    x.add_argument("--audio", required=True); x.add_argument("--out", required=True)
    x.add_argument("--demucs-python", default="python")
    x.add_argument("--demucs-model", default="htdemucs")
    x.add_argument("--torch-home", default=os.environ.get("TORCH_HOME", ""))
    x.add_argument("--device", default="cpu")
    x = lts.add_parser("transcribe"); x.set_defaults(func=cmd_lyric_transcribe)
    x.add_argument("--wav", required=True); x.add_argument("--out", required=True)
    x.add_argument("--whisper-model", required=True)
    x.add_argument("--language", default="zh"); x.add_argument("--threads", type=int, default=6)
    x = lts.add_parser("align"); x.set_defaults(func=cmd_lyric_align)
    x.add_argument("--lyrics", required=True); x.add_argument("--asr", required=True)
    x.add_argument("--out", required=True)
    x = lts.add_parser("segments"); x.set_defaults(func=cmd_lyric_segments)
    x.add_argument("--timing", required=True); x.add_argument("--out", required=True)
    x.add_argument("--min-duration", type=float, default=4.0)
    x.add_argument("--max-duration", type=float, default=15.0)
    x.add_argument("--preroll", type=float, default=0.35)
    x.add_argument("--postroll", type=float, default=0.30)
    x.add_argument("--max-gap", type=float, default=0.9)

    a = p.parse_args(argv)
    if not ffmpeg_available():
        LOGGER.warning("ffmpeg/ffprobe not found on PATH")
    a.func(a)


if __name__ == "__main__":
    main()
