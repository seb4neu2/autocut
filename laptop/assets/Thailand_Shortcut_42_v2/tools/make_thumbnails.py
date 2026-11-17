#!/usr/bin/env python3
"""Two YouTube thumbnails (1280x720 JPG) for the Thailand shortcut video, written to ../youtube/.

  A  split picture: the exhausted face on the left, the lake on the right, "NEVER AGAIN"
  B  the lake full frame, "2,000 BAHT BOAT" struck out, "I WALKED", face in a round inset
Drawn at double size and scaled down, so edges stay clean.
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "youtube"
sys.path.insert(0, str(HERE.parents[2] / "pipeline"))
import graphics  # noqa: E402

FOOTAGE = Path(r"D:\Backup\VlogX")
W, H = 2560, 1440
YELLOW, WHITE, BLACK, RED = (244, 199, 15), (255, 255, 255), (0, 0, 0), (230, 40, 30)
FACE_TIRED = ("43050_DJI_20240318_0098.MP4", 30.0)
FACE_HAPPY = ("43050_DJI_20240318_0098.MP4", 35.5)
LAKE = ("DJI_0300.MP4", 66.0)


def frame(src: tuple[str, float]) -> Image.Image:
    png = OUT / f"frame_{Path(src[0]).stem}_{src[1]:.1f}.png"
    if not png.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{src[1]:.3f}", "-i", str(FOOTAGE / src[0]),
                        "-frames:v", "1", str(png)], check=True)
    return Image.open(png).convert("RGB")


def punch(img: Image.Image, colour=1.35, contrast=1.15, bright=1.05) -> Image.Image:
    img = ImageEnhance.Color(img).enhance(colour)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    return ImageEnhance.Brightness(img).enhance(bright)


def cover(img: Image.Image, w: int, h: int, focus=(0.5, 0.5), zoom=1.0, at=(0.5, 0.5)) -> Image.Image:
    """Crop to w x h, zoomed in, so that the focus point of the picture lands at `at` in the crop."""
    scale = max(w / img.width, h / img.height) * zoom
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    x = min(max(round(focus[0] * img.width - w * at[0]), 0), img.width - w)
    y = min(max(round(focus[1] * img.height - h * at[1]), 0), img.height - h)
    return img.crop((x, y, x + w, y + h))


def font(key: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(graphics._text_font_file(key), size)


def text(img: Image.Image, xy, s: str, size: int, fill, anchor="lm", angle=0.0, stroke=None) -> tuple:
    """Outlined text with a soft drop shadow; returns its bounding box."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font("anton", size)
    sw = stroke if stroke is not None else max(8, size // 11)
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=BLACK)
    box = d.textbbox(xy, s, font=f, anchor=anchor, stroke_width=sw)
    if angle:
        layer = layer.rotate(angle, center=xy, resample=Image.BICUBIC)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.putalpha(layer.split()[-1].point(lambda v: int(v * 0.75)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(shadow, (10, 16))
    img.alpha_composite(layer)
    return box


def save(img: Image.Image, name: str) -> None:
    out = OUT / name
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(out, quality=93, optimize=True)
    print(out, f"{out.stat().st_size / 1024:.0f} KB")


def version_a() -> None:
    img = Image.new("RGBA", (W, H))
    lake = punch(cover(frame(LAKE), W, H, (0.42, 0.62), 1.25), 1.5, 1.15, 1.08)
    img.paste(lake)
    fw = int(W * 0.56)  # the face gets its own crop, centred in the left panel
    face = punch(cover(frame(FACE_TIRED), fw, H, (0.565, 0.45), 1.2, at=(0.43, 0.5)), 1.25, 1.2, 1.12)
    mask = Image.new("L", (W, H), 0)
    split = [(0, 0), (int(W * 0.56), 0), (int(W * 0.44), H), (0, H)]
    ImageDraw.Draw(mask).polygon(split, fill=255)
    img.paste(face, (0, 0), mask.crop((0, 0, fw, H)))
    d = ImageDraw.Draw(img)
    d.line([split[1], split[2]], fill=BLACK, width=44)
    d.line([split[1], split[2]], fill=YELLOW, width=22)
    text(img, (int(W * 0.775), int(H * 0.60)), "NEVER", 400, YELLOW, "mm", 4)
    text(img, (int(W * 0.765), int(H * 0.86)), "AGAIN", 400, WHITE, "mm", 4)
    save(img, "thumbnail_A_never-again.jpg")


def version_b() -> None:
    img = punch(cover(frame(LAKE), W, H, (0.5, 0.6), 1.1), 1.55, 1.15, 1.06).convert("RGBA")
    shade = Image.new("L", (W, 1))
    for x in range(W):
        shade.putpixel((x, 0), int(150 * max(0.0, 1 - x / (W * 0.72))))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dark.putalpha(shade.resize((W, H)))
    img.alpha_composite(dark)
    x0 = 110
    box = text(img, (x0, 300), "2,000 BAHT BOAT", 230, WHITE, "lm")
    d = ImageDraw.Draw(img)
    d.line([(box[0] - 30, 345), (box[2] + 30, 250)], fill=BLACK, width=40)
    d.line([(box[0] - 30, 345), (box[2] + 30, 250)], fill=RED, width=22)
    text(img, (x0, 700), "I WALKED", 430, YELLOW, "lm")
    text(img, (x0 + 8, 1050), "42 minutes of regret", 150, WHITE, "lm")
    r = 400
    cx, cy = W - r - 110, H - r - 90
    face = punch(cover(frame(FACE_TIRED), 2 * r, 2 * r, (0.565, 0.43), 1.45), 1.25, 1.2, 1.12)
    mask = Image.new("L", (2 * r, 2 * r), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
    ring = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse((cx - r - 34, cy - r - 34, cx + r + 34, cy + r + 34), fill=BLACK)
    rd.ellipse((cx - r - 20, cy - r - 20, cx + r + 20, cy + r + 20), fill=YELLOW)
    img.alpha_composite(ring)
    img.paste(face, (cx - r, cy - r), mask)
    save(img, "thumbnail_B_i-walked.jpg")


def main_ab() -> None:
    OUT.mkdir(exist_ok=True)
    version_a()
    version_b()


# ---- version C: in the style of the channel's best thumbnails (smiling face cut out, gold text) ----

FACE_SMILE = ("43050_DJI_20240318_0098.MP4", 36.2)


def cutout(img: Image.Image) -> Image.Image:
    """Person cut out of the picture (OpenCV GrabCut), as RGBA."""
    import cv2
    import numpy as np
    small = cv2.cvtColor(np.asarray(img.resize((960, 540), Image.LANCZOS)), cv2.COLOR_RGB2BGR)
    mask = np.full((540, 960), cv2.GC_BGD, np.uint8)
    mask[95:540, 150:810] = cv2.GC_PR_BGD
    cv2.ellipse(mask, (480, 250), (200, 120), 0, 0, 360, cv2.GC_PR_FGD, -1)   # hat
    cv2.ellipse(mask, (480, 330), (95, 120), 0, 0, 360, cv2.GC_FGD, -1)       # face
    cv2.ellipse(mask, (480, 540), (250, 110), 0, 0, 360, cv2.GC_FGD, -1)      # chest
    cv2.ellipse(mask, (480, 540), (330, 170), 0, 0, 360, cv2.GC_PR_FGD, -1)
    mask[mask == 0] = cv2.GC_BGD
    cv2.ellipse(mask, (480, 330), (95, 120), 0, 0, 360, cv2.GC_FGD, -1)
    cv2.ellipse(mask, (480, 250), (150, 60), 0, 0, 360, cv2.GC_FGD, -1)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(small, mask, None, bgd, fgd, 8, cv2.GC_INIT_WITH_MASK)
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(fg)
    if n > 1:  # keep the biggest blob only
        fg = np.where(labels == 1 + stats[1:, cv2.CC_STAT_AREA].argmax(), 255, 0).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    fg = cv2.GaussianBlur(cv2.resize(fg, img.size, interpolation=cv2.INTER_CUBIC), (0, 0), 5)
    fg = np.clip((fg.astype(np.float32) - 110) * 4, 0, 255).astype(np.uint8)
    out = img.convert("RGBA")
    out.putalpha(Image.fromarray(fg))
    return out


def gold_text(img: Image.Image, xy, s: str, size: int, anchor="rm") -> None:
    f = font("anton", size)
    sw = max(10, size // 9)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text(xy, s, font=f, fill=BLACK, anchor=anchor, stroke_width=sw, stroke_fill=BLACK)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.putalpha(layer.split()[-1].point(lambda v: int(v * 0.8)))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(16)), (12, 18))
    img.alpha_composite(layer)
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).text(xy, s, font=f, fill=255, anchor=anchor)
    box = m.getbbox()
    grad = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    stops = [(255, 244, 150), (250, 214, 40), (244, 199, 15), (226, 140, 0)]
    for y in range(box[1], box[3]):
        t = (y - box[1]) / max(1, box[3] - box[1]) * (len(stops) - 1)
        i = min(int(t), len(stops) - 2)
        c = tuple(int(stops[i][k] + (stops[i + 1][k] - stops[i][k]) * (t - i)) for k in range(3))
        gd.line([(box[0], y), (box[2], y)], fill=c + (255,))
    grad.putalpha(m)
    img.alpha_composite(grad)


def version_c() -> None:
    img = punch(cover(frame(LAKE), W, H, (0.5, 0.62), 1.15), 1.7, 1.18, 1.1).convert("RGBA")
    person = cutout(punch(frame(FACE_SMILE), 1.3, 1.15, 1.12))
    scale = 0.75
    person = person.resize((int(person.width * scale), int(person.height * scale)), Image.LANCZOS)
    px, py = 690 - person.width // 2, H - person.height + 40  # hat centred at x = 690
    dst, src = (max(px, 0), max(py, 0)), (max(-px, 0), max(-py, 0))
    alpha = person.split()[-1]
    for grow, colour in ((34, BLACK), (22, WHITE)):  # white outline around the cut-out, like the channel's other thumbnails
        edge = Image.new("RGBA", person.size, colour + (255,))
        edge.putalpha(alpha.filter(ImageFilter.MaxFilter(2 * (grow // 2) + 1)).filter(ImageFilter.GaussianBlur(3)).point(lambda v: 255 if v > 90 else 0))
        img.alpha_composite(edge, dst, src)
    img.alpha_composite(person, dst, src)
    box = text(img, (W - 90, 250), "2,000 BAHT BOAT?", 178, WHITE, "rm")
    d = ImageDraw.Draw(img)
    d.line([(box[0] - 25, 290), (box[2] + 25, 212)], fill=BLACK, width=28)
    d.line([(box[0] - 25, 290), (box[2] + 25, 212)], fill=RED, width=14)
    gold_text(img, (W - 90, 610), "I WALKED", 400)
    text(img, (W - 96, 905), "42 MINUTES OF JUNGLE", 128, WHITE, "rm")
    save(img, "thumbnail_C_smile-i-walked.jpg")


if __name__ == "__main__":
    main_ab()
    version_c()
