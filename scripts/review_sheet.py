#!/usr/bin/env python3
"""Debug review sheets: original vs modified with the answer circles drawn, plus a
zoom of every single difference so each one can be checked by eye.

Usage: python3 scripts/review_sheet.py
Outputs: _review/review_<stage>.png, _review/diff_zoom_sheet.png, downloads/spot_diff_stages_sheet.png
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

IMG = "assets/stages"
OUT = "_review"

CIRCLED = [
    "stage_01", "stage_02", "stage_03", "stage_04", "stage_05",
]


def font(size):
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def draw_marks(img, marks, color=(255, 59, 92)):
    d = ImageDraw.Draw(img)
    for i, m in enumerate(marks, 1):
        cx, cy = m["px"]
        rx = m["rx"] * 800
        ry = m["ry"] * 600
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=color, width=4)
        d.text((cx - rx + 4, cy - ry - 16), str(i), fill=color, font=font(18))
    return img


def main():
    rep = json.load(open(os.path.join(OUT, "build_report.json")))

    # 1) per stage: a | b(circled)
    for stage in CIRCLED:
        a = Image.open(f"{IMG}/{stage}_a.png").convert("RGB")
        b = Image.open(f"{IMG}/{stage}_b.png").convert("RGB")
        marks = rep[stage]["marks"]
        bc = draw_marks(b.copy(), marks)
        sheet = Image.new("RGB", (800, 1240), "white")
        sheet.paste(a, (0, 20))
        sheet.paste(bc, (0, 640))
        d = ImageDraw.Draw(sheet)
        d.text((6, 2), "ORIGINAL", fill="black", font=font(16))
        d.text((6, 622), "MODIFIED (answer circles)", fill="black", font=font(16))
        sheet.save(f"{OUT}/review_{stage}.png")

    # 2) zoom sheet: each difference as its own original|modified pair, 5 stages x 5
    cw, ch, scale = 84, 63, 2
    pad = 6
    pair_w, pair_h = cw * 2 * scale, ch * scale
    head = 20
    sheet = Image.new("RGB", (5 * (pair_w + pad) + pad, 5 * (pair_h + head + pad) + pad), "#efe9dd")
    d = ImageDraw.Draw(sheet)
    for row, stage in enumerate(CIRCLED):
        a = Image.open(f"{IMG}/{stage}_a.png").convert("RGB")
        b = Image.open(f"{IMG}/{stage}_b.png").convert("RGB")
        marks = rep[stage]["marks"]
        for col, m in enumerate(marks):
            cx, cy = m["px"]
            box = (max(0, min(800 - cw, cx - cw // 2)), max(0, min(600 - ch, cy - ch // 2)),
                   None, None)
            box = (box[0], box[1], box[0] + cw, box[1] + ch)
            ca = a.crop(box).resize((cw * scale, ch * scale), Image.LANCZOS)
            cb = b.crop(box).resize((cw * scale, ch * scale), Image.LANCZOS)
            x = pad + col * (pair_w + pad)
            y = pad + row * (pair_h + head + pad)
            sheet.paste(ca, (x, y + head - 4))
            sheet.paste(cb, (x + cw * scale + 2, y + head - 4))
            d.rectangle([x + cw * scale, y + head - 4, x + cw * scale + 1, y + head - 4 + ch * scale],
                        fill="#ff3b5c")
            d.text((x, y - 2), f"{stage[-2:]}·{col + 1} {m['label']}", fill="black", font=font(11))
    sheet.save(f"{OUT}/diff_zoom_sheet.png")
    print("review sheets written")


if __name__ == "__main__":
    main()
