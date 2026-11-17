#!/usr/bin/env python3
"""Writes plan_v5.json from plan_v4.json: same cut, new narrator, and "forty two minutes".

- Narrator: Richard Basston - Deep on Eleven v4 (see C:\\Work\\AutoCut\\CLAUDE.md). Every line
  carries audio tags written by Claude; "tagged" is what is spoken, "text" what the captions show.
- The opening line uses the take the user made on the ElevenLabs website on 2026-10-12
  (same voice, model and settings), so it costs nothing. Its caption times come from a local
  whisper pass over that file.
- Taken over from the user's hand edits in the v4 draft: the corrected caption with
  "Forty two" in orange, and the quieter opening line.
- The daytime lo-fi track is pinned, so no music is generated.
"""

import json
import shutil
from pathlib import Path

FOLDER = Path(r"D:\Backup\VlogX")
ASSETS = Path(__file__).resolve().parent.parent
VOICE = "i6icHCFicH3kzHTat04x"  # Richard Basston - Deep
WEB_TAKE = "ElevenLabs_2026-10-12T06_50_00_Richard Basston - Deep_pvc_sp107_s50_sb50_v4.mp3"
OPENING = "narration_richard-basston_this-is-sebastian-forty_web-take.mp3"
OPENING_SENTENCES = [  # word times of the web take (faster-whisper large-v3-turbo)
    {"text": "This is Sebastian.", "start": 0.0, "end": 1.2},
    {"text": "Forty two minutes earlier, he had a simple choice: pay two thousand baht for a boat to the lake.",
     "start": 2.12, "end": 8.16},
    {"text": "...or find his own way down.", "start": 8.5, "end": 9.98},
    {"text": "He chose the shortcut.", "start": 10.94, "end": 12.4},
]
ORANGE = [1.0, 0.5, 0.0]

# Loudness: George's lines sat at about -23.7 LUFS and the music levels were set against that.
# The user turned the opening line down to 0.62 in the v4 draft (-24.2 LUFS -> about -28.3).
NARRATION_LUFS = -23.7
OPENING_LUFS = -28.3

# first words of the v4 line -> spoken version with audio tags (words unchanged)
TAGGED = {
    "Spoiler:": "[deadpan] Spoiler: it was not a good idea.",
    "And then, out of nowhere": "[pleasantly surprised] And then, out of nowhere, two local guides appeared. "
                                "[amused] Their fee? Zero baht.",
    "What followed": "[low, ominous voice] What followed were the longest forty minutes of his life.",
    "Tonight's hotel": "[warm, relaxed] Tonight's hotel: a fishermen's hut on the lake. [wry] Price? Also zero baht.",
    "But the night": "[hushed, intrigued] But the night wasn't over. His hosts had one more thing to show him: "
                     "a torch, a diving mask... and a pitch-black lake.",
    "Budget spent": "[matter-of-fact] Budget spent: zero. Water left: zero. [warm] Dogs befriended: two. "
                    "[curious] So... would he ever take a shortcut again?",
}


def strip_tags(tagged: str) -> str:
    out, depth = "", 0
    for c in tagged:
        depth += c == "["
        if not depth:
            out += c
        depth -= c == "]"
    return " ".join(out.split())


def main() -> None:
    import sys
    sys.path.insert(0, str(ASSETS.parent.parent / "pipeline"))
    import assets

    plan = json.loads((FOLDER / "plan_v4.json").read_text(encoding="utf-8"))
    plan["name"] = "Thailand_Shortcut_42_v5"
    plan["narrator_voice"] = VOICE
    plan["narrator_settings"] = {"model": "eleven_v4", "stability": 0.5, "similarity": 0.5, "speed": 1.07}
    plan["narration_lufs"] = NARRATION_LUFS
    plan["music"]["lofi_day"]["file"] = "music_lofi-hiphop-deep-bass-chill-day_140s_8ac9478c2d22.mp3"

    opening = ASSETS / OPENING
    if not opening.exists():
        shutil.copy2(ASSETS / WEB_TAKE, opening)
    opening.with_suffix(".json").write_text(json.dumps({"sentences": OPENING_SENTENCES}, ensure_ascii=False, indent=1),
                                            encoding="utf-8")

    done = set()
    for item in plan["timeline"]:
        narr = item.get("narration")
        if narr and narr["text"].startswith("This is Sebastian."):
            narr["text"] = narr["text"].replace("Forty minutes earlier", "Forty two minutes earlier")
            narr["file"] = OPENING
            narr["volume"] = assets.volume_for(opening, OPENING_LUFS)
            narr["highlight"] = {"Forty two": ORANGE}
            done.add("opening")
        elif narr:
            key = next(k for k in TAGGED if narr["text"].startswith(k))
            assert strip_tags(TAGGED[key]) == narr["text"], f"tags changed the words: {key}"
            narr["tagged"] = TAGGED[key]
            done.add(key)
        for ov in item.get("overlay", []):  # the overlay fonts in CapCut have no baht sign
            for row in ov["gfx"].get("rows", []):
                row[1] = row[1].replace("฿", "BAHT")
    assert done == set(TAGGED) | {"opening"}, f"narration lines not found: {set(TAGGED) | {'opening'} - done}"

    out = FOLDER / "plan_v5.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, len(plan["timeline"]), "items")


if __name__ == "__main__":
    main()
