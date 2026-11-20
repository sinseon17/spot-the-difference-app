#!/usr/bin/env python3
"""Build the final "different" image for each stage.

An AI edit pass redraws the whole picture, so it leaves faint noise everywhere and
sometimes merges two intended changes into one blob. This script keeps the edit's
pixels only inside five hand-picked windows, one per intended difference, and
composites those patches back onto the untouched original with a soft feathered
edge. The result differs from the original in exactly five places, and nothing else.

Usage: python3 scripts/build_stage_b.py [--report _review/build_report.json]
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_diff import diff_mask, load, regions  # noqa: E402

IMG = "assets/stages"
# Five windows per stage, one per intended difference (x0, y0, x1, y1) in 800x600 px.
WINDOWS = {
    "stage_01": [
        ("종이등 색", (20, 78, 86, 139)),
        ("선인장", (712, 185, 800, 400)),
        ("빨간 주전자", (130, 402, 228, 468)),
        ("꽃병 사라짐", (292, 410, 355, 492)),
        ("자는 고양이", (360, 478, 514, 572)),
    ],
    "stage_02": [
        ("가지", (410, 346, 584, 455)),
        ("배", (74, 444, 246, 531)),
        ("바나나 사라짐", (629, 180, 725, 301)),
        ("하얀 고양이", (715, 427, 798, 543)),
        ("거울", (352, 190, 434, 275)),
    ],
    "stage_03": [
        ("빨간 텐트", (86, 316, 408, 566)),
        ("분홍 등대 불빛", (600, 53, 664, 106)),
        ("파란 등대 문", (602, 235, 640, 285)),
        ("갈매기", (428, 34, 542, 100)),
        ("노란 의자", (3, 435, 122, 545)),
    ],
    "stage_04": [
        ("책 더미", (303, 498, 460, 600)),
        ("창가 화분 사라짐", (115, 176, 261, 315)),
        ("회색 고양이", (134, 336, 283, 439)),
        ("빨간 갓등", (340, 28, 461, 90)),
        ("흰 데이지", (729, 315, 800, 382)),
    ],
    "stage_05": [
        ("등 하나 더", (26, 115, 110, 260)),
        ("빨간 모자", (201, 183, 290, 235)),
        ("초승달", (622, 28, 682, 90)),
        ("사라진 소품", (719, 322, 784, 381)),
        ("별똥별", (472, 70, 523, 104)),
    ],
}


def window_mask(dm, box, full=False):
    x0, y0, x1, y1 = box
    m = np.zeros_like(dm)
    m[y0:y1, x0:x1] = 255 if full else dm[y0:y1, x0:x1]
    if not full:
        # keep only the real change, drop redraw speckle of the same window
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        if n > 1:
            areas = [(stats[i][4], i) for i in range(1, n)]
            biggest = max(a for a, _ in areas)
            keep = np.zeros_like(m)
            for area, i in areas:
                if area >= max(60, 0.22 * biggest):
                    keep[lab == i] = 255
            m = keep
    # ignore isolated redraw speckle inside the window, keep the real change
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    return m


def feather(mask, grow=9, blur=13):
    m = cv2.dilate(mask, np.ones((grow, grow), np.uint8), iterations=1)
    a = cv2.GaussianBlur(m, (blur | 1, blur | 1), 0).astype(np.float32) / 255.0
    return a[..., None]


def ellipse_of(mask, pad=10):
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    rx = (x1 - x0 + 1) / 2.0 + pad
    ry = (y1 - y0 + 1) / 2.0 + pad
    return {
        "x": round(cx / 800.0, 4),
        "y": round(cy / 600.0, 4),
        "r": round(max(rx / 800.0, ry / 600.0), 4),
        "rx": round(min(rx / 800.0, 0.33), 4),
        "ry": round(min(ry / 600.0, 0.33), 4),
        "box": [x0, y0, x1 - x0 + 1, y1 - y0 + 1],
        "px": [int(round(cx)), int(round(cy))],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="_review/build_report.json")
    args = ap.parse_args()

    report = {}
    ok = True
    for stage, wins in WINDOWS.items():
        a = load(f"{IMG}/{stage}_a.png")
        raw = load(f"{IMG}/{stage}_b_raw.png")
        dm, _ = diff_mask(a, raw)

        alpha_total = np.zeros((600, 800), np.float32)
        marks, used = [], []
        for label, box in wins:
            m = window_mask(dm, box)
            if m.sum() == 0:
                print(f"!! {stage} / {label}: nothing changed inside {box}")
                ok = False
                continue
            el = ellipse_of(m)
            marks.append({"label": label, **el})
            used.append(label)
            alpha_total = np.maximum(alpha_total, feather(m)[..., 0])

        alpha3 = alpha_total[..., None]
        out = (a.astype(np.float32) * (1 - alpha3) + raw.astype(np.float32) * alpha3)
        out = np.clip(out, 0, 255).astype(np.uint8)
        cv2.imwrite(f"{IMG}/{stage}_b.png", out)

        # --- verification: the composite must differ in exactly five places ---
        dm2, d2 = diff_mask(a, out)
        regs = regions(dm2)
        status = "OK" if len(regs) == 5 else "FAIL"
        if len(regs) != 5:
            ok = False
        print(f"{stage}: {len(used)}/5 windows applied, composite shows {len(regs)} region(s) -> {status}")
        for i, r in enumerate(regs):
            print(f"   [{i}] area={r['area']:6d} box=({r['x']},{r['y']},{r['w']}x{r['h']}) "
                  f"center=({r['cx']:.0f},{r['cy']:.0f})")
        report[stage] = {"status": status, "regions": regs, "marks": marks,
                         "windows": [{"label": l, "box": b} for l, b in wins]}

    with open(args.report, "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print("report ->", args.report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
