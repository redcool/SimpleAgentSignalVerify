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
