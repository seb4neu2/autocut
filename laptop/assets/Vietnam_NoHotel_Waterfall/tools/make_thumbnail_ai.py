#!/usr/bin/env python3
"""AI-made version of thumbnail B (Gemini image model through OpenRouter) + exact text added locally.

The model gets three real frames as references (the camera hand-over at night, the falls, the campfire)
and paints one scene WITHOUT any lettering; the words are drawn afterwards with the channel fonts.
  python make_thumbnail_ai.py [--model google/gemini-3-pro-image]
  python make_thumbnail_ai.py --text-only ai_picture_camera_01.png   redraws the text for free
Each generation costs a few cents (printed after the call). Key: OPENROUTER_API_KEY in pipeline/.env
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
OUT = HERE.parent / "youtube"
sys.path.insert(0, str(HERE))
import make_thumbnails as mt  # noqa: E402  (text helpers, frame grabber)

PROMPT = """Create ONE single continuous photograph that fills the whole 16:9 frame: no split screen, no panels, no collage, no borders. A vivid, high-contrast YouTube thumbnail picture with NO text, NO letters, NO numbers and NO logos anywhere.

Reference images, in order:
1. The people: a shirtless European man with short brown hair and stubble, holding up a small black handheld gimbal camera (a DJI Osmo Pocket), and three Vietnamese village boys next to him (one in a white shirt with small dots, one in a dark green jacket, one in a black hoodie). This is a real photo: keep every face exactly as it is, the same people, the same expressions, recognisable. Do not make anyone older, younger or more handsome.
2. The waterfall (Dray Nur, Vietnam): a wide curtain of white water falling over a long rock wall into a river pool. Use it as the background.
3. The campfire: a tall, bright bonfire on the sandy riverbank.

Composition:
- Night scene. The man and the boys stand in the left two thirds, from the chest up, close to the viewer, like a group selfie. The man is on the left and holds the small camera up towards the viewer, clearly visible, proudly, as if he just got it back.
- Behind them: the waterfall at night, lit by moonlight and the firelight, the white water clearly visible.
- A big, tall campfire behind and to the right of the group, flames and sparks rising, its warm orange light on their faces and shoulders.
- The same scene continues seamlessly into the right third: the waterfall's rock wall and the river run on to the right edge, the fire light fades into the night there. That right third is darker and calm, free of faces and important objects: it will carry a headline later.
Style: punchy colours, warm orange firelight against deep blue night, sharp, photographic, like popular travel vlog thumbnails."""


def ref(img: Image.Image) -> dict:
    buf = io.BytesIO()
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(buf, "JPEG", quality=88)
    return {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}}


def generate(model: str) -> Path:
    key = next(line.split("=", 1)[1].strip() for line in
               (HERE.parents[2] / "pipeline" / ".env").read_text(encoding="utf-8-sig").splitlines()
               if line.startswith("OPENROUTER_API_KEY"))
    people = ImageEnhance.Brightness(mt.frame(mt.BOYS2)).enhance(1.6)  # the night frame is dark; show the faces
    content = [{"type": "text", "text": PROMPT}, ref(people), ref(mt.frame(mt.FALLS2)), ref(mt.frame(mt.FIRE2))]
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
    n = len(list(OUT.glob("ai_picture_camera_*.png"))) + 1
    out = OUT / f"ai_picture_camera_{n:02d}.png"
    Image.open(io.BytesIO(raw)).convert("RGB").save(out)
    print(out, "cost:", (data.get("usage") or {}).get("cost"), "USD")
    return out


def lettering(picture: Path, seam: float | None = None) -> None:
    """Headline on the right. `seam`: where the model left a hard split edge (0..1 of the width); a slanted
    black and yellow divider like thumbnail A covers it, and the panel right of it is darkened for the text."""
    img = mt.cover(Image.open(picture).convert("RGB"), mt.W, mt.H).convert("RGBA")
    if seam:
        x = seam * mt.W
        top, bottom = (x + 28, 0), (x - 28, mt.H)
        dark = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(dark).polygon([top, (mt.W, 0), (mt.W, mt.H), bottom], fill=(0, 0, 0, 95))
        img.alpha_composite(dark)
        d = ImageDraw.Draw(img)
        d.line([top, bottom], fill=mt.BLACK, width=64)
        d.line([top, bottom], fill=mt.YELLOW, width=32)
    mt.shade(img, "right", 110, 0.35)
    mt.text(img, (mt.W - 80, 230), "LOST MY", 230, mt.WHITE, "rm", -2)
    mt.text(img, (mt.W - 80, 470), "CAMERA", 230, mt.WHITE, "rm", -2)
    mt.gold_text(img, (mt.W - 80, 960), "THEY BROUGHT", 190, "rm")
    mt.gold_text(img, (mt.W - 80, 1200), "IT BACK", 250, "rm")
    mt.save(img, f"thumbnail_B3_{picture.stem.replace('ai_picture_', '')}.jpg")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/gemini-3-pro-image")
    ap.add_argument("--text-only", metavar="PICTURE")
    ap.add_argument("--seam", type=float, help="x of a hard split edge in the picture, 0..1 of its width")
    a = ap.parse_args()
    lettering(OUT / a.text_only if a.text_only else generate(a.model), a.seam)
