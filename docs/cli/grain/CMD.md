# grain / grain-metrics —— 收尾处理与颗粒度量

```bash
# 出片
signalverify grain --input take.mp4 --output take_grain.mp4 \
  --strength 7 --contrast 1.03 --vignette 4.0 --crf 18 --audio 原曲.wav

# 量"颗粒到底加上没有"
signalverify grain-metrics --video before.mp4 after.mp4
```

## 怎么读

| 指标 | 期望 |
|---|---|
| `center_lapvar` | 加颗粒后 **上升** |
| `temporal_noise` | 加颗粒后 **上升** |

**不要用整帧方差**：暗角会把它拉低，看起来像"没加"。实测出现过整帧 376→306、但颗粒确实加了。

## 局限

- 颗粒降低压缩效率，必须配 `-crf` 与 `-tune grain`；
- 颗粒只治"太干净"，治不了"内容假"；
- 交付到会二次压缩的平台，强度给到 8–10 更稳。
