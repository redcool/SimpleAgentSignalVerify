# skills/ —— 给 agent 的技能薄壳

> 这里**不放实现**，只放"什么时候用、怎么调、输出怎么读、哪里不能信"。
> 实现只有一份，在 `signalverify/`；**禁止在这里复制脚本**（会漂）。

| 技能 | 命令 | 什么时候用 |
|---|---|---|
| `audio-lyric-timing` | `signalverify lyric-timing ...` | 要把歌词对齐到真正发声的时间，并按整句切段 |
| `video-lip-sync` | `signalverify lip-offset ...` | 要判断画面上的嘴有没有跟着某段音频动、偏了多少 |
| `image-face-grid` | `signalverify face-grid ...` | 要量化一张正面人像"方正/正气"的程度 |
| `frame-sheet` | `signalverify frame-sheet ...` | 要把视频按时间码抽帧拼成一张图给人或视觉模型看 |

## 为什么拆成 skills/

`signalverify` 是**库**（可 import、可测试）；agent 需要的是**技能**（自然语言触发、一句话说清用法）。
两者混在同一个 README 里，人会被淹没，agent 会漏读。
所以：库负责算，skills 负责教怎么用。

## 硬规矩

- 技能里写的命令必须与 `signalverify --help` 一致，改 CLI 就要同步改这里。
- 每个技能必须写 **limitations**：不写局限的技能等于在骗人。
