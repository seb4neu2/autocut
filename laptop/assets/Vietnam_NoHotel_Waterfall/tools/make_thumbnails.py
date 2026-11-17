#!/usr/bin/env python3
"""Three YouTube thumbnails (1280x720 JPG) for the Vietnam waterfall video, written to ../youtube/.

  A  split picture: the falls from the drone on the left, the smiling face in the water on the right, "NO HOTEL?"
  B  the night the three boys brought the camera back, "LOST MY CAMERA" / "THEY BROUGHT IT BACK"
  C  the campfire, "MY HOTEL TONIGHT" with five empty stars
Drawn at double size and scaled down, so edges stay clean. Helpers copied from the Thailand script.
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "youtube"
sys.path.insert(0, str(HERE.parents[2] / "pipeline"))
import graphics  # noqa: E402

FOOTAGE = Path(r"C:\Users\niu\Desktop\Sort\2026-04-12_DrayNur")
UPRIGHT = HERE.parent / "upright"
W, H = 2560, 1440
YELLOW, WHITE, BLACK, RED = (244, 199, 15), (255, 255, 255), (0, 0, 0), (230, 40, 30)
FALLS = (FOOTAGE / "Drone shots" / "DJI_20260412174910_0003_D.MP4", 483.0)
FACE_WATER = (FOOTAGE / "DJI_20260412104554_0005_D.MP4", 228.0)
BOYS = (UPRIGHT / "PXL_20260412_124820870.mp4", 21.0)
FIRE = (FOOTAGE / "PXL_20260412_135658744.mp4", 5.0)


def frame(src: tuple[Path, float]) -> Image.Image:
    png = OUT / f"frame_{src[0].stem}_{src[1]:.1f}.png"
    if not png.exists():
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{src[1]:.3f}", "-i", str(src[0]),
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


def shade(img: Image.Image, side="left", strength=170, reach=0.7) -> None:
    """Darken one side with a soft gradient so the text reads."""
    ramp = Image.new("L", (W, 1))
    for x in range(W):
        p = x / W if side == "left" else 1 - x / W
        ramp.putpixel((x, 0), int(strength * max(0.0, 1 - p / reach)))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dark.putalpha(ramp.resize((W, H)))
    img.alpha_composite(dark)


def star(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill, outline, width: int) -> None:
    import math
    pts = [(cx + (r if i % 2 == 0 else r * 0.45) * math.sin(i * math.pi / 5),
            cy - (r if i % 2 == 0 else r * 0.45) * math.cos(i * math.pi / 5)) for i in range(10)]
    d.polygon(pts, fill=fill, outline=outline, width=width)


def save(img: Image.Image, name: str) -> None:
    out = OUT / name
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(out, quality=93, optimize=True)
    print(out, f"{out.stat().st_size / 1024:.0f} KB")


def version_a() -> None:
    img = Image.new("RGBA", (W, H))
    falls = punch(cover(frame(FALLS), W, H, (0.47, 0.5), 1.35, at=(0.3, 0.55)), 1.45, 1.18, 1.06)
    img.paste(falls)
    fx = int(W * 0.47)  # the face gets its own crop in the right panel
    face = punch(cover(frame(FACE_WATER), W - fx + 200, H, (0.5, 0.42), 1.25, at=(0.55, 0.5)), 1.25, 1.15, 1.1)
    mask = Image.new("L", (W, H), 0)
    split = [(fx + 120, 0), (W, 0), (W, H), (fx - 120, H)]
    ImageDraw.Draw(mask).polygon(split, fill=255)
    img.paste(face, (fx - 200, 0), mask.crop((fx - 200, 0, W, H)))
    d = ImageDraw.Draw(img)
    d.line([split[0], split[3]], fill=BLACK, width=44)
    d.line([split[0], split[3]], fill=YELLOW, width=22)
    shade(img, "left", 120, 0.45)
    text(img, (90, 260), "NO HOTEL?", 300, WHITE, "lm", 3)
    gold_text(img, (95, 1150), "NO PROBLEM", 260, "lm")
    save(img, "thumbnail_A_no-hotel.jpg")


def version_b() -> None:
    img = punch(cover(frame(BOYS), W, H, (0.36, 0.5), 1.0, at=(0.36, 0.5)), 1.2, 1.1, 1.3).convert("RGBA")
    shade(img, "right", 200, 0.42)
    text(img, (W - 90, 260), "LOST MY", 230, WHITE, "rm", -3)
    text(img, (W - 90, 500), "CAMERA", 230, WHITE, "rm", -3)
    gold_text(img, (W - 90, 880), "THEY BROUGHT", 190, "rm")
    gold_text(img, (W - 90, 1120), "IT BACK", 260, "rm")
    save(img, "thumbnail_B_camera-back.jpg")


# ---- version B2: the camera hand-over in front of the falls at night, with a big fire (user, 2026-10-23) ----

BOYS2 = (UPRIGHT / "PXL_20260412_124820870.mp4", 22.3)      # looking into the lens, camera held up
FIRE2 = (FOOTAGE / "PXL_20260412_135658744.mp4", 2.0)       # the tallest flame
FALLS2 = (FOOTAGE / "Drone shots" / "DJI_20260412174910_0003_D.MP4", 476.0)


def night(img: Image.Image) -> Image.Image:
    """Day picture graded to blue night."""
    import numpy as np
    a = np.asarray(img).astype(np.float32) / 255
    lum = a.mean(axis=2, keepdims=True)
    a = (0.55 * a + 0.45 * lum) * np.array([0.42, 0.55, 0.85]) * 0.75
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def version_b2() -> None:
    import numpy as np
    bg = night(cover(frame(FALLS2), W, H, (0.42, 0.42), 1.05, at=(0.62, 0.42)))
    acc = np.asarray(bg).astype(np.float32) / 255
    # fire: screen blend of the flame crop, under a soft oval so its surroundings disappear
    fw, fh = 1300, 1500
    fire = cover(frame(FIRE2), 1920 * fh // 1080, fh, (0.43, 0.4), 1.0)
    fire = np.asarray(fire.crop(((fire.width - fw) // 2, 0, (fire.width + fw) // 2, fh))).astype(np.float32) / 255
    yy, xx = np.mgrid[0:fh, 0:fw]
    oval = np.clip(1.6 - np.hypot((xx - fw / 2) / (fw * 0.42), (yy - fh * 0.45) / (fh * 0.55)) * 1.6, 0, 1)[..., None]
    fire = np.clip((fire - 0.12) * 1.25, 0, 1) * oval
    fx, fy = 1180, H - fh + 60
    x0, x1, y0 = max(fx, 0), min(fx + fw, W), max(fy, 0)
    part = fire[y0 - fy:H - fy, x0 - fx:x1 - fx]
    acc[y0:, x0:x1] = 1 - (1 - acc[y0:, x0:x1]) * (1 - part)
    # warm glow of the fire on the whole scene
    gy, gx = np.mgrid[0:H, 0:W]
    glow = np.clip(1 - np.hypot((gx - 1830) / 1500, (gy - 900) / 1000), 0, 1)[..., None] ** 1.5
    acc = 1 - (1 - acc) * (1 - glow * np.array([0.55, 0.25, 0.04]))
    # the people: the night frame lies on top, its black background lets the scene show through
    ppl = cover(frame(BOYS2), W, H, (0.4, 0.55), 1.06, at=(0.4, 0.6))
    p = np.asarray(ppl).astype(np.float32) / 255
    lum = np.asarray(ppl.convert("L").filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
    alpha = np.clip((lum - 0.05) / 0.12, 0, 1)[..., None]
    p = np.clip(p ** 0.72 * 1.12, 0, 1)                      # lift the flash-lit faces
    p = 1 - (1 - p) * (1 - glow * np.array([0.35, 0.15, 0.0]))  # fire light on them
    acc = p * alpha + acc * (1 - alpha)
    img = punch(Image.fromarray((np.clip(acc, 0, 1) * 255).astype(np.uint8)), 1.2, 1.12, 1.0).convert("RGBA")
    shade(img, "right", 110, 0.3)
    text(img, (W - 80, 200), "LOST MY CAMERA", 210, WHITE, "rm", -2)
    gold_text(img, (W - 80, 1000), "THEY BROUGHT", 190, "rm")
    gold_text(img, (W - 80, 1240), "IT BACK", 250, "rm")
    save(img, "thumbnail_B2_camera-back-fire.jpg")


def version_c() -> None:
    img = punch(cover(frame(FIRE), W, H, (0.55, 0.55), 1.15), 1.25, 1.1, 0.95).convert("RGBA")
    shade(img, "left", 190, 0.5)
    text(img, (90, 230), "MY HOTEL", 260, WHITE, "lm")
    gold_text(img, (95, 500), "TONIGHT", 260, "lm")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(5):
        for r, c in ((112, BLACK), (96, YELLOW), (66, (35, 35, 35))):  # empty star: black rim, yellow line, dark inside
            star(d, 190 + i * 230, 860, r, c, None, 0)
    img.alpha_composite(layer)
    text(img, (100, 1130), "0 STARS", 230, WHITE, "lm")
    save(img, "thumbnail_C_my-hotel-tonight.jpg")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    version_a()
    version_b()
    version_c()
