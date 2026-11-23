# docs/cli —— CLI 用法卡

> **这里只写"命令怎么调、输出怎么读、哪里不能信"。**
> 业务技能（何时用、怎么编排）在 **VideoPrj** 的 `MV_Gen/Skills/`。
> 本仓不提供"技能"，只提供**可执行能力 + 用法卡**。

| 用法卡 | 命令 | 一句话 |
|---|---|---|
| `audio-slice` | `signalverify audio-slice` | PCM 母版 + 整数采样下标切片，重组必须与母版一致 |
| `audio-lyric-timing` | `signalverify lyric-timing` | 歌词对齐到真正发声的时间，并按整句切段 |
| `video-lip-sync` | `signalverify lip-offset` | 嘴有没有跟着音频动、偏了多少 |
| `frame-sheet` | `signalverify frame-sheet` | 按时间码抽帧拼联络单 |
| `image-face-grid` | `signalverify face-grid` | 面相四线量化（只用于评审） |
| `grain` | `signalverify grain` / `grain-metrics` | 颗粒/对比/暗角 + 度量 |

## 规矩

- 用法卡里的命令必须与 `signalverify --help` 一致；改 CLI 就同步改卡片。
- 每张卡必须有 **局限**。
- **禁止**在这里复制实现代码；实现只有一份，在 `signalverify/`。
