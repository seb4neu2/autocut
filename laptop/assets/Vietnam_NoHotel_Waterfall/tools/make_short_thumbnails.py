#!/usr/bin/env python3
"""Thumbnails (1080x1920 JPG) for the four Vietnam Shorts, written to ../youtube/shorts/.

Local step: two real frames stacked (top and bottom picture, slanted black and yellow divider like thumbnail A)
and the headline in the channel fonts. Text stays inside the middle of the picture, away from the Shorts
player buttons (right edge) and the title at the bottom.
  python make_short_thumbnails.py                 all four, local only (free)
  python make_short_thumbnails.py --ai camera     the local one goes to Gemini (OpenRouter) for a better version,
                                                  a few cents each (printed after the call)
"""

import argparse
import base64
import io
import json
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageEnhance

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_thumbnails as mt  # noqa: E402  (frame grabber, outlined and gold text, colour punch)

OUT = HERE.parent / "youtube" / "shorts"
W, H = 2160, 3840  # drawn at double size, saved at 1080x1920
F, U = mt.FOOTAGE, mt.UPRIGHT
SHORTS = {
    "camera": {"top": (U / "PXL_20260412_124820870.mp4", 22.3), "top_focus": (0.3, 0.5),   # camera held up
               "bottom": (U / "PXL_20260412_124820870.mp4", 20.0), "bottom_focus": (0.7, 0.5),  # the three boys
               "dark": True,
               "lines": [("I LOST MY", "white"), ("CAMERA", "white"), ("THEY BROUGHT", "gold"), ("IT BACK", "gold")]},
    "waterfall": {"top": (F / "PXL_20260412_103028669.mp4", 116.0), "top_focus": (0.5, 0.45),  # the big smile
                  "bottom": (F / "DJI_20260412103747_0002_D.MP4", 25.0), "bottom_focus": (0.55, 0.5),  # the falls
                  "lines": [("I THOUGHT", "white"), ("IT WAS DRY", "white"), ("NOPE", "gold")]},
    "pee": {"top": (F / "Drone shots" / "DJI_20260412174910_0003_D.MP4", 472.0), "top_focus": (0.6, 0.45),
            "bottom": (F / "DJI_20260412104554_0005_D.MP4", 271.0), "bottom_focus": (0.5, 0.5),  # thinking, in the river
            "lines": [("DID YOU", "white"), ("KNOW?", "gold"), ("75 LITRES", "white"), ("IN ONE POOL", "white")]},
    "koel": {"top": (F / "DJI_20260412223930_0012_D.MP4", 158.0), "top_focus": (0.45, 0.45),  # woken up at dawn
             "bottom_pic": HERE.parent / "ai_koel_01.png", "bottom_focus": (0.5, 0.0), "text_dy": -300,  # headline higher: the bird stays clear of it
             "lines": [("5:30 AM", "white"), ("THIS BIRD", "white"), ("SAYS", "white"), ("\"FOR REAL\"", "gold")]},
}


def panel(img: Image.Image, h: int, focus) -> Image.Image:
    return mt.punch(mt.cover(img, W, h, focus, 1.0, at=(0.5, 0.5)), 1.3, 1.12, 1.05)


def local(name: str) -> Path:
    s = SHORTS[name]
    split = int(H * 0.5)
    top = mt.frame(s["top"])
    if s.get("dark"):
        top = ImageEnhance.Brightness(top).enhance(1.6)
    bottom = Image.open(s["bottom_pic"]).convert("RGB") if "bottom_pic" in s else mt.frame(s["bottom"])
    if s.get("dark"):
        bottom = ImageEnhance.Brightness(bottom).enhance(1.6)
    img = Image.new("RGBA", (W, H))
    img.paste(panel(top, split + 120, s["top_focus"]), (0, 0))
    lower = panel(bottom, H - split + 120, s["bottom_focus"])
    mask = Image.new("L", (W, H), 0)
    a, b = (0, split + 90), (W, split - 90)  # slanted divider
    ImageDraw.Draw(mask).polygon([a, b, (W, H), (0, H)], fill=255)
    img.paste(lower, (0, split - 120), mask.crop((0, split - 120, W, H)))
    # soft dark band across the middle so the headline reads on any picture
    band = Image.new("L", (1, H))
    for y in range(H):
        band.putpixel((0, y), int(150 * max(0.0, 1 - abs(y - split) / (H * 0.3))))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dark.putalpha(band.resize((W, H)))
    img.alpha_composite(dark)
    d = ImageDraw.Draw(img)
    d.line([a, b], fill=mt.BLACK, width=60)
    d.line([a, b], fill=mt.YELLOW, width=30)
    lines = s["lines"]
    size, gap = 300, 330
    y0 = split - gap * (len(lines) - 1) / 2 + s.get("text_dy", 0)
    for i, (t, style) in enumerate(lines):
        xy = (W // 2 - 60, round(y0 + i * gap))  # a little left of centre: the player buttons sit on the right
        f = mt.font("anton", size)
        tw = ImageDraw.Draw(Image.new("L", (1, 1))).textlength(t, font=f)
        sz = min(size, int(size * (W - 360) / tw))  # long lines shrink to fit
        if style == "gold":
            mt.gold_text(img, xy, t, sz, "mm")
        else:
            mt.text(img, xy, t, sz, mt.WHITE, "mm", 0)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"short_{name}_local.jpg"
    img.convert("RGB").resize((1080, 1920), Image.LANCZOS).save(out, quality=93, optimize=True)
    print(out)
    return out


PROMPT = """Improve this YouTube Shorts thumbnail (vertical 9:16) so that more people click on it in the Shorts feed.

Keep:
- the same people with exactly the same faces, recognisable, not older, younger or more handsome (they are real people);
- the same story and the same two scenes: {scenes};
- the headline with exactly these words and nothing else written anywhere: {words}. Spell them exactly like that, big, bold, easy to read on a small phone screen, white and yellow (#F4C70F) letters with a black outline, in the middle of the picture, a little left of centre (the right edge is covered by the player buttons, the bottom fifth by the title).

Make it better: stronger, more vivid colours and light, more drama and emotion, a clearer focus on the faces and the key object, cleaner layout, like the best travel vlog Shorts thumbnails. One finished picture, no extra logos, no watermarks, no frames, no emojis."""

SCENES = {
    "camera": "at night, a shirtless man holds up his small handheld camera that three village boys just brought back to him, and the three smiling boys",
    "waterfall": "a happy man in a sun hat and sunglasses, and the wide waterfall Dray Nur in Vietnam that is full of water although he expected it dry",
    "pee": "a man in a river below a waterfall who looks thoughtful, as if he has to pee, and the waterfall seen from a drone",
    "koel": "a sleepy, annoyed man woken up at dawn in a hammock tent, and the bird that woke him: an Asian koel, glossy black with red eyes, sitting on a branch in the lower part of the picture, clearly below the headline (nothing may cover any letter)",
}


def improve(name: str, model: str) -> Path:
    key = next(line.split("=", 1)[1].strip() for line in
               (HERE.parents[2] / "pipeline" / ".env").read_text(encoding="utf-8-sig").splitlines()
               if line.startswith("OPENROUTER_API_KEY"))
    src = local(name)
    buf = io.BytesIO()
    Image.open(src).save(buf, "JPEG", quality=90)
    words = " / ".join(t for t, _ in SHORTS[name]["lines"])
    content = [{"type": "text", "text": PROMPT.format(scenes=SCENES[name], words=words)},
               {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}}]
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": "Bearer " + key},
                      json={"model": model, "messages": [{"role": "user", "content": content}],
                            "modalities": ["image", "text"], "image_config": {"aspect_ratio": "9:16"},
                            "usage": {"include": True}}, timeout=600)
    if not r.ok:
        raise SystemExit(f"generation failed ({r.status_code}): {r.text[:600]}")
    data = r.json()
    msg = data["choices"][0]["message"]
    images = msg.get("images") or []
    if not images:
        raise SystemExit(f"no image came back: {json.dumps(msg)[:600]}")
    raw = base64.b64decode(images[0]["image_url"]["url"].split(",", 1)[1])
    n = len(list(OUT.glob(f"short_{name}_ai_*.jpg"))) + 1
    out = OUT / f"short_{name}_ai_{n:02d}.jpg"
    Image.open(io.BytesIO(raw)).convert("RGB").resize((1080, 1920), Image.LANCZOS).save(out, quality=93)
    print(out, "cost:", (data.get("usage") or {}).get("cost"), "USD")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", nargs="*", metavar="SHORT", help="send these (or all) to Gemini for a better version")
    ap.add_argument("--model", default="google/gemini-3-pro-image")
    a = ap.parse_args()
    if a.ai is None:
        for n in SHORTS:
            local(n)
    else:
        for n in a.ai or SHORTS:
            improve(n, a.model)
