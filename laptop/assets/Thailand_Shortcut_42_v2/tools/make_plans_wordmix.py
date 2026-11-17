#!/usr/bin/env python3
"""Writes the plans for four experimental vertical Shorts made of single words cut together
into sentences the user never said (word mix), from the Thailand shortcut footage:

  plan_wordmix_secret.json   "I took the boat. Two thousand baht. Nobody will know." -> the real hike
  plan_wordmix_dog.json      the dog speaks with the user's voice
  plan_wordmix_review.json   deadpan review -> "Never again. Never go shortcuts."
  plan_wordmix_wine.json     "I don't drink" -> "I need water. I have wine. Wine is water."

Word cuts come from wordmix/candidates.json (wordmix_find.py: trimmed on the audio and checked
by local whisper). PICK chooses a take when the best-ranked one is not wanted. No paid assets:
music and sound effects are the ones already in the asset folder.
Build each with:  python pipeline/build_plan.py <plan> D:\\Backup\\VlogX
"""

import json
from pathlib import Path

FOLDER = Path(r"D:\Backup\VlogX")
HERE = Path(__file__).resolve().parent.parent
CANDS = json.loads((HERE / "wordmix" / "candidates.json").read_text(encoding="utf-8"))
C91, C92, C93, C94, C95, C96, C97, C98, C99, C100 = (
    "42700_DJI_20240318_0091.MP4", "42750_DJI_20240318_0092.MP4", "42800_DJI_20240318_0093.MP4",
    "42850_DJI_20240318_0094.MP4", "42900_DJI_20240318_0095.MP4", "42950_DJI_20240318_0096.MP4",
    "43000_DJI_20240318_0097.MP4", "43050_DJI_20240318_0098.MP4", "43100_DJI_20240318_0099.MP4",
    "43150_DJI_20240318_0100.MP4")

# word -> (clip prefix, source time) of the take to use, where the best-ranked one is not wanted
PICK: dict[str, tuple[str, float]] = {
    "i": ("42700", 37.58), "took": ("42700", 164.14), "the": ("42700", 50.30), "boat": ("42700", 95.68),
    "nobody": ("42700", 115.36), "will": ("42700", 34.20), "know": ("43250", 4.80), "dogs": ("42900", 33.60),
    "am": ("42950", 275.70), "dog": ("42800", 28.38), "follow": ("42850", 102.50), "me": ("42850", 257.44),
    "tired": ("42850", 142.88), "sweaty": ("42700", 154.70), "ridiculous": ("42950", 277.46),
    "no": ("42700", 28.10), "water": ("42700", 152.34), "dangerous": ("42850", 275.56),
    "i'm": ("42700", 13.40), "five": ("43100", 15.80), "stars": ("43300", 42.00), "go": ("42700", 95.10),
    "need": ("42750", 21.72), "have": ("42700", 144.08), "wine": ("43100", 64.60), "is": ("42700", 59.42),
}
LEVEL = -20.0   # dB peak every word cut is brought to, so quiet takes (night, far from the mic) match

# a dog looking down into the camera (filmed upside down, turned upright)
DOG_FACE = {"broll": C98, "start": 194.5, "rotate": 180}
DOGS_WALK = {"broll": C94, "start": 7.0, "x": -0.6}


def take(word: str, pick=None) -> dict:
    cands = CANDS[word]
    pick = pick or PICK.get(word)
    if pick:
        return next(c for c in cands if c["clip"].startswith(pick[0]) and abs(c["src"] - pick[1]) < 0.05)
    return cands[0]


def W(word: str, pick=None, **kw) -> dict:
    """One single-word cut, cut exactly on the trimmed times, no caption of its own."""
    c = dict(take(word, pick))
    if word == "hello":
        c["end"] = 11.10   # the take runs into "forty-two"
    vol = round(min(max(10 ** ((LEVEL - c["level_db"]) / 20), 0.6), 6.0), 2)
    return {"clip": c["clip"], "start": c["start"], "end": c["end"], "snap": False, "caption": False,
            "text": word, "volume": vol, **kw}


def P(clip: str, start: float, end: float, text: str) -> dict:
    """A few words said together in the footage, used as one piece of a built sentence."""
    return {"clip": clip, "start": start, "end": end, "pad_before": 0.04, "pad_after": 0.04, "caption": False,
            "text": text}


def line(text: str, *words, gap: float = 0.18, **first) -> list[dict]:
    """A sentence built from single-word cuts, captioned as one line; a short pause after it."""
    items = [W(w) if isinstance(w, str) else w if isinstance(w, dict) else W(*w) for w in words]
    items[0].update(line=text, line_items=len(items), **first)
    items[-1]["pad_after"] = gap
    return items


def over(items: list[dict], shot: dict) -> list[dict]:
    """Voice of these word cuts over one continuous shot (starting at shot["start"])."""
    for i, it in enumerate(items):
        it["over"] = {k: v for k, v in shot.items() if k != "start" or i == 0}
    return items


def hook(text: str, duration: float, y: float = 0.2) -> dict:
    # text splashes in Shorts use CapCut size 25 (CLAUDE.md); label size is px on a 1080 canvas
    return {"gfx": {"type": "label", "text": text, "size": 250, "y": y}, "at": 0.0, "duration": duration}


def cta(at: float, duration: float) -> dict:
    return {"gfx": {"type": "label", "text": "WATCH\nTHE FULL\nVIDEO", "size": 250, "y": 0.27, "accent_line": 1},
            "at": at, "duration": duration}


def base(name: str, timeline: list) -> dict:
    full = json.loads((FOLDER / "plan_v5.json").read_text(encoding="utf-8"))
    music = {k: {**full["music"][k]} for k in ("trouble", "reveal", "lofi_day", "lofi_night")}
    return {"name": name, "assets": "Thailand_Shortcut_42_v2", "canvas": "vertical", "fps": 60,
            "sfx": full["sfx"], "music": music, "timeline": timeline}


def secret() -> list:
    t = []
    t += line("I took the boat.", "i", "took", "the", "boat", overlay=[hook("MY\nSECRET", 1.6)])
    t += line("Two thousand baht.", "two", "thousand", "baht", sfx=[{"id": "chaching", "at": 0.0}])
    t += line("Nobody will know.", "nobody", "will", "know", gap=0.5, sfx=[{"id": "sting", "at": 0.05}])
    t += [
        {"broll": C97, "start": 10.0, "end": 16.0, "speed": 3.0, "music": "trouble",
         "sfx": [{"id": "scratch", "at": 0.0}]},
        {"clip": C92, "start": 69.9, "end": 71.34, "text": "It's fucking far."},
        {"broll": C97, "start": 36.0, "end": 42.0, "speed": 3.0},
        {"clip": C96, "start": 114.8, "end": 117.58, "text": "Are you fucking kidding me?"},
        {"clip": C98, "start": 2.66, "end": 5.52, "text": "Last steps. I am there."},
    ]
    t += over(line("The dogs know.", ("the", ("42700", 87.38)), "dogs", "know", gap=0.6, music="stop",
                   sfx=[{"id": "sting", "at": 0.0}]), DOG_FACE)
    t[-1]["overlay"] = [cta(0.3, 1.5)]
    return t


def dog() -> list:
    t = []
    hello = line("Hello.", "hello", gap=0.3, overlay=[hook("THE DOG\nSPEAKS", 1.8)])
    am = line("I am the dog.", "i", "am", ("the", ("42700", 87.38)), "dog", gap=0.4)
    over(hello + am, DOG_FACE)
    know = line("I know the best way.", ("i", ("42700", 34.10)), P(C94, 107.34, 108.42, "know the best way"), gap=0.25)
    follow = line("Follow me.", "follow", "me", gap=0.6, sfx=[{"id": "levelup", "at": 0.0}])
    over(know + follow, DOGS_WALK)
    know[0]["music"] = "trouble"
    t += hello + am + know + follow
    t += [
        {"clip": C94, "start": 101.6, "end": 103.14, "text": "I will follow them."},
        {"broll": C96, "start": 72.0, "end": 76.0, "speed": 2.0, "x": 1.26},
        {"clip": C96, "start": 114.8, "end": 117.58, "text": "Are you fucking kidding me?"},
    ]
    # the dog's comment on the man behind it, over the man's own sweaty face
    tired = line("He's tired.", "he's", "tired", gap=0.25)
    sweaty = line("He's sweaty.", "he's", "sweaty", gap=0.25)
    ridic = line("Ridiculous.", "ridiculous", gap=0.5)
    over(tired + sweaty + ridic, {"broll": C94, "start": 214.0})
    t += tired + sweaty + ridic
    t += [
        {"clip": C96, "start": 281.02, "end": 283.74, "text": "Thank you dogs, you found the best way ever.",
         "music": "lofi_day"},
        {"clip": C96, "start": 286.4, "end": 287.78, "text": "They actually wanted to go up.", "pad_after": 1.2,
         "sfx": [{"id": "crickets", "at": 1.3}], "overlay": [cta(1.4, 1.2)]},
    ]
    return t


def review() -> list:
    t = []
    t += line("Beautiful place.", P(C91, 25.38, 26.40, "beautiful place"), gap=0.35, overlay=[hook("HONEST\nREVIEW", 1.6)],
              music="lofi_day")
    t += line("No water.", "no", "water", gap=0.35)
    t += line("Trash everywhere.", P(C92, 44.0, 45.1, "trash everywhere"), gap=0.35)
    t += line("I'm sweaty.", P(C91, 154.27, 155.15, "I'm sweaty"), gap=0.35)
    t += line("Many stars.", P("43300_DJI_20240318_0103.MP4", 41.40, 42.55, "many stars"), gap=0.4, sfx=[{"id": "levelup", "at": 0.0}])
    t += line("I will go again.", ("i", ("42700", 34.10)), "will", "go", "again", gap=0.5)
    t += [
        {"clip": C98, "start": 34.36, "end": 37.82, "snap": False, "pad_after": 0.2,
         "text": "Never again. Never go shortcuts.", "music": "stop",
         "sfx": [{"id": "scratch", "at": 0.0}], "overlay": [cta(2.0, 1.6)]},
    ]
    return t


def wine() -> list:
    t = [
        {"clip": C99, "start": 88.36, "end": 91.04, "text": "I don't drink at all. Zero. Zero.",
         "music": "lofi_night", "overlay": [hook("THE WINE\nRULE", 1.8)]},
    ]
    t += line("I need water.", "i", "need", "water", gap=0.4, sfx=[{"id": "scratch", "at": 0.0}])
    t += line("I have wine.", "i", "have", "wine", gap=0.4)
    t += line("Wine is water.", ("wine", ("43250", 22.44)), "is", ("water", ("42700", 85.18)), gap=0.4, sfx=[{"id": "pop", "at": 0.0}])
    t += [
        {"clip": C99, "start": 81.0, "end": 81.58, "text": "Very good.", "pad_after": 1.0,
         "overlay": [cta(0.4, 1.4)]},
    ]
    return t


def main() -> None:
    for name, fn in (("secret", secret), ("dog", dog), ("review", review), ("wine", wine)):
        cut = fn()
        out = FOLDER / f"plan_wordmix_{name}.json"
        out.write_text(json.dumps(base(f"Thailand_Shortcut_42_Wordmix_{name}", cut), ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(out, len(cut), "items")


if __name__ == "__main__":
    main()
