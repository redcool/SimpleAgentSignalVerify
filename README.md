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

# 视觉：面相"王"字格量化（评审用，不要写进生成提示词）
sv face-grid --image face1.png face2.png --json face_grid.json
```

## 目录

```
signalverify/   库：能 import、能测试，实现只有这一份
  core/         ffmpeg 调用、时间基准、统一报告信封
  audio/        歌词时间码、口型对齐、WAV/包络
  visual/       抽帧联络单、面相王字格量化
docs/cli/       命令文档：每条命令的用法、参数、局限——工具技能在这里
skills/         面向 agent 的技能包，只写方法与判据，不放脚本
  defect-loop-review/   流程技能：缺陷闭环审核（广度→深度→增量验证）
tests/          确定性单测（零依赖运行器，装了 pytest 也能跑）
```

> **库负责算，技能负责教怎么用。** 技能里禁止复制脚本——复制就会漂。

## 两类技能

| 类型 | 位置 | 形态 | 例子 |
|---|---|---|---|
| 工具技能 | `docs/cli/<命令名>/` | 一条命令的薄壳：什么时候用、命令、局限 | `frame-sheet` `video-lip-sync` |
| 流程技能 | `skills/<技能名>/` | 一套方法与判据，零代码 | `defect-loop-review` |

两类分开，是因为它们解决的问题不同：工具技能回答"**是不是**"（口型偏了几秒、响度差了几个 dB），流程技能回答"**要不要改、改完怎么停**"。

流程技能为什么也放进这个仓库：量具与判据要一起用。能变成数字的，交给 `signalverify` 出证据（进 A 级）；量不出来的，进人审或降为可选建议，不许伪装成 A 级。

## 出处

- `visual/` 与 `audio/` 的部分思路来自 [lovisdotio/video-to-game](https://github.com/lovisdotio/video-to-game)（MIT），
  以及其衍生技能 `visual-taste` / `audio-taste`。见 `NOTICE`。
- `audio/lyric_timing.py`、`audio/lip_offset.py`、`visual/frame_sheet.py` 为本库原创。

## 许可

MIT。
