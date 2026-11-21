"""面相"王"字格量化：三条水平线 + 一条中线，量它们有多"方正"。

用途：**评审**，不是生成。给一张正面人像，输出
  eye_angle      两瞳孔连线的倾角（度，正值=右高左低）
  mouth_angle    两嘴角连线的倾角
  parallel_gap   两条线的夹角差（应接近 0）
  light_balance  左右半脸平均亮度差（反映"光是否压暗一侧"，**不是**鼻梁歪斜）
  symmetry       左右半脸的结构差异（0=完全对称）
  squareness     综合方正度 0-10

局限（必须写进报告）：
  - 依赖 Haar 级联，侧脸/低头/遮挡会丢检测；
  - 没有关键点模型，中线与嘴角是"估计"，不是解剖测量；
  - 本工具**测不出**鼻梁是否真的歪，只能给出左右受光差；
  - 目测与测量在 2 度以内不可分辨，不要拿小数点论输赢。
"""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class FaceGrid:
    eye_angle: float | None
    mouth_angle: float | None
    parallel_gap: float | None
    light_balance: float | None
    symmetry: float | None
    squareness: float
    face_box: tuple[int, int, int, int] | None
    eyes_found: int


def _angle_deg(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    if abs(dx) < 1e-6:
        return 90.0
    return float(np.degrees(np.arctan2(dy, dx)))


def _mouth_line(gray, box):
    """在下半脸找"暗带"（嘴缝），返回左右两端点与倾角。"""
    x, y, w, h = box
    y0, y1 = int(y + h * 0.55), int(y + h * 0.85)
    x0, x1 = int(x + w * 0.22), int(x + w * 0.78)
    roi = gray[y0:y1, x0:x1].astype(np.float32)
    if roi.size == 0:
        return None, None, None
    # 每一行取中位数亮度，找到最暗的一段作为唇缝
    rows = np.median(roi, axis=1)
    thr = rows.mean() - 0.8 * rows.std()
    dark = np.where(rows < thr)[0]
    if len(dark) == 0:
        return None, None, None
    # 取最暗行作为唇缝基准，再分左右两半各自找该区域的暗带中心
    seam = dark[np.argmin(rows[dark])]
    band = max(2, int(len(rows) * 0.12))
    lo, hi = max(0, seam - band), min(rows.shape[0], seam + band + 1)
    half = roi.shape[1] // 2
    ys = []
    for seg in (roi[lo:hi, :half], roi[lo:hi, half:]):
        m = seg.mean(axis=1)
        ys.append(float(np.argmin(m)))
    left_y = y0 + lo + ys[0]
    right_y = y0 + lo + ys[1]
    left_p = (x0, left_y)
    right_p = (x1, right_y)
    return left_p, right_p, _angle_deg(left_p, right_p)


def _symmetry(gray, box):
    x, y, w, h = box
    roi = gray[y:y + h, x:x + w].astype(np.float32)
    if roi.size == 0:
        return None
    left = roi[:, : w // 2]
    right = np.fliplr(roi[:, w - (w // 2):])
    n = min(left.shape[1], right.shape[1])
    left, right = left[:, :n], right[:, :n]
    denom = (left.std() + right.std()) / 2 + 1e-6
    return float(np.mean(np.abs(left - right)) / denom)


def measure(image_path):
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("cannot read image: %s" % image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    cas_face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cas_eye = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

    faces = cas_face.detectMultiScale(gray, 1.08, 5, minSize=(120, 120))
    if len(faces) == 0:
        return FaceGrid(None, None, None, None, None, 0.0, None, 0)
    box = tuple(int(v) for v in max(faces, key=lambda q: q[2] * q[3]))
    x, y, w, h = box

    upper = gray[y:y + int(h * 0.6), x:x + w]
    eyes = cas_eye.detectMultiScale(upper, 1.08, 6, minSize=(max(12, w // 12), max(12, w // 12)))
    eye_angle = None
    if len(eyes) >= 2:
        eyes = sorted(eyes, key=lambda e: e[2] * e[3], reverse=True)[:2]
        centers = sorted([(x + e[0] + e[2] / 2, y + e[1] + e[3] / 2) for e in eyes],
                         key=lambda c: c[0])
        eye_angle = _angle_deg(centers[0], centers[1])

    left_p, right_p, mouth_angle = _mouth_line(gray, box)
    parallel_gap = None
    if eye_angle is not None and mouth_angle is not None:
        parallel_gap = abs(eye_angle - mouth_angle)

    # 左右受光平衡：只反映"光是否把一侧压暗"，不代表鼻梁真的歪。
    # 真鼻梁轴线需要关键点模型，本工具没有，所以不谎称它是鼻轴偏移。
    roi = gray[y:y + h, x:x + w].astype(np.float32)
    left = roi[:, : w // 2]
    right = roi[:, w - (w // 2):]
    light_balance = None
    if left.size and right.size:
        diff = float(left.mean() - right.mean())
        light_balance = round(diff / 255.0, 4)

    sym = _symmetry(gray, box)

    # 综合分：角度项主导，平行与对称次之
    score = 10.0
    if eye_angle is not None:
        score -= min(4.0, abs(eye_angle) * 0.8)
    if mouth_angle is not None:
        score -= min(4.0, abs(mouth_angle) * 0.8)
    if parallel_gap is not None:
        score -= min(2.0, parallel_gap * 0.4)
    if sym is not None:
        score -= min(2.0, sym * 2.0)
    score = max(0.0, min(10.0, score))

    return FaceGrid(
        eye_angle=None if eye_angle is None else round(eye_angle, 2),
        mouth_angle=None if mouth_angle is None else round(mouth_angle, 2),
        parallel_gap=None if parallel_gap is None else round(parallel_gap, 2),
        light_balance=light_balance,
        symmetry=None if sym is None else round(sym, 3),
        squareness=round(score, 1),
        face_box=box,
        eyes_found=len(eyes),
    )


def to_dict(grid: FaceGrid):
    return {
        "eye_angle_deg": grid.eye_angle,
        "mouth_angle_deg": grid.mouth_angle,
        "parallel_gap_deg": grid.parallel_gap,
        "left_right_light_balance_norm": grid.light_balance,
        "half_face_symmetry": grid.symmetry,
        "squareness_0_10": grid.squareness,
        "face_box": grid.face_box,
        "eyes_found": grid.eyes_found,
    }
