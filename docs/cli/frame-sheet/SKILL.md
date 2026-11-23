---
name: frame-sheet
description: 把视频按固定时间点抽帧、拼成一张带时间码的联络单，用于人工或视觉模型审片。
---

# frame-sheet

## 什么时候用

- 要把"后半段有问题"变成"第 3.50 秒那条";
- 视觉模型被压到 768px 宽，整帧看等于没看，需要拼图+时间码；
- 要给用户一张能一眼扫完整条片子的图。

## 命令

```bash
signalverify frame-sheet --video take.mp4 --count 12 --cols 4 --out sheet.png
signalverify frame-sheet --video take.mp4 --times 0,0.5,1,2,4,6,8,9.5 --out sheet.png
```

## 局限

- 时间码是**请求时间**，实际帧可能偏一帧，不要在 ±0.05 秒上做文章；
- 联络单只能看"形态"，看不到逐字口型；口型判定要靠人耳 + 原速播放。
