#!/usr/bin/env python3
"""Build the two review images the deliverable ships with.

 · downloads/spot_diff_app_preview.png  — real app screenshots (actual Chromium captures)
 · downloads/spot_diff_stages_sheet.png — all five stages, original vs modified with the
   numbered answer circles drawn from the verified coordinates
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

FONT_KR = "/usr/share/fonts/pickle-hwp/NotoSansCJKkr-Regular.otf"
SHOTS = "_review/shots"
OUT_DIR = os.path.join("..", "..", "downloads")

CREAM = (255, 246, 234)
INK = (74, 58, 49)
SOFT = (139, 116, 102)
CORAL = (227, 84, 58)


def f(size):
    return ImageFont.truetype(FONT_KR, size)


def center_text(d, text, cx, y, font, fill):
    w = d.textlength(text, font=font)
    d.text((cx - w / 2, y), text, font=font, fill=fill)


def phone_shot(path, width):
    im = Image.open(path).convert("RGB")
    h = int(im.height * width / im.width)
    im = im.resize((width, h), Image.LANCZOS)
    # rounded corners
    from PIL import ImageDraw as _D
    mask = Image.new("L", (width * 3, h * 3), 0)
    _D.Draw(mask).rounded_rectangle([0, 0, width * 3 - 1, h * 3 - 1], radius=int(width * 3 * 0.075), fill=255)
    mask = mask.resize((width, h), Image.LANCZOS)
    out = Image.new("RGB", (width, h), "white")
    out.paste(im, (0, 0))
    return out, mask


def make_preview():
    panels = [
        (f"{SHOTS}/01_home.png", "스테이지 선택"),
        (f"{SHOTS}/02_game.png", "게임 플레이"),
        (f"{SHOTS}/05_clear_modal.png", "클리어 결과"),
    ]
    pw = 320
    shots = []
    for path, label in panels:
        im = Image.open(path).convert("RGB")
        h = int(im.height * pw / im.width)
        shots.append((im.resize((pw, h), Image.LANCZOS), label))
    gap = 26
    pad = 40
    head = 92
    body_h = max(s[0].height for s in shots)
    W = pad * 2 + pw * 3 + gap * 2
    H = head + body_h + 56 + pad
    canvas = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(canvas)
    # soft top accent
    for y in range(0, 220):
        a = int(28 * (1 - y / 220))
        d.line([(0, y), (W, y)], fill=(255, 236, 214 + a % 20))
    center_text(d, "틀린그림찾기 — 모바일 앱 화면", W / 2, 26, f(34), INK)
    center_text(d, "실제 앱을 크로미움(390×844)에서 실행해 캡처한 화면입니다", W / 2, 68, f(15), SOFT)

    for i, (im, label) in enumerate(shots):
        x = pad + i * (pw + gap)
        y = head + (body_h - im.height) // 2
        shadow = Image.new("RGB", (pw + 16, im.height + 16), CREAM)
        canvas.paste((228, 210, 190), (x - 4, y - 2, x + pw + 8, y + im.height + 10))
        canvas.paste(im, (x, y))
        d.rectangle([x - 1, y - 1, x + pw, y + im.height], outline=(226, 205, 184))
        center_text(d, label, x + pw / 2, y + im.height + 14, f(17), INK)
    os.makedirs(OUT_DIR, exist_ok=True)
    canvas.save(os.path.join(OUT_DIR, "spot_diff_app_preview.png"), optimize=True)
    print("preview:", canvas.size)


def draw_marks(img, marks, scale=1.0):
    d = ImageDraw.Draw(img)
    for i, m in enumerate(marks, 1):
        cx, cy = m["px"][0] * scale, m["px"][1] * scale
        rx, ry = m["rx"] * 800 * scale, m["ry"] * 600 * scale
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=(255, 59, 92), width=4)
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=(255, 255, 255), width=1)
        tx, ty = cx - rx * 0.72, cy - ry - 20
        d.ellipse([tx - 11, ty - 11, tx + 11, ty + 11], fill=(255, 59, 92), outline="white", width=2)
        w = d.textlength(str(i), font=f(15))
        d.text((tx - w / 2, ty - 9), str(i), font=f(15), fill="white")
    return img


def make_stages_sheet():
    rep = json.load(open("_review/build_report.json"))
    titles = {
        "stage_01": ("1. 아늑한 한옥 카페", "쉬움 · 90초"),
        "stage_02": ("2. 정겨운 과일가게", "쉬움 · 90초"),
        "stage_03": ("3. 바닷가 등대 캠핑", "보통 · 80초"),
        "stage_04": ("4. 고양이 서점", "보통 · 80초"),
        "stage_05": ("5. 밤하늘 포장마차", "어려움 · 75초"),
    }
    cw, ch = 400, 300
    gap, pad, head, lab = 18, 36, 96, 34
    W = pad * 2 + cw * 2 + gap
    H = head + 5 * (ch + lab + gap) + pad
    canvas = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(canvas)
    center_text(d, "틀린그림찾기 — 5개 스테이지 미리보기", W / 2, 24, f(30), INK)
    center_text(d, "왼쪽 원본 / 오른쪽 다른 그림 (빨간 동그라미 = 정답 5곳)", W / 2, 62, f(15), SOFT)

    for row, sid in enumerate(["stage_01", "stage_02", "stage_03", "stage_04", "stage_05"]):
        a = Image.open(f"assets/stages/{sid}_a.png").convert("RGB").resize((cw, ch), Image.LANCZOS)
        b = Image.open(f"assets/stages/{sid}_b.png").convert("RGB").resize((cw, ch), Image.LANCZOS)
        draw_marks(b, rep[sid]["marks"], scale=cw / 800.0)
        y = head + row * (ch + lab + gap)
        canvas.paste(a, (pad, y))
        canvas.paste(b, (pad + cw + gap, y))
        d.rectangle([pad - 1, y - 1, pad + cw, y + ch], outline=(226, 205, 184))
        d.rectangle([pad + cw + gap - 1, y - 1, pad + cw * 2 + gap, y + ch], outline=(226, 205, 184))
        title, meta = titles[sid]
        d.text((pad, y + ch + 6), title, font=f(20), fill=INK)
        d.text((pad + cw + gap - d.textlength(meta, font=f(16)) - 2, y + ch + 10), meta, font=f(16), fill=CORAL)
    canvas.save(os.path.join(OUT_DIR, "spot_diff_stages_sheet.png"), optimize=True)
    print("stages sheet:", canvas.size)


if __name__ == "__main__":
    make_preview()
    make_stages_sheet()
