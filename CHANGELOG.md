# 变更记录

版本号规则（遵循 SimpleMcpServer docsRules / Agent工作纪律 第 6 条）：

```
x.y.z.w
x 世代版本   人手操作
y 大版本     人手操作
z 大功能版本  功能清单全部完成并有验证后才升 z
w 小版本     CRUD / 修正，agent 可操作
```

功能清单未完结期间，只升 w：`0.0.1.1`、`0.0.1.2`……

---

## 0.0.1.5 — 2026-10-12（新增流程技能与仓库开工说明）

- **新增 `skills/defect-loop-review/`**（流程技能，零代码）：缺陷闭环审核。
  三段式——广度出缺陷总表、深度用五步追问挖规则、验证只审增量；收敛看净流入
  （本轮新发现 A/B − 本轮修复造成 A/B），不设轮次上限，设四条停手信号。
  含 `references/` 三件模板：判据卡、缺陷总表、规则与净流入。
  来源：《毒与证》五轮审核实战（`H:\Works\ScienceFound\docs\写作与审核流程.md`）。
- **新增 `AGENTS.md`**：仓库开工说明。硬纪律、目录约定、技能包写法、审核流程、版本规则、禁止事项。
- **修正 `README.md` 目录说明**：原文写 `skills/` 下有四个工具技能，实际它们在 `docs/cli/`。
  现改为两类技能分列——工具技能在 `docs/cli/`，流程技能在 `skills/`，并说明为什么分开。

## 0.0.1.4 — 2026-11-21（分层重构：能力层收口）

- **新增 `sv audio-slice`**（采样精确切块）：MP3 一次解码为 48k/16bit/mono PCM 母版，
  按整数采样下标切片，**重组必须与母版逐字节一致**。来自 VideoPrj 的 `audio_slice_exact.py`，
  现为唯一实现。真实素材验证：《浮沉歌》50 块（2×8s + 48×5s = 256s），
  `continuous_matches_master = true`，解码 12,288,000 采样。
- **新增 `sv grain` / `sv grain-metrics`**：来自 VideoPrj 的 `film_grain.py` + `grain_metrics.py`。
- **`skills/` 改名 `docs/cli/`**：让 "skills" 这个词只属于 VideoPrj。
- 测试从 7 条增到 **11 条**。
- 依赖方向确立：**VideoPrj → SignalVerify，单向**。

## 0.0.1.3 — 2026-11-21

- **补上 `skills/` 目录**。此前 README 的目录树里写了 `skills/`，但仓库里根本不存在——
  这是文档与实际不一致，用户追问才发现。现在按"薄壳"补齐 4 个技能：
  `audio-lyric-timing` / `video-lip-sync` / `image-face-grid` / `frame-sheet`，
  外加 `skills/README.md` 索引。
- README 目录树改为与实际一致，并写明"库负责算、skills 负责教"。

## 0.0.1.2 — 2026-11-21

- 新增 `sv face-grid`：面相"王"字格量化（眼线角、唇线角、两线夹角、左右受光差、半脸对称度、方正度 0–10）。
  实测能区分"方正"与"偏邪"的样张（8.2 / 7.8 / 7.0，与人工判断同序）。
  只用于**评审**，明确标注不得写进生成提示词。
- 明确 `left_right_light_balance_norm` 的语义：它反映"光是否压暗一侧"，**不是**鼻梁歪斜；
  真鼻轴需要关键点模型，本库没有，不谎称。

## 0.0.1.1 — 2026-11-20

- 修正版本号：`0.1.0` → `0.0.1`。理由：x/y 属人手操作，agent 不得自行升到 0.1。
- 命令名 `sv` 改为 `signalverify`。理由：纪律要求见名知意，禁止缩写。
- 补类型注解与结构化日志（诊断走 logging，stdout 只留 JSON 产物）。
- 新增 `docs/工程纪律对照.md`。

## 0.0.1 — 2026-11-20

- 首次提交：core（ffmpeg 封装 / 报告信封 / probe）、audio（歌词时间码 / 口型偏移）、
  visual（联络单）、7 个确定性测试。
- 已推送 https://github.com/redcool/SimpleAgentSignalVerify
