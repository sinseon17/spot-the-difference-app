#!/usr/bin/env python3
"""Compare stage_0X_a.png and stage_0X_b.png and report distinct difference regions.

Usage: python3 scripts/analyze_diff.py <a.png> <b.png> [--json out.json] [--debug out.png]
"""
import argparse
import json
import sys

import cv2
import numpy as np


def load(path, size=(800, 600)):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"cannot read {path}")
    if (img.shape[1], img.shape[0]) != size:
        img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    return img


def diff_mask(a, b, threshold=26, blur=5):
    """Per-pixel difference mask that ignores smooth global resampling drift."""
    af = cv2.GaussianBlur(a.astype(np.float32), (blur, blur), 0)
    bf = cv2.GaussianBlur(b.astype(np.float32), (blur, blur), 0)
    d = np.abs(af - bf).max(axis=2)
    mask = (d > threshold).astype(np.uint8) * 255
    # close small gaps inside a changed object, then drop speckle
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return mask, d


def regions(mask, min_area=140):
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < min_area:
            continue
        out.append({
            "x": int(x), "y": int(y), "w": int(w), "h": int(h), "area": int(area),
            "cx": float(centroids[i][0]), "cy": float(centroids[i][1]),
        })
    out.sort(key=lambda r: -r["area"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--json")
    ap.add_argument("--debug")
    ap.add_argument("--threshold", type=float, default=26)
    ap.add_argument("--min-area", type=int, default=140)
    args = ap.parse_args()

    a = load(args.a)
    b = load(args.b)
    mask, d = diff_mask(a, b, args.threshold)
    regs = regions(mask, args.min_area)

    print(f"{args.a} vs {args.b}: {len(regs)} region(s), max diff {d.max():.0f}, "
          f"changed px {int((mask > 0).sum())}")
    for i, r in enumerate(regs):
        print(f"  [{i}] area={r['area']:6d} box=({r['x']},{r['y']},{r['w']}x{r['h']}) "
              f"center=({r['cx']:.0f},{r['cy']:.0f})")

    if args.debug:
        vis = b.copy()
        for i, r in enumerate(regs):
            cv2.rectangle(vis, (r["x"], r["y"]), (r["x"] + r["w"], r["y"] + r["h"]), (0, 0, 255), 2)
            cv2.putText(vis, str(i), (r["x"] + 3, r["y"] + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
        cv2.imwrite(args.debug, vis)

    if args.json:
        with open(args.json, "w") as f:
            json.dump(regs, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
