#!/usr/bin/env python3
"""Writes the plans for three vertical Shorts of the Thailand shortcut video:

  plan_short_dogs.json    "Two stray dogs guided me through the jungle"
  plan_short_boat.json    "I refused to pay 2,000 baht for a boat"
  plan_short_hotel.json   "Free hotel on a lake in Thailand"

Every narration line, sound effect and music track already exists in the asset folder
(the tagged narration text must stay word for word the same to hit the cache), and the
dialogue cuts are ones already verified for the main video, so building costs nothing.
Build each with:  python pipeline/build_plan.py <plan> D:\\Backup\\VlogX
"""

import json
from pathlib import Path

FOLDER = Path(r"D:\Backup\VlogX")
C91, C92, C93, C94, C95, C96, C97, C98, C99, C100 = (
    "42700_DJI_20240318_0091.MP4", "42750_DJI_20240318_0092.MP4", "42800_DJI_20240318_0093.MP4",
    "42850_DJI_20240318_0094.MP4", "42900_DJI_20240318_0095.MP4", "42950_DJI_20240318_0096.MP4",
    "43000_DJI_20240318_0097.MP4", "43050_DJI_20240318_0098.MP4", "43100_DJI_20240318_0099.MP4",
    "43150_DJI_20240318_0100.MP4")
DRONE, DRONE2 = "DJI_0300.MP4", "DJI_0301.MP4"

GUIDES = {"text": "And then, out of nowhere, two local guides appeared. Their fee? Zero baht.",
          "tagged": "[pleasantly surprised] And then, out of nowhere, two local guides appeared. [amused] Their fee? Zero baht."}
SPOILER = {"text": "Spoiler: it was not a good idea.", "tagged": "[deadpan] Spoiler: it was not a good idea."}
HOTEL = {"text": "Tonight's hotel: a fishermen's hut on the lake. Price? Also zero baht.",
         "tagged": "[warm, relaxed] Tonight's hotel: a fishermen's hut on the lake. [wry] Price? Also zero baht."}
WATER = {"text": "They gave him clean water. He shared the food he had brought.",
         "tagged": "[warm] They gave him clean water. He shared the food he had brought."}


def label(text: str, at: float = 0.0, duration: float = 2.6, **kw) -> dict:
    return {"gfx": {"type": "label", "text": text, **kw}, "at": at, "duration": duration}


def cta(duration: float) -> dict:
    return label("FULL VIDEO\nON THE CHANNEL", 0.2, duration - 0.2, y=0.2)


def base(name: str, timeline: list) -> dict:
    full = json.loads((FOLDER / "plan_v5.json").read_text(encoding="utf-8"))
    music = {k: {**full["music"][k]} for k in ("trouble", "reveal", "lofi_day")}
    music["trouble"].update(dialog=0.1, open=0.4)
    music["reveal"].update(dialog=0.16, open=0.6)
    return {"name": name, "assets": "Thailand_Shortcut_42_v2", "canvas": "vertical", "fps": 60,
            "narrator_voice": full["narrator_voice"], "narrator_settings": full["narrator_settings"],
            "narration_lufs": full["narration_lufs"], "sfx": full["sfx"], "music": music, "timeline": timeline}


DOGS = [
    {"clip": C93, "start": 16.44, "end": 18.48, "text": "I have no idea how to get down there.", "music": "trouble",
     "overlay": [label("LOST IN THE\nTHAI JUNGLE", 0.0, 2.3)]},
    {"broll": C96, "start": 72.0, "end": 74.8, "x": 1.26, "narration": {**GUIDES, "offset": 0.2},
     "sfx": [{"id": "levelup", "at": 2.6}]},
    {"broll": C94, "start": 9.3, "end": 12.5, "x": -0.3},
    {"clip": C94, "start": 101.6, "end": 103.14, "text": "I will follow them."},
    {"clip": C94, "start": 107.16, "end": 110.12, "text": "They know the best way, hopefully."},
    {"clip": C95, "start": 28.32, "end": 34.06,
     "text": "I think this is the path. If they go there, I go there. Okay, let's follow the dogs."},
    {"clip": C96, "start": 281.02, "end": 287.78, "text": "Thank you dogs, you found the best way ever.", "music": "lofi_day"},
    {"clip": C98, "start": 208.8, "end": 212.0, "text": "Hi doggies. We arrived.", "x": 0.5, "overlay": [cta(3.3)]},
]

BOAT = [
    {"clip": C91, "start": 89.86, "end": 96.1, "text": "and it costs like two thousand baht to go with the boat.",
     "overlay": [{"gfx": {"type": "sticker", "text": "2,000 BAHT", "sub": "for a boat ride?!"}, "at": 0.9, "duration": 3.4}],
     "sfx": [{"id": "chaching", "at": 0.9}]},
    {"clip": C91, "start": 107.34, "end": 113.6, "text": "So I decided to go around and find a way in for myself."},
    {"freeze": C91, "at": 116.4, "narration": SPOILER, "sfx": [{"id": "sting", "at": 0.1}]},
    {"clip": C92, "start": 69.9, "end": 71.34, "text": "It's fucking far.", "music": "trouble"},
    {"broll": C97, "start": 10.0, "end": 16.0, "speed": 3.0, "sfx": [{"id": "whoosh", "at": 0.0}]},
    {"broll": C97, "start": 36.0, "end": 42.0, "speed": 3.0},
    {"clip": C96, "start": 275.36, "end": 278.28, "text": "What am I doing here? This is ridiculous."},
    {"clip": C96, "start": 114.8, "end": 117.58, "text": "Are you fucking kidding me?"},
    {"clip": C98, "start": 2.66, "end": 5.52, "text": "Last steps. I am there."},
    {"broll": DRONE, "start": 58.0, "end": 65.0, "music": "reveal", "sfx": [{"id": "impact", "at": 0.0}],
     "overlay": [label("WORTH IT?", 1.0, 3.0, accent_line=0)]},
    {"clip": C98, "start": 34.2, "end": 35.24, "text": "Never again."},
    {"broll": DRONE, "start": 66.0, "end": 68.5, "overlay": [cta(2.5)]},
]

HOTEL_CUT = [
    {"broll": DRONE, "start": 58.0, "end": 63.5, "music": "reveal", "sfx": [{"id": "impact", "at": 0.0}],
     "overlay": [label("FREE HOTEL\nON A LAKE?", 0.2, 3.0)]},
    {"clip": C98, "start": 52.56, "end": 55.9, "text": "But look at this view. Ridiculous."},
    {"broll": DRONE, "start": 181.0, "end": 188.0, "narration": {**HOTEL, "offset": 0.3}, "music": "lofi_day"},
    {"broll": DRONE2, "start": 0.5, "end": 5.5, "x": 0.9},
    {"broll": C100, "start": 95.0, "end": 100.0, "x": -1.6, "volume": 0.4, "narration": {**WATER, "offset": 0.4}},
    {"clip": C99, "start": 62.92, "end": 64.98, "text": "I just tried this wine."},
    {"clip": C99, "start": 73.24, "end": 75.84, "pad_after": 0.0, "text": "It is quite strong, but very tasty."},
    {"broll": DRONE, "start": 97.0, "end": 102.0, "overlay": [label("COST OF THE DAY:\n0 BAHT", 0.2, 2.2), cta(2.4) | {"at": 2.6}]},
]


def main() -> None:
    for name, cut in (("dogs", DOGS), ("boat", BOAT), ("hotel", HOTEL_CUT)):
        out = FOLDER / f"plan_short_{name}.json"
        out.write_text(json.dumps(base(f"Thailand_Shortcut_42_Short_{name}", cut), ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(out, len(cut), "items")


if __name__ == "__main__":
    main()
