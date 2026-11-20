# SimpleAgentSignalVerify

> 给 agent 用的**信号验证**工具集：把"看着对不对 / 听着对不对 / 口型对不对"变成可复现的数字与证据。

不是生成模型，不是审美裁判。它只做三件事：

1. **量**：从视频/音频里取出可比较的数值（偏移、相关度、响度、配色、细节密度、口型运动）；
2. **证**：把结论落成 JSON + 可看的联络单/并排图，让人类能复核；
3. **定位**：任何结论都能落到秒或像素，不给"感觉有点问题"。

## 为什么单独成库

同一套指标已经在四个项目里各写了一遍（游戏预告、MV 生成、短视频质检、素材筛选）。
重复实现带来的不是工作量，而是**口径漂移**——音画两边的时间基准一旦不一致，
"口型滞后 0.3 秒"这种结论就没人敢信。所以把测量层抽出来，版本化。

## 设计纪律

| 纪律 | 含义 |
|---|---|
| **零 LLM** | 库里不调用任何模型。判断交给人或上层 agent，库只出数字 |
| **重模型可插拔** | Whisper、Demucs 不进依赖，只作为 `--backend` 外部命令调用 |
| **一切 JSON** | 每个命令都有 `--json`，schema 稳定，供流水线消费 |
| **可反驳** | 报告里必须写清方法、参数、已知局限；低置信度要显式标注 |

## 安装

```bash
pip install -e .
```

只依赖 Python 3.10+、ffmpeg/ffprobe、numpy、opencv-python。

## 命令

```bash
# 音频：歌词逐句时间码（需要 --backend 提供 whisper）
sv lyric-timing all --audio song.mp3 --lyrics song.txt --out timing/ \
   --whisper-model /path/to/whisper-small

# 音频+视频：口型偏移与相关度
sv lip-offset --video take.mp4 --audio ref.wav --json out.json

# 视觉：按时间码拼联络单（给视觉模型或人看）
sv frame-sheet --video take.mp4 --count 12 --cols 4 --out sheet.png
```

## 目录

```
signalverify/
  core/      ffmpeg 调用、时间基准、JSON 报告
  audio/     歌词时间码、口型对齐、包络
  visual/    抽帧联络单、帧指标、对比
skills/      面向 agent 的 SKILL.md 薄壳（只调 CLI）
tests/       确定性单测（不依赖模型）
```

## 出处

- `visual/` 与 `audio/` 的部分思路来自 [lovisdotio/video-to-game](https://github.com/lovisdotio/video-to-game)（MIT），
  以及其衍生技能 `visual-taste` / `audio-taste`。见 `NOTICE`。
- `audio/lyric_timing.py`、`audio/lip_offset.py`、`visual/frame_sheet.py` 为本库原创。

## 许可

MIT。
