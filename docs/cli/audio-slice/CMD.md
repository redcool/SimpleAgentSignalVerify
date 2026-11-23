# audio-slice —— 采样精确音频切块

```bash
signalverify audio-slice --audio song.mp3 --plan shot_plan_50.json --out timing/slices_50 --json report.json
```

## 计划格式（必须连续）

```json
{"shots":[{"id":"b01","start":0,"duration":8},{"id":"b02","start":8,"duration":8}]}
```

**前段 end_sample 必须等于后段 start_sample**，否则拒绝执行。

## 输出

- `master_48k_mono_s16.wav`：一次性解码的母版（源文件只解码一次）
- `bNN.wav`：各段
- `continuous_reassembled.wav`：切块重组
- `manifest.json`：含 `continuous_matches_master`（**必须为 true**）

## 局限

- 母版固定 48kHz / 16-bit / mono；
- 计划必须覆盖且连续，不能留空档；
- preroll 只为模型 guide，不能混进最终音频。
