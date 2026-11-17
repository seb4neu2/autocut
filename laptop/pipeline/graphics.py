"""Overlay layouts for CapCut drafts: text stays editable, images are background only.

Every overlay (title card, HUD panel, route map, sticker, end card) is described as
  - an optional full-canvas transparent PNG holding only shapes (panel, route line, slots)
  - a list of text items with a position in canvas pixels, which build_plan.py turns into
    native CapCut text segments. Nothing readable is baked into an image, so every word can
    be changed or deleted in CapCut.
Text widths are measured with the same font files CapCut uses (from its cache), so text can
be lined up against a panel edge. Thumbnails are separate 1280x720 JPGs and stay rendered.
"""

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = {
    "impact": "C:/Windows/Fonts/impact.ttf",
    "black": "C:/Windows/Fonts/ariblk.ttf",
    "bold": "C:/Windows/Fonts/segoeuib.ttf",
    "heavy": "C:/Windows/Fonts/seguibl.ttf",
    "mono": "C:/Windows/Fonts/consolab.ttf",
    "cond": "C:/Windows/Fonts/bahnschrift.ttf",
}
# CapCut fonts used for overlay text: pycapcut FontType name, cached file, Windows stand-in for measuring
TEXT_FONTS = {
    "anton": ("Anton", "Anton-Regular.ttf", "impact"),
    "bebas": ("BebasNeue", "BebasNeue-Regular.ttf", "cond"),
    "poppins": ("Poppins_Bold", "Poppins-Bold.ttf", "bold"),
}
CAPCUT_CACHE = Path(os.environ.get("LOCALAPPDATA", "")) / "CapCut" / "User Data" / "Cache"
# brand yellow #F4C70F: card rims, card titles, highlights, narration captions (see CLAUDE.md)
YELLOW, WHITE, BLACK = (244, 199, 15), (255, 255, 255), (0, 0, 0)
YELLOW_F = (0.957, 0.780, 0.059)  # the same yellow as a CapCut 0-1 RGB colour
ORANGE_F = (1.0, 0.502, 0.0)      # #FF8000, only for "forty two"
WHITE_F, BLACK_F = (1.0, 1.0, 1.0), (0.0, 0.0, 0.0)
LINE_PITCH = 1.25  # estimated line height of multi-line CapCut text, in font sizes


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONTS[name], size)


def px_per_size(w: int, h: int) -> float:
    """Canvas pixels per CapCut text size unit (size 15 is about 150 px tall on a 1080p canvas).
    Estimated, not measured in CapCut: if overlay text comes out too big or too small against
    its panels, this is the one number to correct."""
    return min(w, h) / 108


@lru_cache(maxsize=None)
def _text_font_file(key: str) -> str:
    _, file, fallback = TEXT_FONTS[key]
    hits = sorted(CAPCUT_CACHE.glob(f"**/{file}")) if CAPCUT_CACHE.exists() else []
    return str(hits[0]) if hits else FONTS[fallback]


def text_width(text: str, key: str, px: float) -> float:
    """Width in canvas pixels of the widest line of `text` at font size `px`."""
    fnt = ImageFont.truetype(_text_font_file(key), 200)
    return max(fnt.getlength(line) for line in text.split("\n")) * px / 200


def _t(text, x, y, px, font="poppins", color=WHITE_F, **kw) -> dict:
    """One CapCut text item: centre (x, y) in canvas pixels, font size in pixels."""
    return {"text": text, "x": x, "y": y, "px": px, "font": font, "color": color, **kw}


def _canvas(w: int, h: int) -> Image.Image:
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def _outlined(draw, xy, text, fnt, fill, stroke, anchor="mm", sw=None):
    draw.text(xy, text, font=fnt, fill=fill, anchor=anchor,
              stroke_width=sw if sw is not None else max(4, fnt.size // 14), stroke_fill=stroke)


def _shadow(img: Image.Image, radius: int = 18, offset=(10, 14), alpha: int = 170) -> Image.Image:
    a = img.split()[-1]
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.putalpha(a.point(lambda v: min(alpha, v)))
    sh = sh.filter(ImageFilter.GaussianBlur(radius))
    out = _canvas(*img.size)
    out.alpha_composite(sh, offset)
    out.alpha_composite(img)
    return out


def _panel(draw, box, radius, fill=(10, 12, 14, 200), outline=None, width=0):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _pos(w, h, pw, ph, where: str, margin: float) -> tuple[int, int]:
    m = int(min(w, h) * margin)
    x = {"left": m, "center": (w - pw) // 2, "right": w - pw - m}
    y = {"top": m, "middle": (h - ph) // 2, "bottom": h - ph - m}
    vy, hx = where.split("-") if "-" in where else ("middle", where)
    return x.get(hx, x["center"]), y.get(vy, y["middle"])


# ---- overlays: each returns (background image or None, text items) -----------------------

def title_card(w, h, title: str, subtitle: str = "", kicker: str = ""):
    """Three centred lines, no image at all."""
    s = w / 3840
    texts = [_t(title.upper(), w / 2, h * 0.5, 400 * s, "anton", YELLOW_F, border=60, intro="放大")]
    if kicker:
        texts.append(_t(kicker.upper(), w / 2, h * 0.355, 120 * s, "bebas", border=45, intro="放大"))
    if subtitle:
        texts.append(_t(subtitle, w / 2, h * 0.665, 110 * s, "poppins", border=45, intro="放大"))
    return None, texts


def hud(w, h, title: str, rows: list[tuple[str, str]], where: str = "top-left", highlight: int | None = None):
    """Game-style mission panel, e.g. rows=[("BUDGET", "0 BAHT"), ("WATER", "0.5 L")].
    The panel is an image; title, labels and values are three text items on top of it."""
    s = w / 3840 if w > h else w / 2160
    pt, pr = 72 * s, 96 * s
    keys, vals = "\n".join(k for k, _ in rows), "\n".join(v for _, v in rows)
    key_w, val_w, title_w = text_width(keys, "bebas", pr), text_width(vals, "bebas", pr), text_width(title, "bebas", pt)
    pad, gap, title_h = 70 * s, 120 * s, pt * LINE_PITCH
    block_h = len(rows) * pr * LINE_PITCH
    pw = int(max(key_w + gap + val_w, title_w) + pad * 2)
    ph = int(pad * 2 + title_h + 24 * s + block_h)
    img = _canvas(w, h)
    x, y = _pos(w, h, pw, ph, where, 0.045)
    _panel(ImageDraw.Draw(img), (x, y, x + pw, y + ph), int(28 * s), outline=YELLOW + (255,), width=max(3, int(6 * s)))
    rows_y = y + pad + title_h + 24 * s + block_h / 2
    spans = []
    if highlight is not None:
        a = sum(len(v) + 1 for _, v in rows[:highlight])
        spans = [(a, a + len(rows[highlight][1]), {"color": YELLOW_F})]
    texts = [
        _t(title, x + pad + title_w / 2, y + pad + title_h / 2, pt, "bebas", YELLOW_F, align=0),
        _t(keys, x + pad + key_w / 2, rows_y, pr, "bebas", WHITE_F, align=0),
        _t(vals, x + pw - pad - val_w / 2, rows_y, pr, "bebas", WHITE_F, align=2, spans=spans),
    ]
    return _shadow(img, int(16 * s), (int(6 * s), int(8 * s)), 140), texts


def info(w, h, title: str = "", lines: list[str] = (), image: str | None = None, where: str = "top-left",
         highlight: list[str] = ()):
    """Info card, optionally with a picture (e.g. a bowl of soup under its name).
    The panel sits in the corner; the picture (a photo, no text in it, yellow rim) goes below it,
    left-aligned (user, 2026-10-23), or in the corner on its own. Title (yellow) and lines (white,
    `highlight` phrases yellow) are text items, centred in the panel so they do not depend on the
    estimated text size. A title with Vietnamese letters Bebas lacks (ộ, ư, ở) is set in Anton."""
    s = w / 3840 if w > h else w / 2160
    m = int(min(w, h) * 0.045)
    rim, radius = max(3, int(6 * s)), int(28 * s)
    pic = int(640 * s)
    pt, pl = 96 * s, 80 * s
    tfont = "anton" if any("Ạ" <= c <= "ỹ" or c in "ƠơƯư" for c in title) else "bebas"
    body = "\n".join(lines)
    title_h = pt * LINE_PITCH if title else 0
    body_h = len(lines) * pl * LINE_PITCH
    pad = 60 * s
    tw = max(text_width(title, tfont, pt) if title else 0, text_width(body, "poppins", pl) if lines else 0)
    pw = int(tw * 1.12 + pad * 2) if (title or lines) else 0
    ph = int(pad * 2 + title_h + (24 * s if title and lines else 0) + body_h)
    img = _canvas(w, h)
    d = ImageDraw.Draw(img)
    x, y = m, m
    if where.endswith("right"):
        x = w - m - max(pw, pic if image else 0)
    if image:
        py = y + ph + int(40 * s) if pw else y
        photo = Image.open(image).convert("RGB")
        side = min(photo.size)
        photo = photo.crop(((photo.width - side) // 2, (photo.height - side) // 2,
                            (photo.width + side) // 2, (photo.height + side) // 2)).resize((pic, pic), Image.LANCZOS)
        mask = Image.new("L", (pic, pic), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, pic - 1, pic - 1), radius=radius, fill=255)
        img.paste(photo, (x, py), mask)
        d.rounded_rectangle((x, py, x + pic, py + pic), radius=radius, outline=YELLOW + (255,), width=rim)
    texts = []
    if pw:
        _panel(d, (x, y, x + pw, y + ph), radius, outline=YELLOW + (255,), width=rim)
        cy = y + (ph - title_h - (24 * s if title and lines else 0) - body_h) / 2
        if title:
            texts.append(_t(title, x + pw / 2, cy + title_h / 2, pt, tfont, YELLOW_F))
            cy += title_h + 24 * s
        if lines:
            spans = [(i, i + len(p), {"color": YELLOW_F}) for p in highlight if (i := body.find(p)) >= 0]
            texts.append(_t(body, x + pw / 2, cy + body_h / 2, pl, "poppins", WHITE_F, spans=spans))
    return _shadow(img, int(16 * s), (int(6 * s), int(8 * s)), 140), texts


def route_map(w, h, start: str, end: str, note: str, where: str = "top-right"):
    """Stylised A -> B route card (no real map data): dotted curve between two pins.
    The card, curve and pins are an image; the two place names and the note are text."""
    s = w / 3840 if w > h else w / 2160
    pw, ph = int(1300 * s), int(760 * s)
    card = _canvas(pw, ph)
    d = ImageDraw.Draw(card)
    _panel(d, (0, 0, pw - 1, ph - 1), int(36 * s), fill=(18, 40, 38, 215), outline=YELLOW + (255,), width=int(6 * s))
    a, b = (int(230 * s), int(560 * s)), (int(1080 * s), int(240 * s))
    pts = []
    for i in range(41):
        t = i / 40
        cx, cy = int(700 * s), int(640 * s)
        px = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * cx + t ** 2 * b[0]
        py = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * cy + t ** 2 * b[1]
        pts.append((px, py))
    for i in range(0, 40, 2):
        d.line([pts[i], pts[i + 1]], fill=YELLOW, width=int(14 * s))
    for px, py in (a, b):
        r = int(30 * s)
        d.ellipse((px - r, py - r, px + r, py + r), fill=YELLOW, outline=BLACK, width=int(6 * s))
    img = _canvas(w, h)
    x, y = _pos(w, h, pw, ph, where, 0.045)
    img.alpha_composite(card, (x, y))
    texts = [_t(label, x + px, y + py - 85 * s, 64 * s, "poppins", border=40)
             for (px, py), label in ((a, start), (b, end))]
    texts.append(_t(note, x + pw / 2, y + ph - 72 * s, 58 * s, "poppins", YELLOW_F, border=40))
    return _shadow(img, int(18 * s), (int(8 * s), int(10 * s)), 150), texts


def sticker(w, h, text: str, sub: str = "", where: str = "top-right", color=YELLOW, angle: float = -6):
    """Punchy tilted label, e.g. '2,000 BAHT' with sub 'for a boat ride?!'.
    One text item with CapCut's own coloured text background, no image."""
    s = w / 3840 if w > h else w / 2160
    pm, ps = 215 * s, 80 * s
    full = text + ("\n" + sub if sub else "")
    bw = max(text_width(text, "anton", pm), text_width(sub, "poppins", ps) if sub else 0) + 150 * s
    bh = pm * LINE_PITCH + (ps * LINE_PITCH if sub else 0) + 90 * s
    x, y = _pos(w, h, int(bw), int(bh), where, 0.07)
    spans = [(len(text), len(full), {"px": ps, "font": "poppins"})] if sub else []
    bg = {"color": "#%02X%02X%02X" % tuple(color), "alpha": 0.96, "round_radius": 0.25, "width": 0.22, "height": 0.2}
    return None, [_t(full, x + bw / 2, y + bh / 2, pm, "anton", BLACK_F, spans=spans, background=bg,
                     rotation=-angle, intro="弹入")]


def end_card(w, h, title: str, lines: list[str]):
    """End screen over the last shot: the title line and e.g. "Thanks for watching / See you in the
    next one". No darkening and no "next video" / "subscribe" slots (user, 2026-10-23)."""
    s = w / 3840
    texts = [_t(title.upper(), w / 2, h * 0.17, 225 * s, "anton", YELLOW_F, border=55)]
    if lines:
        texts.append(_t("\n".join(lines), w / 2, h * 0.29 + (len(lines) - 1) * 55 * s, 84 * s, "poppins", border=40))
    return None, texts


def thumbnail(frame: Path, lines: list[str], out: Path, *, align: str = "left", accent_line: int = 0,
              darken: float = 0.25, zoom: float = 1.0, focus=(0.5, 0.5)) -> Path:
    """1280x720 YouTube thumbnail: a video frame plus 1-3 huge outlined words."""
    W, H = 1280, 720
    base = Image.open(frame).convert("RGB")
    bw, bh = base.size
    cw, ch = bw / zoom, bh / zoom
    cx, cy = focus[0] * bw, focus[1] * bh
    box = (max(0, min(bw - cw, cx - cw / 2)), max(0, min(bh - ch, cy - ch / 2)))
    base = base.crop((int(box[0]), int(box[1]), int(box[0] + cw), int(box[1] + ch))).resize((W, H), Image.LANCZOS)
    img = base.convert("RGBA")
    grad = Image.new("L", (W, 1))
    for x in range(W):
        t = x / W if align == "right" else 1 - x / W
        grad.putpixel((x, 0), int(255 * darken * 2 * max(0, t - 0.3)))
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    shade.putalpha(grad.resize((W, H)))
    img.alpha_composite(shade)
    d = ImageDraw.Draw(img)
    size = 170 if len(lines) <= 2 else 130
    y0 = H / 2 - (len(lines) - 1) * size * 0.55
    for i, line in enumerate(lines):
        fnt = font("impact", size)
        x = 60 if align == "left" else W - 60
        _outlined(d, (x, y0 + i * size * 1.05), line.upper(), fnt, YELLOW if i == accent_line else WHITE, BLACK,
                  anchor="lm" if align == "left" else "rm", sw=12)
    img.convert("RGB").save(out, quality=92)
    return out


def label(w, h, text: str, y: float = 0.16, size: float = 250, accent_line: int | None = 1):
    """Headline for Shorts (hook at the start, call to action at the end): one or two centred
    lines of outlined text, no image. `size` is the font size on a 1080 px wide canvas; the default
    250 is CapCut text size 25, the user's size for text splashes in Shorts (CLAUDE.md, 2026-10-12)."""
    px = size * min(w, h) / 1080
    lines = text.splitlines()
    spans = []
    if accent_line is not None and accent_line < len(lines):
        a = sum(len(line) + 1 for line in lines[:accent_line])
        spans = [(a, a + len(lines[accent_line]), {"color": YELLOW_F})]
    return None, [_t(text, w / 2, h * y, px, "anton", WHITE_F, border=55, spans=spans, intro="弹入")]


LAYOUTS = {"title": title_card, "hud": hud, "info": info, "map": route_map, "sticker": sticker, "end": end_card, "label": label}


def layout(spec: dict, w: int, h: int, out_dir: Path) -> tuple[Path | None, list[dict]]:
    """Lay out an overlay spec like {"type": "hud", "title": ..., "rows": [...]}.
    Returns (cached text-free background PNG or None, text items for CapCut)."""
    args = {k: v for k, v in spec.items() if k != "type"}
    if "rows" in args:
        args["rows"] = [tuple(r) for r in args["rows"]]
    if "color" in args:
        args["color"] = tuple(args["color"])
    if args.get("image"):  # a picture from the asset folder, by file name
        args["image"] = str(out_dir / args["image"])
    img, texts = LAYOUTS[spec["type"]](w, h, **args)
    if img is None:
        return None, texts
    # named by the drawn pixels, not the spec: a layout change (sizes, margins) with the same spec must not
    # reuse an old panel, or the text, laid out anew, no longer sits on it (Vietnam v2 info cards, 2026-10-22)
    key = hashlib.sha1(img.tobytes()).hexdigest()[:12]
    out = out_dir / f"gfx_{spec['type']}-background_{key}.png"
    if not out.exists():
        img.save(out)
    return out, texts
