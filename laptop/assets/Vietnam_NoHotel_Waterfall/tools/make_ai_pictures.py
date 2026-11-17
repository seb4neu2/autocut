#!/usr/bin/env python3
"""AI pictures for the info cards (Gemini image model through OpenRouter), no text in the picture.

  python make_ai_pictures.py pho|milo [--model google/gemini-3-pro-image]
Writes ai_<name>_NN.png into the asset folder; build_plan places it as a picture next to its card.
Each picture costs a few cents (printed after the call). Key: OPENROUTER_API_KEY in pipeline/.env
"""

import argparse
import base64
import io
import json
from pathlib import Path

import requests
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE.parent

PROMPTS = {
    "pho": "A steaming bowl of Vietnamese pho bo (beef noodle soup) on a simple metal table at a roadside "
           "breakfast stall in rural Vietnam, morning light. Clear broth, flat rice noodles, thin slices of "
           "rare beef, spring onions, a plate of fresh herbs, lime wedges and chili beside it. Seen from slightly "
           "above, the bowl fills most of the frame. Photographic, appetising, warm colours. "
           "NO text, NO letters, NO logos anywhere.",
    "koel": "A male Asian koel (Eudynamys scolopaceus) perched on a bare branch at sunrise over a quiet river in "
            "Vietnam, singing with its beak open. Accurate to the real species: entirely glossy blue-black plumage, "
            "bright crimson-red eye, pale greenish-ivory bill, long tail. Soft golden dawn light, misty river and "
            "trees softly blurred behind, the bird sharp and filling most of the frame. Wildlife photograph, "
            "natural colours. NO text, NO letters, NO logos anywhere.",
    "milo": "A small green carton of Milo chocolate malt drink with a straw, the kind sold in Vietnamese corner "
            "shops, standing on a wooden shop counter, a few more cartons blurred behind it. Bright, cheerful, "
            "product-photo look, the green carton fills most of the frame. Keep any lettering on the carton "
            "minimal and do not add any other text or captions.",
}


def generate(name: str, model: str) -> Path:
    key = next(line.split("=", 1)[1].strip() for line in
               (HERE.parents[2] / "pipeline" / ".env").read_text(encoding="utf-8-sig").splitlines()
               if line.startswith("OPENROUTER_API_KEY"))
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": "Bearer " + key},
                      json={"model": model, "messages": [{"role": "user", "content": PROMPTS[name]}],
                            "modalities": ["image", "text"], "image_config": {"aspect_ratio": "1:1"},
                            "usage": {"include": True}}, timeout=600)
    if not r.ok:
        raise SystemExit(f"generation failed ({r.status_code}): {r.text[:600]}")
    data = r.json()
    msg = data["choices"][0]["message"]
    images = msg.get("images") or []
    if not images:
        raise SystemExit(f"no image came back: {json.dumps(msg)[:600]}")
    raw = base64.b64decode(images[0]["image_url"]["url"].split(",", 1)[1])
    n = len(list(OUT.glob(f"ai_{name}_*.png"))) + 1
    out = OUT / f"ai_{name}_{n:02d}.png"
    Image.open(io.BytesIO(raw)).convert("RGB").save(out)
    print(out, "cost:", (data.get("usage") or {}).get("cost"), "USD")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=PROMPTS)
    ap.add_argument("--model", default="google/gemini-3-pro-image")
    a = ap.parse_args()
    generate(a.name, a.model)
