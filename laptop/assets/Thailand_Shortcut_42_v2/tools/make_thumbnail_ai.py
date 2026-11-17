#!/usr/bin/env python3
"""AI-made thumbnail picture (Gemini image model through OpenRouter) + exact text added locally.

The model gets real frames from the video as references (face, lake, dogs) and paints the
picture WITHOUT any lettering, because image models misspell and repeat text. The words,
the price tag and the cross are drawn afterwards with the channel fonts, so they are exact
and easy to change:  python make_thumbnail_ai.py --text-only   redraws the text for free.

  python make_thumbnail_ai.py [--mood smile|shock] [--model google/gemini-3-pro-image]
Each generation costs a few cents (printed after the call). Key: OPENROUTER_API_KEY in pipeline/.env
"""

import argparse
import base64
import io
import json
import subprocess
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "youtube"
sys.path.insert(0, str(HERE))
import make_thumbnails as mt  # noqa: E402  (text helpers, frame grabber)

DOGS = ("43050_DJI_20240318_0098.MP4", 211.0)
MOODS = {
    "smile": "a big, relieved, exhausted grin, proud that he made it, looking straight into the camera",
    "shock": "wide eyes and open mouth, shocked and exhausted, looking straight into the camera",
}
PROMPT = """Create a vivid, high-contrast YouTube thumbnail picture, 16:9, with NO text, NO letters, NO numbers and NO logos anywhere.

Reference images, in order:
1. The man. Keep his real face, beard, straw hat, maroon t-shirt and backpack straps exactly recognisable as this person.
2. The lake with jungle islands, seen from a drone. Use it as the background.
3. The two dogs that guided him. Keep their real look (black and dark brown short-haired dogs).

Composition:
- Right third: the man as a large close-up portrait, chest up, with {mood}. Sweat and a little dirt on his face. A thin bright orange-yellow glow outline around him.
- Background: the lake and the green jungle islands in saturated turquoise and green, bright daylight.
- Bottom left on the water: a traditional Thai longtail boat, empty.
- Centre: a red dotted line winding down the jungle hillside to the water, like a hiking route on a map.
- Next to the man, lower centre: the two dogs walking.
- Keep the top left area (about 45 percent of the width, 40 percent of the height) free of important objects, it will carry a headline later. Keep the area above the boat free as well.
Style: punchy colours, sharp, photographic, slightly exaggerated like popular travel vlog thumbnails."""


def ref(img: Image.Image) -> dict:
    buf = io.BytesIO()
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(buf, "JPEG", quality=88)
    return {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}}


def generate(model: str, mood: str, face_src) -> Path:
    key = next(line.split("=", 1)[1].strip() for line in
               (HERE.parents[2] / "pipeline" / ".env").read_text(encoding="utf-8-sig").splitlines()
               if line.startswith("OPENROUTER_API_KEY"))
    content = [{"type": "text", "text": PROMPT.format(mood=MOODS[mood])},
               ref(mt.frame(face_src)), ref(mt.frame(mt.LAKE)), ref(mt.frame(DOGS))]
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": "Bearer " + key},
                      json={"model": model, "messages": [{"role": "user", "content": content}],
                            "modalities": ["image", "text"], "image_config": {"aspect_ratio": "16:9"},
                            "usage": {"include": True}}, timeout=600)
    if not r.ok:
        raise SystemExit(f"generation failed ({r.status_code}): {r.text[:600]}")
    data = r.json()
    msg = data["choices"][0]["message"]
    images = msg.get("images") or []
    if not images:
        raise SystemExit(f"no image came back: {json.dumps(msg)[:600]}")
    raw = base64.b64decode(images[0]["image_url"]["url"].split(",", 1)[1])
    n = len(list(OUT.glob(f"ai_picture_{mood}_*.png"))) + 1
    out = OUT / f"ai_picture_{mood}_{n:02d}.png"
    Image.open(io.BytesIO(raw)).convert("RGB").save(out)
    print(out, "cost:", (data.get("usage") or {}).get("cost"), "USD")
    return out


def add_text(picture: Path, mood: str) -> Path:
    W, H = mt.W, mt.H
    img = mt.cover(Image.open(picture).convert("RGB"), W, H).convert("RGBA")
    mt.text(img, (90, 250), "I WALKED!", 340, (255, 235, 20), "lm", 3)
    mt.text(img, (105, 555), "NEVER AGAIN!", 215, (240, 30, 25), "lm", 3, stroke=24)
    # price tag with a cross, above the boat
    tag = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(tag)
    x0, y0, x1, y1 = 120, 800, 900, 1010
    d.rounded_rectangle((x0 - 14, y0 - 14, x1 + 14, y1 + 14), 70, fill=(255, 255, 255, 255))
    d.rounded_rectangle((x0, y0, x1, y1), 60, fill=(225, 30, 25, 255))
    img.alpha_composite(tag.rotate(4, center=((x0 + x1) // 2, (y0 + y1) // 2), resample=Image.BICUBIC))
    mt.text(img, ((x0 + x1) // 2, (y0 + y1) // 2 - 4), "2,000 BAHT", 150, (255, 255, 255), "mm", 4, stroke=14)
    cross = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(cross)
    for a, b in (((x0 + 150, y0 - 110), (x1 - 150, y1 + 110)), ((x1 - 150, y0 - 110), (x0 + 150, y1 + 110))):
        d.line([a, b], fill=(0, 0, 0, 255), width=46)
    for a, b in (((x0 + 150, y0 - 110), (x1 - 150, y1 + 110)), ((x1 - 150, y0 - 110), (x0 + 150, y1 + 110))):
        d.line([a, b], fill=(255, 30, 25, 255), width=24)
    img.alpha_composite(cross)
    out = OUT / f"thumbnail_D_ai-{mood}.jpg"
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(out, quality=93, optimize=True)
    print(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mood", choices=MOODS, default="smile")
    ap.add_argument("--model", default="google/gemini-3-pro-image")
    ap.add_argument("--text-only", action="store_true", help="reuse the latest generated picture, only redraw the text")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if args.text_only:
        picture = sorted(OUT.glob(f"ai_picture_{args.mood}_*.png"))[-1]
    else:
        picture = generate(args.model, args.mood, mt.FACE_SMILE if args.mood == "smile" else mt.FACE_TIRED)
    add_text(picture, args.mood)


if __name__ == "__main__":
    main()
