#!/usr/bin/env python3
"""Derive every icon size the PWA and the Android package need from one master image."""
import os

from PIL import Image, ImageFilter

SRC = "assets/icon/icon_raw2.png"
OUT = "www/icons"
MASTER = "assets/icon/icon-512.png"


def rounded(img, radius_ratio=0.22):
    from PIL import ImageDraw
    w, h = img.size
    mask = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius=int(w * 4 * radius_ratio), fill=255)
    mask = mask.resize((w, h), Image.LANCZOS)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs("assets/icon", exist_ok=True)
    src = Image.open(SRC).convert("RGB")
    # square crop from the centre, then scale
    side = min(src.size)
    left = (src.width - side) // 2
    top = (src.height - side) // 2
    square = src.crop((left, top, left + side, top + side))

    base = square.resize((512, 512), Image.LANCZOS)
    base.save(MASTER, optimize=True)
    base.save(f"{OUT}/icon-512.png", optimize=True)
    square.resize((192, 192), Image.LANCZOS).save(f"{OUT}/icon-192.png", optimize=True)
    square.resize((180, 180), Image.LANCZOS).save(f"{OUT}/apple-touch-icon.png", optimize=True)
    square.resize((32, 32), Image.LANCZOS).save(f"{OUT}/favicon-32.png", optimize=True)

    # maskable: keep the art inside the 80% safe zone, fill the bleed with a blurred copy
    canvas = base.filter(ImageFilter.GaussianBlur(18)).resize((512, 512))
    inner = base.resize((410, 410), Image.LANCZOS)
    canvas.paste(inner, ((512 - 410) // 2, (512 - 410) // 2))
    canvas.save(f"{OUT}/icon-maskable-512.png", optimize=True)

    # rounded variant used inside the web UI
    rounded(base, 0.24).save(f"{OUT}/icon-rounded-512.png", optimize=True)
    print("icons written:", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
