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

## 0.0.1.1 — 2026-11-20

- 修正版本号：`0.1.0` → `0.0.1`。理由：x/y 属人手操作，agent 不得自行升到 0.1。
- 命令名 `sv` 改为 `signalverify`。理由：纪律要求见名知意，禁止缩写。
- 补类型注解与结构化日志（诊断走 logging，stdout 只留 JSON 产物）。
- 新增 `docs/工程纪律对照.md`。

## 0.0.1 — 2026-11-20

- 首次提交：core（ffmpeg 封装 / 报告信封 / probe）、audio（歌词时间码 / 口型偏移）、
  visual（联络单）、7 个确定性测试。
- 已推送 https://github.com/redcool/SimpleAgentSignalVerify
