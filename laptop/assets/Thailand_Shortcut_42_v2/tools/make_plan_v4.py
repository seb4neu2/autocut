#!/usr/bin/env python3
"""Writes plan_v4.json from plan_v2.json: the same cut plus silent footage the shot log found.

Nothing is removed or re-timed; b-roll is inserted after the lines it illustrates. The
late-night music is pinned to the existing file and restarted at "The Night", so the longer
cut generates no new music. Only new paid asset: one narration line.
"""

import json
from pathlib import Path

FOLDER = Path(r"D:\Backup\VlogX")
NIGHT_TRACK = "music_lofi-hiphop-deep-bass-late-night_165s_3c251802dd23.mp3"

DOGS, LAKE, LOCALS, FISHING, SNORKEL = (
    "42850_DJI_20240318_0094.MP4", "43050_DJI_20240318_0098.MP4", "43150_DJI_20240318_0100.MP4",
    "43200_DJI_20240318_0101.MP4", "43350_DJI_20240318_0001.MP4",
)

# after the item whose text / narration starts with the key -> items to insert
INSERT_AFTER = {
    "And then, out of nowhere": [  # first clear look at the guide
        {"broll": DOGS, "start": 5.5, "end": 12.5},
    ],
    "Yeah, I have no idea how I'm going to get into": [  # the shore he has to get down to
        {"broll": LAKE, "start": 163.5, "end": 171.5},
    ],
    "They just have seen something": [  # the kids at the bank with a stick
        {"broll": LOCALS, "start": 71.0, "end": 77.0, "volume": 0.4},
    ],
    "Wow. That's big.": [  # boy fishing at dusk, seen from behind
        {"broll": FISHING, "start": 5.0, "end": 12.0, "volume": 0.4},
    ],
    "I love it that it's so peaceful": [  # still lake with the floating hut
        {"broll": LOCALS, "start": 95.0, "end": 102.0, "volume": 0.4},
    ],
    "@broll 43150_DJI_20240318_0100.MP4 150.0": [  # night snorkelling, filmed between 0103 and 0002
        {"broll": SNORKEL, "start": 33.0, "end": 41.5, "volume": 0.3,
         "narration": {"text": "But the night wasn't over. His hosts had one more thing to show him: "
                               "a torch, a diving mask... and a pitch-black lake.", "offset": 0.3}},
        {"broll": SNORKEL, "start": 62.5, "end": 67.5, "volume": 0.6},
        {"broll": SNORKEL, "start": 79.0, "end": 87.0, "volume": 0.6},
        {"broll": SNORKEL, "start": 100.0, "end": 105.0, "volume": 0.6},
    ],
}


def key_of(item: dict) -> str:
    if "broll" in item:
        tag = f'@broll {item["broll"]} {item["start"]}'
        return tag + " " + (item.get("narration") or {}).get("text", "")
    return item.get("text") or (item.get("narration") or {}).get("text", "")


def main() -> None:
    plan = json.loads((FOLDER / "plan_v2.json").read_text(encoding="utf-8"))
    plan["name"] = "Thailand_Shortcut_42_v4"
    night = plan["music"]["lofi_night"]
    night.pop("prompt", None)
    night["file"] = NIGHT_TRACK
    plan["music"]["lofi_night_2"] = {**night, "skip": 24.0, "fade_in": 1.5}

    timeline, done = [], set()
    for item in plan["timeline"]:
        if item.get("section") == "The Night":
            item["music"] = "lofi_night_2"
        timeline.append(item)
        k = key_of(item)
        narr = (item.get("narration") or {}).get("text", "")
        for key, extra in INSERT_AFTER.items():
            if key not in done and (k.startswith(key) or narr.startswith(key)):
                timeline.extend(extra)
                done.add(key)
    missing = set(INSERT_AFTER) - done
    assert not missing, f"anchor not found: {missing}"
    plan["timeline"] = timeline
    out = FOLDER / "plan_v4.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, len(timeline), "items")


if __name__ == "__main__":
    main()
