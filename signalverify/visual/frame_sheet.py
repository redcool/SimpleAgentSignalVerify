"""把视频按固定时间点抽帧、拼成带时间码的联络单。

为什么：视觉模型常被压到 768px 宽，整帧看细节等于没看。
拼成联络单并标上时间码，审片者才能对着"第 3.50 秒"说话，而不是笼统说"后半段"。
"""
from pathlib import Path

import cv2
import numpy as np


def build_frame_sheet(video, out, times=None, count=12, cols=4, tile_width=480):
    cap = cv2.VideoCapture(str(video))
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    duration = total / fps if total else 0.0
    if not times:
        times = [duration * (i + 0.5) / count for i in range(count)]

    tiles = []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000)
        ok, im = cap.read()
        if not ok:
            continue
        h, w = im.shape[:2]
        im = cv2.resize(im, (tile_width, int(h * tile_width / float(w))),
                        interpolation=cv2.INTER_AREA)
        bar = np.zeros((28, im.shape[1], 3), np.uint8)
        cv2.putText(bar, "%.2fs" % t, (6, 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(np.vstack([bar, im]))
    cap.release()
    if not tiles:
        raise ValueError("no frames decoded from %s" % video)

    rows = (len(tiles) + cols - 1) // cols
    th, tw = tiles[0].shape[:2]
    canvas = np.full((rows * th + (rows + 1) * 6, cols * tw + (cols + 1) * 6, 3), 24, np.uint8)
    for i, tile in enumerate(tiles):
        r, c = divmod(i, cols)
        canvas[6 + r * (th + 6):6 + r * (th + 6) + th,
               6 + c * (tw + 6):6 + c * (tw + 6) + tw] = tile
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(p), canvas)
    return {"out": str(p), "frames": len(tiles), "bytes": p.stat().st_size}
