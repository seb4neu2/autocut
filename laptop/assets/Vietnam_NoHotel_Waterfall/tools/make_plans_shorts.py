#!/usr/bin/env python3
"""Writes the plans for three vertical Shorts of the Vietnam waterfall video (picked by the user, 2026-10-23):

  plan_short_camera.json      "They brought my camera back"   (the camera scene, 99 -> 100 subscribers)
  plan_short_zerostars.json   "Hotel rating: zero stars"      (no hotel -> dawn by the river -> the "for real" bird)
  plan_short_thrownout.json   "Thrown out of a waterfall"     (not allowed after 18:00, "Bullsh*t", find a bed)

Second round (user, 2026-10-23): camera v2 with a happy after story (fire, eating together, thank you), and
three new full 9:16 Shorts (no blur bars) with new narrator lines:
  plan_short_waterfall.json   "It was supposed to be dry"     (doubt -> reveal -> swim), replaces "thrown out"
  plan_short_pee.json         "Did you know?"                 (Phelps, the Canadian pool study, Dad's rule fact-checked)
  plan_short_koel.json        "The for real bird"             (picture card ai_koel_01.png, crows raise its chick)

Every item is copied from plan_v3.json (the cuts the user kept in the final v3 draft), so cuts, narration
lines (same tagged text, cached), sounds and cards cost nothing. Wide shots (the boys, the phone at the
frame edge) use "fit": the whole picture across the width with CapCut's background blur behind it.
The koel in the morning Short is the user's own recording (DJI_0018 at 416 s), no licence needed.
Build each with:  python pipeline/build_plan.py <plan> C:\\Users\\niu\\Desktop\\Sort\\2026-04-12_DrayNur
"""

import copy
import json
from pathlib import Path

FOLDER = Path(r"C:\Users\niu\Desktop\Sort\2026-04-12_DrayNur")
FULL = json.loads((FOLDER / "plan_v3.json").read_text(encoding="utf-8"))
T = FULL["timeline"]
ASSETS = Path(__file__).resolve().parents[1]


def take(i: int, **changes) -> dict:
    """Item i of plan_v3, without its chapter label (Shorts have no chapters)."""
    item = copy.deepcopy(T[i])
    for k in ("section", "section_label"):
        item.pop(k, None)
    item.update(changes)
    return item


def label(text: str, at: float = 0.0, duration: float = 2.6, **kw) -> dict:
    return {"gfx": {"type": "label", "text": text, **kw}, "at": at, "duration": duration}


def cta(at: float, duration: float) -> dict:
    return label("FULL\nVIDEO", at, duration)


def base(name: str, music: tuple, timeline: list) -> dict:
    sfx = copy.deepcopy(FULL["sfx"])
    sfx["koel_own"] = {"file": "sfx_asian-koel-own-recording-DJI_0018.mp3", "volume": 0.36}  # 6.5 dB quieter than XC779913
    mus = {k: {**FULL["music"][k]} for k in music}
    for m in mus.values():  # a Short has no quiet stretches: keep the music a little lower under the open parts
        m["open"] = min(m.get("open", 0.45), 0.4)
        if "file" not in m:  # pin the track the main video already has: a prompt would be generated (and billed) per length
            slug = m["name"].replace(" ", "-")
            m["file"] = max(ASSETS.glob(f"music_{slug}_*s_*.mp3"), key=lambda p: int(p.stem.split("_")[-2][:-1])).name
            del m["prompt"]
    return {"name": name, "assets": "Vietnam_NoHotel_Waterfall", "canvas": "vertical", "fps": 60,
            "narrator_voice": FULL["narrator_voice"], "narration_lufs": FULL["narration_lufs"],
            "emphasis": FULL["emphasis"], "media": FULL["media"], "sfx": sfx, "music": mus, "timeline": timeline}


def narr(text: str, tagged: str, offset: float = 0.2) -> dict:
    return {"text": text, "tagged": tagged, "offset": offset}


# v2 (user, 2026-10-23): after the camera story a happy after story, the big fire, eating together, thank you
CAMERA = [
    take(0, music="lofi_warm", fit=True, y=0.0,           # hook: you hold the camera up next to the boys,
         overlay=[label("I LOST MY\nCAMERA", 0.0, 3.0)]),   # "So the guys found my camera. Thank you very much."
    take(57, fit=True),                     # narrator over the boys: they looked for him the whole evening
    take(55),                               # "In Europa there is no password... they just returned it"
    take(58, fit=True),                     # "this is my YouTube, 99 followers" (the phone is at the frame edge)
    take(59, fit=True, end=9.5, rotate=-90, zoom=round(16 / 9, 4), x=0.0),  # the boys subscribe: +1 SUBSCRIBER, 99 -> 100
    # (user, 2026-10-23: the phone is filmed sideways, so the clip is turned 90 degrees anticlockwise; a turned
    # 16:9 picture is 9:16, the zoom 16/9 makes it fill the screen exactly)
    {"broll": "PXL_20260412_135658744.mp4", "start": 2.0, "end": 8.4, "volume": 0.5, "x": 0.44, "music": "lofi_fire",
     "narration": narr("The camera was back. So nobody went home... and the night turned into a party.",
                       "[warm] The camera was back. [short pause] So nobody went home... and the night turned into a party.")},
    take(68),                               # "Big fire. Very big fire."
    {"broll": "PXL_20260412_130621596.mp4", "start": 57.3, "end": 60.8, "volume": 0.35, "x": -0.3},  # the boys eat the cake
    {"clip": "PXL_20260412_132838375.mp4", "start": 341.6, "end": 343.15, "text": "Mm. It's very delicious."},
    take(60, overlay=[cta(2.4, 2.9)]),      # "Thank you very much for the camera, guys. I will not forget that."
]

CAMERA[4]["overlay"][0]["duration"] = 2.2  # the subscribe clip is shorter now: the sticker ends with it
for sc in CAMERA[4].get("side_captions", []):  # turned clip: the phone fills the top half, keep the quotes off its screen
    sc["y"] = 0.05

koel = take(79)
koel["overlay"] = [label("ASIAN\nKOEL", 4.0, 7.5)]  # the landscape info card does not fit a vertical screen
for s in koel["sfx"]:
    if s["id"] == "koel":
        s.update(id="koel_own", volume=round(s["volume"] / 0.17 * 0.36, 3))
ZEROSTARS = [
    take(3, music="lofi_morning", fit=True, overlay=[label("NO HOTEL\nNO PLAN", 0.0, 3.2)]),  # "I'm tired and I have no hotel or hostel."
    take(74),                               # dawn drone, narrator: "Hotel rating: zero stars. Stars visible from the bed: all of them."
    take(75),                               # "but the night was so starry"
    take(76),                               # "I slept actually quite good... I had no blanket"
    take(78),                               # "Good morning, Vietnam."
    koel,                                   # "you will never forget it... For real. For real." + koel card
    take(80),
    {"broll": "DJI_20260412223930_0012_D.MP4", "start": 82.0, "end": 85.0, "volume": 0.5,
     "sfx": [{"id": "koel_own", "at": 0.0, "skip": 15.0, "max": 3.0, "volume": 0.36}], "overlay": [cta(0.1, 2.9)]},
]

THROWNOUT = [
    take(13, music="lofi_swim", overlay=[label("THROWN\nOUT", 0.0, 3.0)]),  # "Oh, waterfall. And it's not dry."
    take(31, music="trouble", x=-0.65),             # "not allowed after 18:00"
    # take(32) (entry fee 50,000 VND) left out: Shorts stay under 1 minute (user, 2026-10-23)
    take(33, x=-0.63),                      # "the guy said yes, and another guy just threw me out"
    take(34),                               # "Maybe people die here after night"
    take(35),                               # narrator: "He was guessing. But... people really did drown here."
    take(36),                               # "because of a few stupid people... they have to have rules"
    take(37),                               # "Bullsh*t." (bleeped)
    take(38, overlay=[label("MISSION:\nFIND A BED", 1.2, 2.0)]),  # "Okay, I'm going. I still need to find a place to sleep."
                                            # (the landscape HUD panel is too small on a vertical screen)
    {"broll": "Drone shots\\DJI_20260412174910_0003_D.MP4", "start": 150.0, "end": 153.5, "overlay": [cta(0.1, 3.3)]},
]

# ---- second round (user, 2026-10-23): full 9:16, no blur bars ("fit" not used), new narrator lines ----
# Facts checked on the web on 2026-10-23 (sources listed in the session report and in youtube_upload.txt).
DRONE3 = "Drone shots\\DJI_20260412174910_0003_D.MP4"

WATERFALL = [  # replaces "thrown out": the reveal of a waterfall that was supposed to be dry
    take(12, music="trouble", overlay=[label("IS IT\nDRY?", 0.0, 3.0)]),   # "The waterfall definitely is dry. I think so."
    {"broll": "DJI_20260412103747_0002_D.MP4", "start": 43.0, "end": 49.0, "volume": 0.4,   # the boardwalk down
     "narration": narr("April. The end of the dry season. Expectations were low.",
                       "[dry] April. The end of the dry season. [short pause] Expectations were low.")},
    take(13, music="reveal", sfx=[{"id": "impact", "at": 0.0}]),            # "Wow, a waterfall, and it's not dry."
    {"broll": "DJI_20260412103747_0002_D.MP4", "start": 20.0, "end": 29.0, "volume": 0.4, "pan": [1.2, -0.7],
     "overlay": [label("ĐRAY NUR", 0.8, 3.5, accent_line=0)]},
    {"broll": DRONE3, "start": 4.0, "end": 15.0, "pan": [1.6, 0.3],
     "narration": narr("Đray Nur. About thirty metres high... and two hundred and fifty metres wide. Dry, apparently.",
                       "[impressed] Dray Nur. About thirty metres high... and two hundred and fifty metres wide. "
                       "[short pause] [dry] Dry, apparently.", 0.5)},
    take(17, music="lofi_swim"),            # "But I want to swim there."
    take(18),                               # "Well, I don't know if swimming is allowed."
    take(19),                               # "Okay, let's go swimming."
    take(22, overlay=[cta(4.6, 3.0)]),      # "The water is nice. Quite cold..."
]

PEE = [  # a "did you know" hook, Dad's rule, and the narrator checking it
    {"broll": DRONE3, "start": 470.0, "end": 475.5, "music": "lofi_swim", "overlay": [label("DID YOU\nKNOW?", 0.0, 3.0)],
     "narration": narr("Did you know? Michael Phelps once said: everybody pees in the pool.",
                       "[curious] Did you know? Michael Phelps once said: everybody pees in the pool.", 0.1)},
    {"broll": DRONE3, "start": 476.0, "end": 483.3, "overlay": [label("75\nLITRES", 2.0, 3.0)],
     "narration": narr("Scientists in Canada checked. One big public pool held seventy-five litres of it.",
                       "[dry] Scientists in Canada checked. [short pause] One big public pool held seventy-five litres of it.")},
    take(23, sfx=[]),                       # "Oh, I need to pee. And my father told me I should never pee into the water."
    take(24, overlay=[label("DAD'S\nRULE #1", 0.3, 3.0)]),   # "Yeah, let's listen to my father. Possibly he is right."
    {"freeze": "DJI_20260412104554_0005_D.MP4", "at": 258.0, "sfx": [{"id": "scratch", "at": 0.0}],
     "overlay": [label("MYTH", 3.2, 3.0, accent_line=0)],
     "narration": narr("Dad's theory: germs swim up while you pee. Science found no proof of that. "
                       "The famous fish from the Amazon? Probably a myth too.",
                       "[dry] Dad's theory: germs swim up while you pee. [short pause] Science found no proof of that. "
                       "[wry] The famous fish from the Amazon? Probably a myth too.")},
    {"broll": "DJI_20260412104554_0005_D.MP4", "start": 240.0, "end": 247.2, "volume": 0.3,
     "narration": narr("In a pool, pee and chlorine make the stuff that stings your eyes. This is a river.",
                       "[thoughtful] In a pool, pee and chlorine make the stuff that stings your eyes. [short pause] This is a river.")},
    take(25, end=272.62, sfx=[{"id": "crickets", "at": "end"}]),   # "But I have to go somewhere now."
    {"broll": "DJI_20260412103747_0002_D.MP4", "start": 20.0, "end": 24.5, "volume": 0.4, "pan": [0.9, 0.2],
     "overlay": [cta(1.6, 2.9)],
     "narration": narr("He went somewhere. We did not follow him.",
                       "[deadpan] He went somewhere. [short pause] We did not follow him.")},
]


def koel_card() -> str:
    """The koel picture as a card: square crop on the bird, brand-yellow rim, round corners (no text in it)."""
    from PIL import Image, ImageDraw
    out = ASSETS / "gfx_koel-card_ai_koel_01.png"
    if not out.exists():
        pic = Image.open(ASSETS / "ai_koel_01.png").convert("RGB").crop((250, 170, 1010, 930)).resize((900, 900), Image.LANCZOS)
        rim, r = 18, 70
        card = Image.new("RGBA", (900 + 2 * rim, 900 + 2 * rim), (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), r + rim, fill=(244, 199, 15, 255))
        mask = Image.new("L", pic.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 899, 899), r, fill=255)
        card.paste(pic, (rim, rim), mask)
        card.save(out)
    return out.name


koel_said = take(79, sfx=[{"id": "koel_own", "at": 1.0, "max": 11.0, "skip": 0.0, "volume": 0.36}])
koel_said.pop("overlay", None)
KOEL = [  # the "for real" bird, with a picture card and the koel's real habits
    {"broll": "DJI_20260412223930_0012_D.MP4", "start": 69.0, "end": 76.0, "volume": 0.5, "music": "lofi_morning",
     "sfx": [{"id": "koel_own", "at": 0.0, "max": 6.5, "skip": 3.0, "volume": 0.36}],
     "overlay": [label("5:30\nAM", 0.0, 3.0)],
     "narration": narr("Half past five. Sebastian's alarm clock goes off. He doesn't own an alarm clock.",
                       "[dry] Half past five. Sebastian's alarm clock goes off. [short pause] He doesn't own an alarm clock.", 0.1)},
    take(78),                               # "Good morning, Vietnam."
    koel_said,                              # "When you hear it one time, you will never forget it... For real. For real."
    {"broll": "DJI_20260412223930_0012_D.MP4", "start": 76.2, "end": 85.8, "volume": 0.4,
     "overlay": [label("ASIAN\nKOEL", 0.2, 8.3),
                 {"video": koel_card(), "scale": 0.6, "y": 0.08, "at": 0.4, "duration": 8.1}],
     "narration": narr("Meet the Asian koel, a cuckoo. It builds no nest. It lays its egg in a crow's nest... "
                       "and lets the crows raise the chick.",
                       "[curious] Meet the Asian koel, a cuckoo. [short pause] It builds no nest. "
                       "[wry] It lays its egg in a crow's nest... and lets the crows raise the chick.")},
    {"broll": "Drone shots\\DJI_20260413063941_0005_D.MP4", "start": 44.0, "end": 51.4,
     "sfx": [{"id": "koel_own", "at": 2.5, "max": 3.5, "skip": 12.0, "volume": 0.36}], "overlay": [cta(4.4, 3.0)],
     "narration": narr("No nest, no hotel, up at dawn. Sebastian may have found his spirit animal.",
                       "[amused] No nest, no hotel, up at dawn. [short pause] Sebastian may have found his spirit animal.")},
]

if __name__ == "__main__":
    for key, music, tl in (("camera", ("lofi_warm", "lofi_fire"), CAMERA), ("zerostars", ("lofi_morning",), ZEROSTARS),
                           ("thrownout", ("lofi_swim", "trouble"), THROWNOUT),
                           ("waterfall", ("trouble", "reveal", "lofi_swim"), WATERFALL),
                           ("pee", ("lofi_swim",), PEE), ("koel", ("lofi_morning",), KOEL)):
        out = FOLDER / f"plan_short_{key}.json"
        out.write_text(json.dumps(base(f"Vietnam_NoHotel_Waterfall_Short_{key}", music, tl), ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(out, len(tl), "items")
