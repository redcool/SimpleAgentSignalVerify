"""歌词逐句时间码。

核心立场：时间码可信度 = 人工确认 > 权威歌词+ASR强制对齐 > 纯ASR > 按拍/能量猜。
本模块做第二档：用歌词文本当靶子，把 ASR 的时间信息强制对齐上去。
ASR 认错字不要紧，只要没整段漏掉，对齐后每句起点仍然可信。

依赖：ASR 由外部后端提供（`sv lyric-timing transcribe`，需要 transformers），
本模块本身只做文本与对齐的纯计算，无重依赖。
"""
import json
import re
import wave
from pathlib import Path

CJK = re.compile(r"[\u3400-\u9fff]")


def parse_lyrics(path):
    """解析歌词：丢掉 [Section]，返回 [{section, line, chars}]。"""
    lines, section = [], ""
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s:
            continue
        m = re.match(r"^[\[【(（]\s*(.+?)\s*[\]】)）]$", s)
        if m:
            section = m.group(1)
            continue
        chars = CJK.findall(s) or [c for c in re.sub(r"[^\w]", "", s)]
        if chars:
            lines.append({"section": section, "line": s, "chars": chars})
    return lines


def asr_char_times(asr):
    """把 ASR chunk 摊平成逐字时间。chunk 内部按字数等分——精度只到句级。"""
    rows = []
    for c in asr.get("chunks", []):
        t = c.get("timestamp") or [None, None]
        if t[0] is None:
            continue
        chars = CJK.findall(c["text"])
        if not chars:
            continue
        s = float(t[0])
        e = float(t[1] if t[1] is not None else t[0])
        if e <= s:
            e = s + 0.12 * len(chars)
        step = (e - s) / len(chars)
        for i, ch in enumerate(chars):
            rows.append({"ch": ch, "start": round(s + i * step, 3),
                         "end": round(s + (i + 1) * step, 3)})
    return rows


def align_global(A, B, gap=1.4):
    """A=歌词字符, B=ASR字符；返回 A 每位的 B 下标或 None（单调，不允许交叉）。"""
    n, m = len(A), len(B)
    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    bt = [[0] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            cur = dp[i][j]
            if cur == INF:
                continue
            if i < n and j < m:
                c = cur + (0.0 if A[i] == B[j] else 1.0)
                if c < dp[i + 1][j + 1]:
                    dp[i + 1][j + 1], bt[i + 1][j + 1] = c, 1
            if i < n:
                c = cur + gap
                if c < dp[i + 1][j]:
                    dp[i + 1][j], bt[i + 1][j] = c, 2
            if j < m:
                c = cur + gap
                if c < dp[i][j + 1]:
                    dp[i][j + 1], bt[i][j + 1] = c, 3
    map_a = [None] * n
    i, j = n, m
    while i > 0 or j > 0:
        step = bt[i][j]
        if step == 1:
            map_a[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif step == 2:
            i -= 1
        elif step == 3:
            j -= 1
        else:
            break
    return map_a, dp[n][m]


def build_timing(lines, times, gap=1.4, adjust_duration=True):
    """把歌词行对齐到逐字时间，产出每句 start/end + 每句 ASR 命中率。"""
    A, owner = [], []
    for li, ln in enumerate(lines):
        for ch in ln["chars"]:
            A.append(ch)
            owner.append(li)
    B = [r["ch"] for r in times]
    map_a, cost = align_global(A, B, gap=gap)

    rows = []
    matched = mismatched = unmatched = 0
    for li, ln in enumerate(lines):
        idx = [k for k, o in enumerate(owner) if o == li]
        hits = [(A[k], times[map_a[k]]) for k in idx if map_a[k] is not None]
        line_match = sum(1 for ch, t in hits if ch == t["ch"])
        matched += line_match
        mismatched += sum(1 for ch, t in hits if ch != t["ch"])
        unmatched += sum(1 for k in idx if map_a[k] is None)
        rows.append({
            "index": li, "section": ln["section"], "text": ln["line"],
            "chars": [{"ch": ch, "start": t["start"], "end": t["end"], "asr": t["ch"]}
                      for ch, t in hits],
            "start": hits[0][1]["start"] if hits else None,
            "end": hits[-1][1]["end"] if hits else None,
            "char_count": len(ln["chars"]),
            "asr_rate": round(line_match / len(ln["chars"]), 3) if ln["chars"] else 0.0,
        })

    for i, row in enumerate(rows):
        if row["start"] is not None:
            continue
        prev = next((rows[k]["end"] for k in range(i - 1, -1, -1)
                     if rows[k]["end"] is not None), 0.0)
        nxt = next((rows[k]["start"] for k in range(i + 1, len(rows))
                    if rows[k]["start"] is not None), None)
        row["start"] = round(prev, 3)
        row["end"] = round(nxt if nxt is not None else prev, 3)
        row["interpolated"] = True

    rate = 0.30
    if adjust_duration:
        rates = sorted((r["end"] - r["start"]) / r["char_count"]
                       for r in rows
                       if not r.get("interpolated") and r["end"] and r["char_count"] >= 2
                       and (r["end"] - r["start"]) > 0.3)
        if rates:
            rate = rates[len(rates) // 2]
        limited = 0
        for i, row in enumerate(rows):
            if row["end"] is None or row["char_count"] == 0:
                continue
            expect = rate * row["char_count"]
            dur = row["end"] - row["start"]
            lo, hi = 0.55 * expect, 1.9 * expect
            if dur < lo or dur > hi:
                nxt = next((rows[k]["start"] for k in range(i + 1, len(rows))
                            if rows[k]["start"] is not None), None)
                new_end = row["start"] + max(lo, min(hi, expect))
                if nxt is not None:
                    new_end = min(new_end, nxt)
                new_end = max(new_end, row["start"] + 0.3)
                row["raw_end"] = row["end"]
                row["end"] = round(new_end, 3)
                row["duration_adjusted"] = True
                limited += 1
        adjusted = limited
    else:
        adjusted = 0

    total = matched + mismatched + unmatched
    qa = {
        "lyric_chars": total, "asr_chars": len(B),
        "char_match": matched, "char_mismatch": mismatched, "char_unmatched": unmatched,
        "match_rate": round(matched / total, 4) if total else 0.0,
        "dp_cost": round(cost, 2),
        "seconds_per_char_median": round(rate, 3),
        "duration_adjusted_lines": adjusted,
        "weak_lines": [r["index"] for r in rows if r["asr_rate"] < 0.5 or r.get("interpolated")],
        "note": "match_rate 反映 ASR 认字准确度，不等于时间准确度；weak_lines 必须人工复核。",
    }
    return rows, qa


def build_segments(rows, min_duration=4.0, max_duration=15.0,
                   preroll=0.35, postroll=0.30, max_gap=0.9):
    """按整句切段。句中起唱=模型没有起唱参照=口型必然错，所以绝不从句子中间切。"""
    usable = [r for r in rows
              if r["start"] is not None and r["end"] is not None and not r.get("interpolated")]
    groups, cur = [], None
    for r in usable:
        r_start = max(0.0, r["start"] - preroll)
        if cur is None:
            cur = {"lines": [r], "start": r_start, "end": r["end"]}
            continue
        gap = r["start"] - cur["end"]
        if (r["end"] - cur["start"]) <= max_duration and gap <= max_gap:
            cur["lines"].append(r)
            cur["end"] = r["end"]
        else:
            groups.append(cur)
            cur = {"lines": [r], "start": r_start, "end": r["end"]}
    if cur:
        groups.append(cur)

    out, prev_end = [], -1.0
    for i, g in enumerate(groups):
        start = max(0.0, g["start"] - preroll)
        if start <= prev_end:          # 不许重叠：宁可牺牲 preroll
            start = prev_end
        end = g["end"] + postroll
        if end - start < min_duration:
            end = start + min_duration
        prev_end = end
        out.append({
            "id": "s%02d" % (i + 1),
            "start": round(start, 3), "end": round(end, 3),
            "duration": round(end - start, 3),
            "lines": [{"text": l["text"], "start": l["start"],
                       "local_start": round(l["start"] - start, 3),
                       "end": l["end"], "local_end": round(l["end"] - start, 3)}
                      for l in g["lines"]],
            "lyric_text": "｜".join(l["text"] for l in g["lines"]),
        })
    return out
