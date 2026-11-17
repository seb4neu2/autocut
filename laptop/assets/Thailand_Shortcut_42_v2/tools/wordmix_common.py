"""Building blocks for word-mix (mashup) Short plans: narrator questions over freeze frames,
answers made of single-word clips.

Mashup rule (user, 2026-10-14): every word is its own clip, picture and sound from the moment the
user says it, single words only. Each take is given as (word, clip prefix, rough time from the
transcript JSON); wordmix_precise.refine() finds the exact cut with local whisper and the audio.
"""

import json
import sys
from pathlib import Path

import numpy as np

from wordmix_precise import FOLDER, SR, _load, _whisper, refine

LEVEL = -20.0   # dB peak every word cut is brought to, so quiet takes match
_clips = {p.name[:5]: p.name for p in FOLDER.glob("*.MP4")}


def W(word: str, clip: str, src: float) -> dict:
    """One word = one clip, cut precisely, picture and sound from the same moment."""
    name = _clips[clip[:5]]
    start, end, info = refine(name, src, word)
    vol = round(min(max(10 ** ((LEVEL - info["level_db"]) / 20), 0.6), 6.0), 2)
    return {"clip": name, "start": start, "end": end, "snap": False, "caption": False, "text": word,
            "volume": vol}


def answer(text: str, *words, gap: float = 0.15, word_gap: float = 0.0, **first) -> list[dict]:
    """The user's answer: single-word clips, captioned as one line. `word_gap` leaves a beat between
    words (slow, dramatic answers); `gap` a pause after the line."""
    items = [W(*w) for w in words]
    for it in items[:-1]:
        it["pad_after"] = word_gap
    items[0].update(line=text, line_items=len(items), **first)
    items[-1]["pad_after"] = gap
    return items


def ask(text: str, tagged: str, still: str, at: float, bw: bool = True, **kw) -> dict:
    """A narrator line over a freeze frame that lasts as long as the line."""
    return {"freeze": still if (FOLDER / still).exists() else _clips[still[:5]], "at": at, "bw": bw,
            "narration": {"text": text, "tagged": tagged, "offset": 0.15}, "tail": 0.2, **kw}


def label(text: str, at: float, duration: float, y: float = 0.22) -> dict:
    # text splashes in Shorts use CapCut size 25 (CLAUDE.md); label size is px on a 1080 canvas
    return {"gfx": {"type": "label", "text": text, "size": 250, "y": y}, "at": at, "duration": duration}


def sentence_check(timeline: list) -> None:
    """Plays every built answer as one sentence to local whisper and prints what it hears."""
    sys.stdout.reconfigure(encoding="utf-8")
    i = 0
    while i < len(timeline):
        it = timeline[i]
        if "line" not in it:
            i += 1
            continue
        parts = [np.zeros(8000, np.float32)]
        for w in timeline[i:i + it["line_items"]]:
            a = _load(w["clip"])
            parts.append(a[int(w["start"] * SR):int(w["end"] * SR)] * w.get("volume", 1.0))
            parts.append(np.zeros(int(w.get("pad_after", 0.0) * SR), np.float32))
        parts.append(np.zeros(8000, np.float32))
        segs, _ = _whisper().transcribe(np.concatenate(parts).astype(np.float32), language="en", beam_size=5,
                                        vad_filter=False, condition_on_previous_text=False)
        print(f"  {it['line']!r:34} heard {' '.join(s.text.strip() for s in segs)!r}")
        i += it["line_items"]


def write_plan(name: str, timeline: list, music: tuple) -> Path:
    full = json.loads((FOLDER / "plan_v5.json").read_text(encoding="utf-8"))
    p = {"name": f"Thailand_Shortcut_42_Wordmix_{name}", "assets": "Thailand_Shortcut_42_v2",
         "canvas": "vertical", "fps": 60, "narrator_voice": full["narrator_voice"],
         "narrator_settings": full["narrator_settings"], "narration_lufs": full["narration_lufs"],
         "sfx": full["sfx"], "music": {k: full["music"][k] for k in music}, "timeline": timeline}
    out = FOLDER / f"plan_wordmix_{name}.json"
    out.write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, len(timeline), "items")
    sentence_check(timeline)
    return out
