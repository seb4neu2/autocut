"""Writes plan.json for the drowned-drone video (idea 1: 'I drowned my drone. Twice.')."""
import json
from pathlib import Path

FOLDER = Path(r"C:\Users\niu\Desktop\How did i destroy my first done")

D = {int(f.name.split("_")[2]): f.name for f in FOLDER.glob("DJI_*_D.MP4")}
FLIGHT, CONFESS, DRYER, TRUTH, WASH, TEST, TEST_AIR, LATER = D[8], D[54], D[55], D[57], D[58], D[60], D[11], D[13]


def clip(src, start, end, text, **kw):
    return {"clip": src, "start": start, "end": end, "text": text, **kw}


def broll(src, start, end, **kw):
    return {"broll": src, "start": start, "end": end, **kw}


def freeze(src, at, text, **kw):
    return {"freeze": src, "at": at, "narration": {"text": text}, **kw}


def sfx(id_, at=0.0):
    return {"id": id_, "at": at}


def gfx(spec, at=0.2, duration=None, **kw):
    o = {"gfx": spec, "at": at, **kw}
    if duration:
        o["duration"] = duration
    return o


timeline = [
    # ---- cold open ---------------------------------------------------------------------
    clip(TRUTH, 132.50, 138.10, "No, don't go in the water again. That's ridiculous.", section="Cold open",
         section_label=False),
    clip(TRUTH, 346.64, 349.18, "I just dried it. It was dry and then I..."),
    freeze(TRUTH, 348.0, "This is Sebastian. That was his drone, flying into a pond. For the second time that day. "
                         "Let's rewind.", sfx=[sfx("scratch")]),
    broll(FLIGHT, 22.0, 28.0, sfx=[sfx("whoosh"), sfx("impact", 0.3)], transition="闪白", transition_duration=0.4,
          overlay=[gfx({"type": "title", "title": "I Drowned My Drone. Twice.", "subtitle": "A homestay in Vietnam",
                        "kicker": "and one bottle of ethanol"}, at=0.3, duration=5.4)]),

    # ---- the flight --------------------------------------------------------------------
    broll(FLIGHT, 93.0, 106.0, section="The Flight", music="reveal", transition="叠化", transition_duration=0.6,
          narration={"text": "Early that morning, he sent the drone up to film a little video for his homestay.",
                     "offset": 1.5}),
    broll(FLIGHT, 268.0, 278.0),
    broll(FLIGHT, 549.0, 562.5, music="lofi_day",
          narration={"text": "That flight went perfectly. It even came home through the window. "
                             "The next one ended in the pond.", "offset": 0.8}),

    # ---- the confession ----------------------------------------------------------------
    clip(CONFESS, 28.73, 30.89, "So good morning.", section="The Confession"),
    clip(CONFESS, 31.87, 39.87, "I was flying today with my drone and I wanted to record a video for the home stay."),
    clip(CONFESS, 41.27, 46.05, "And, uh, yeah, I fell into the water.", sfx=[sfx("sting", "end")]),
    clip(CONFESS, 49.84, 57.70, "Oh, I actually, actually fell here. It fell, uh, the drone fell in this place there."),
    clip(CONFESS, 62.68, 64.88, "I went into the water."),
    clip(CONFESS, 65.90, 76.80, "Luckily, I had my, uh, swimming goggles because otherwise it would be difficult to "
                                "find the drone without opening my eyes."),
    clip(CONFESS, 121.68, 129.86, "It was quite interesting because the drone was still working below the water. "
                                  "I saw the lights."),

    # ---- the rescue --------------------------------------------------------------------
    clip(CONFESS, 81.26, 91.50, "I put the drone into ethanol. I had like seventy percent ethanol, and then I also had "
                                "a bottle of ninety percent ethanol.", section="The Rescue", sfx=[sfx("pop", 3.8)],
         overlay=[gfx({"type": "hud", "title": "DRONE RESCUE KIT", "rows": [["ETHANOL 70%", "1"], ["ETHANOL 90%", "1"],
                                                                             ["HAIR DRYER", "1"]],
                       "highlight": 1}, at=3.8, duration=6.0)]),
    broll(DRYER, 0.0, 15.0, speed=1.5, volume=0.35,
          narration={"text": "Step two: a plastic bag and a hair dryer. Then, about six hours of waiting.",
                     "offset": 0.4}),
    clip(CONFESS, 174.91, 182.29, "I will tell you later if this worked or not. I hope so. Fingers crossed."),

    # ---- the moment of truth -----------------------------------------------------------
    clip(TRUTH, 9.07, 17.33, "the moment of truth. Will the drone work after swimming today?",
         section="The Moment of Truth", music="trouble"),
    clip(TRUTH, 20.69, 23.31, "I don't hear any water. Okay, that's good."),
    clip(TRUTH, 62.15, 68.28, "The display has some problems but it's still working."),
    clip(TRUTH, 91.36, 92.80, "Okay, let's do a selfie shot."),
    clip(TRUTH, 106.20, 113.82, "Okay, so this was, uh, not good. But, uh, he was flying."),
    clip(TRUTH, 113.94, 117.88, "Okay, let's, let's make follow. Maybe follow will be better."),
    broll(TRUTH, 125.5, 132.3, volume=1.0, music_level=0.05),
    clip(TRUTH, 132.50, 141.98, "No, don't go in the water again. That's ridiculous. This is ridiculous. Holy shit.",
         music="stop", zoom=1.0, sfx=[sfx("scratch", 0.1)]),
    clip(TRUTH, 144.62, 148.44, "What the fuck? I need to swim again.", zoom=1.0),
    clip(TRUTH, 153.01, 154.79, "That was very sad.", zoom=1.0, sfx=[sfx("crickets", "end")]),
    broll(TRUTH, 236.0, 302.0, speed=6.0, music="lofi_night", sfx=[sfx("pop", 0.6)],
          narration={"text": "So he went swimming. Again.", "offset": 0.6},
          overlay=[gfx({"type": "sticker", "text": "SWIM #2", "sub": "same pond, same drone"}, at=0.6, duration=5.0,
                       **{"in": "向下甩入"})]),

    # ---- round two ---------------------------------------------------------------------
    clip(TRUTH, 346.64, 352.30, "I just dried it. It was dry and then I... Yeah, it was my mistake. "
                                "Of course it was my mistake.", section="Round Two"),
    clip(TRUTH, 363.53, 369.73, "I will have to buy alcohol now and dry it again but first I shower."),
    clip(WASH, 28.41, 34.73, "This is 70% alcohol. Um, this is not ideal."),
    broll(WASH, 50.0, 98.0, speed=5.0, volume=0.3),
    clip(WASH, 157.88, 171.84, "Oh, I hope it will be good. But he plunged twice into the water. I think, I think I, "
                               "I told him too many times leave me alone, and now he just want to drown himself."),
    clip(WASH, 174.02, 179.16, "I'm sorry. I, I, I, I ... Don't leave me alone. Stay with me, please."),

    # ---- the verdict -------------------------------------------------------------------
    broll(TEST, 38.0, 56.0, speed=1.5, volume=0.6, section="The Verdict",
          narration={"text": "Two hours later. Attempt number three. Indoors, this time.", "offset": 0.8}),
    broll(TEST_AIR, 6.0, 10.0),
    clip(TEST, 146.27, 157.47, "So the drone works. I don't know, after two times being into water? I need to read in "
                               "the internet about it if this drone is waterproof.", sfx=[sfx("levelup", 0.2)],
         overlay=[gfx({"type": "sticker", "text": "IT WORKS", "sub": "after two swims"}, at=0.2, duration=4.0,
                      **{"in": "向下甩入"})]),
    clip(TEST, 160.02, 163.30, "Incredible. Nice"),

    # ---- outro -------------------------------------------------------------------------
    broll(LATER, 33.0, 38.5, section="Outro", transition="叠化", transition_duration=0.6,
          narration={"text": "Two days later, it was back in the air.", "offset": 0.5}),
    broll(FLIGHT, 512.0, 534.0, sfx=[sfx("levelup", 0.6)],
          narration={"text": "Final score. Plunges: two. Ethanol baths: two. Drones destroyed: zero. For now.",
                     "offset": 0.6},
          overlay=[gfx({"type": "hud", "title": "FLIGHT REPORT", "rows": [["PLUNGES", "2"], ["ETHANOL BATHS", "2"],
                                                                          ["DRONES DESTROYED", "0"],
                                                                          ["STATUS", "STILL FLYING"]],
                        "highlight": 3}, at=0.6, duration=10.5),
                   gfx({"type": "end", "title": "Don't go in the water again",
                        "lines": ["Thanks for watching", "See you in the next one"]},
                       at=11.5, duration=10.5, **{"in": "渐显"})]),
]

sfx_lib = {
    "scratch": ("vinyl record scratch stop, comedic freeze frame", 1.2, 0.7),
    "whoosh": ("fast cinematic whoosh swoosh transition", 1.0, 0.6),
    "impact": ("deep cinematic trailer boom impact hit with long reverb tail", 3.0, 0.8),
    "crickets": ("awkward silence, crickets chirping, comedic", 2.5, 0.6),
    "levelup": ("retro 8-bit video game level up power-up chime", 1.5, 0.5),
    "pop": ("soft user interface pop blip notification", 0.5, 0.5),
    "sting": ("comedic dramatic orchestral sting dun dun dunnn", 2.2, 0.6),
}

plan = {
    "name": "Drone_Drowned_Twice",
    "canvas": "landscape",
    "fps": 60,
    "narrator_voice": "JBFqnCBsd6RMkjVDRZzb",
    "emphasis": ["drone", "water", "ethanol", "goggles", "truth", "swimming", "swim", "ridiculous", "mistake",
                 "alcohol", "drown", "twice", "works", "waterproof", "incredible", "sad", "follow", "lights", "dried"],
    "sfx": {k: {"prompt": p, "duration": d, "volume": v, "name": p} for k, (p, d, v) in sfx_lib.items()},
    # all four tracks are reused from the earlier videos (pinned files, no new music generated)
    "music": {
        "reveal": {"file": "music_epic-cinematic-reveal-strings-choir-drums_25s_3dad2bb3fc38.mp3", "dialog": 0.3,
                   "open": 0.7, "fade_in": 0.8},
        "lofi_day": {"file": "music_lofi-hiphop-deep-bass-chill-day_140s_8ac9478c2d22.mp3", "dialog": 0.13,
                     "open": 0.45, "fade_in": 0.6},
        "trouble": {"file": "music_comedic-suspense-pizzicato-marimba-tension_100s_323f53b710b6.mp3", "dialog": 0.09,
                    "open": 0.45},
        "lofi_night": {"file": "music_lofi-hiphop-deep-bass-late-night_165s_3c251802dd23.mp3", "dialog": 0.12,
                       "open": 0.42, "fade_in": 1.0},
    },
    "timeline": timeline,
}

out = FOLDER / "plan.json"
out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
n_clip = sum("clip" in i for i in timeline)
print(f"wrote {out}: {len(timeline)} items, {n_clip} dialogue cuts")
