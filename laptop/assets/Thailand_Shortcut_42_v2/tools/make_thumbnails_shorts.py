#!/usr/bin/env python3
"""Vertical thumbnails (1080x1920 JPG) for the three Thailand Shorts, written to ../youtube/.

  dogs    the dog leading through the jungle / both dogs at the lake, "THE DOGS"
  boat    the exhausted face / the lake from above, "2,000 BAHT BOAT?" struck out, "I WALKED"
  hotel   the lake from above / the fishermen's hut, "0 BAHT"
Same look as thumbnail C of the main video: two pictures split by a yellow diagonal, gold main word.
The text sits in the middle band, clear of the Shorts buttons and of the 4:5 crop of the Shorts shelf.
Drawn at double size and scaled down, so edges stay clean.
"""

import io
import subprocess

from PIL import Image, ImageDraw

import make_thumbnails as mt
from make_thumbnails import BLACK, RED, WHITE, YELLOW, cover, font, gold_text, punch, text

W, H = 2160, 3840
SPLIT_R, SPLIT_L = 0.455, 0.545  # the diagonal: height of the cut at the right and at the left edge
MAX_TEXT = W - 240

C94, C96, C98, C100 = ("42850_DJI_20240318_0094.MP4", "42950_DJI_20240318_0096.MP4",
                       "43050_DJI_20240318_0098.MP4", "43150_DJI_20240318_0100.MP4")
DRONE, DRONE2 = "DJI_0300.MP4", "DJI_0301.MP4"


def frame(src: tuple[str, float]) -> Image.Image:
    """One frame straight from the footage, not kept on disk (a 4K PNG is up to 25 MB)."""
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{src[1]:.3f}", "-i", str(mt.FOOTAGE / src[0]),
                          "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "-"],
                         check=True, capture_output=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGB")


def fit(s: str, size: int) -> int:
    """Largest size up to `size` at which the line fits the width."""
    while font("anton", size).getlength(s) > MAX_TEXT:
        size -= 6
    return size


def background(top: dict, bottom: dict) -> Image.Image:
    hp = int(H * SPLIT_L)
    img = Image.new("RGBA", (W, H))
    for part, y in ((bottom, H - hp), (top, 0)):
        pic = cover(frame(part["src"]), W, hp, part["focus"], part.get("zoom", 1.0), part.get("at", (0.5, 0.5)))
        pic = punch(pic, *part.get("punch", (1.4, 1.15, 1.08)))
        if y:
            img.paste(pic, (0, y))
        else:
            mask = Image.new("L", (W, hp), 0)
            ImageDraw.Draw(mask).polygon([(0, 0), (W, 0), (W, int(H * SPLIT_R)), (0, hp)], fill=255)
            img.paste(pic, (0, 0), mask)
    d = ImageDraw.Draw(img)
    cut = [(-40, int(H * SPLIT_L) + 2), (W + 40, int(H * SPLIT_R) - 2)]
    d.line(cut, fill=BLACK, width=52)
    d.line(cut, fill=YELLOW, width=26)
    return img


def thumbnail(name: str, top: dict, bottom: dict, line1: str, main: str, line3: str, struck: bool = False) -> None:
    img = background(top, bottom)
    cx, cy = W // 2, H // 2
    size = fit(main, 760)
    half = int(size * 0.5)
    s1 = fit(line1, 250)
    y1 = cy - half - int(s1 * 0.72)
    box = text(img, (cx, y1), line1, s1, WHITE, "mm")
    if struck:
        d = ImageDraw.Draw(img)
        line = [(box[0] - 30, y1 + 50), (box[2] + 30, y1 - 55)]
        d.line(line, fill=BLACK, width=36)
        d.line(line, fill=RED, width=18)
    gold_text(img, (cx, cy), main, size, "mm")
    s3 = fit(line3, 250)
    text(img, (cx, cy + half + int(s3 * 0.78)), line3, s3, WHITE, "mm")
    out = mt.OUT / f"thumbnail_short_{name}.jpg"
    img.convert("RGB").resize((1080, 1920), Image.LANCZOS).save(out, quality=93, optimize=True)
    print(out, f"{out.stat().st_size / 1024:.0f} KB")


def main() -> None:
    thumbnail("dogs",
              {"src": (C96, 72.5), "focus": (0.31, 0.52), "zoom": 1.25, "at": (0.5, 0.42)},
              {"src": (C98, 211.0), "focus": (0.635, 0.6), "zoom": 1.12, "at": (0.5, 0.64), "punch": (1.3, 1.2, 1.05)},
              "LOST IN THE JUNGLE", "THE DOGS", "KNEW THE WAY")
    thumbnail("boat",
              {"src": (C98, 30.0), "focus": (0.565, 0.45), "zoom": 1.2, "at": (0.5, 0.42), "punch": (1.25, 1.2, 1.12)},
              {"src": (DRONE, 66.0), "focus": (0.42, 0.62), "zoom": 1.1, "at": (0.5, 0.6), "punch": (1.55, 1.15, 1.08)},
              "2,000 BAHT BOAT?", "I WALKED", "NEVER AGAIN", struck=True)
    thumbnail("hotel",
              {"src": (DRONE, 99.0), "focus": (0.42, 0.45), "zoom": 1.0, "at": (0.5, 0.45), "punch": (1.55, 1.15, 1.08)},
              {"src": (C100, 99.0), "focus": (0.79, 0.34), "zoom": 1.9, "at": (0.5, 0.6), "punch": (1.5, 1.15, 1.15)},
              "MY HOTEL IN THAILAND", "0 BAHT", "A HUT ON A LAKE")


if __name__ == "__main__":
    main()
