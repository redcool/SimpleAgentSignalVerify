---
name: audio-lyric-timing
description: 把歌词对齐到真正发声的时间，输出每句起止时间码，并按整句切段。用于音频驱动的口型生成、按乐句剪辑、把审核意见定位到"第几句"。
---

# audio-lyric-timing

## 什么时候用

- 要拿"每句歌词从第几秒开始"（不是按拍、不是按固定 10 秒切）；
- 要给音频驱动的视频模型喂"从整句开头起"的音频段；
- 要把"大概 50 秒那里有问题"变成"第 7 句第二遍副歌"。

## 命令

```bash
# 1) 分离人声（可选但强烈建议；直接对混音做 ASR 会明显变差）
signalverify lyric-timing separate --audio song.mp3 --out timing/ \
  --demucs-python /path/to/python --torch-home /path/to/models --device cuda

# 2) 转写（需要 transformers + 本地 Whisper）
signalverify lyric-timing transcribe --wav timing/stems/htdemucs/song/vocals.wav \
  --out timing/ --whisper-model /path/to/whisper-small

# 3) 强制对齐
signalverify lyric-timing align --lyrics song.txt --asr timing/asr.json --out timing/

# 4) 按整句切段
signalverify lyric-timing segments --timing timing/lyric_timing.json --out timing/
```

## 输出怎么读

`lyric_timing.json`：

| 字段 | 含义 | 怎么用 |
|---|---|---|
| `start` / `end` | 该句起止（全曲绝对秒） | 切音频、写提示词、定位审核 |
| `asr_rate` | 该句 ASR 认对比例 | < 0.5 视为弱证据，必须人耳复核 |
| `duration_adjusted` | 时长被先验拉回过的句子 | `end` 是估算，`raw_end` 才是原值 |
| `qa.weak_lines` | 必须人工听一遍的句子 | 不要把弱证据当权威 |

`segments.json`：每段 `lyrics[].local_start` 就是"这句在本段里第几秒起"，可直接写进视频提示词。

## 局限

- 逐字时间是 chunk 内等分插值，**精度只到句级**；
- 歌词演唱场景 ASR 认字率常只有六成，`weak_lines` 必须人工复核；
- 器乐段不会出现在时间码里，要另用能量/波形判断。
