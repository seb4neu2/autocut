#!/usr/bin/env python3
"""Writes plan_wordmix_interrogation_v2.json: a vertical Short in which the narrator questions the
user like a police detective about the shortcut, and the user answers in a word mashup.

Mashup rule (user, 2026-10-14): every word is its own clip, picture and sound from the moment the
user says it, single words only. Each take is cut precisely by wordmix_precise.
 The narrator's questions play over black-and-white
freeze frames of the trip ("evidence"), which stretch to the length of each line.
Build:  python pipeline/build_plan.py D:\\Backup\\VlogX\\plan_wordmix_interrogation_v2.json D:\\Backup\\VlogX
"""

from wordmix_common import answer, ask, label, write_plan

C91, C92, C94, C96, C98 = "42700", "42750", "42850", "42950", "43050"
DRONE = "DJI_0300.MP4"


def plan() -> list:
    t = [ask("Case number forty two. The shortcut.",
             "[low, steady voice, like a tired detective] Case number forty two. [short pause] The shortcut.",
             DRONE, 60.0, music="trouble", sfx=[{"id": "impact", "at": 0.0}],
             overlay=[{"gfx": {"type": "label", "text": "THE\nSHORTCUT\nCASE", "size": 250, "y": 0.22},
                       "at": 0.0, "duration": 2.4}]),
         ask("Sebastian. You had a boat. Two thousand baht. Why did you walk?",
             "Sebastian. You had a boat. Two thousand baht. [short pause] Why did you walk?", C91, 96.0)]
    t += answer("Because... I'm... stupid.", ("because", "42700", 153.94), ("i'm", "42700", 13.40),
                ("stupid", "42700", 166.67), word_gap=0.25, gap=0.3)
    t += [ask("Who planned the route?", "[dry] Who planned the route?", C94, 9.0)]
    t += answer("The dogs.", ("the", "42700", 87.38), ("dogs", "42900", 33.60), gap=0.3)
    t += [ask("Did the dogs know the way?", "[skeptical] Did the dogs know the way?", C94, 14.0)]
    t += answer("No idea.", ("no", "42700", 28.10), ("idea", "42700", 229.44), gap=0.3)
    t += [ask("How far was it?", "How far was it?", DRONE, 45.0)]
    t += answer("Very. Very. Far.", ("very", "42750", 65.09), ("very", "42750", 65.43), ("far", "42750", 67.88),
                word_gap=0.2, gap=0.3)
    t += [ask("How much water did you bring?", "How much water did you bring?", C92, 3.0)]
    t += answer("Half... liter.", ("half", "42750", 4.76), ("liter", "42750", 6.42), word_gap=0.3, gap=0.3)
    t += [ask("And food?", "[deadpan] And food?", C91, 211.0)]
    t += answer("Small ananas.", ("small", "42700", 212.45), ("ananas", "42700", 211.02),
                gap=0.15)
    t += answer("Not edible.", ("not", "42750", 8.24), ("edible", "42700", 216.19), gap=0.3)
    t += [ask("Would you do it again?", "[slowly] Would you do it again?", C96, 116.0)]
    t += answer("Yes.", ("yes", "43050", 204.75), gap=0.5)
    t += [{"clip": "43050_DJI_20240318_0098.MP4", "start": 34.36, "end": 35.24, "snap": False, "pad_after": 0.4, "text": "Never again.",
           "sfx": [{"id": "sting", "at": 0.0}]}]
    t += [ask("Any last words?", "[sighs] Any last words?", C98, 234.0)]
    t += answer("I love the dogs.", ("i", "42700", 37.58), ("love", "43150", 39.16), ("the", "42700", 87.38),
                ("dogs", "42900", 33.60), gap=0.25, music="lofi_day")
    t += answer("The dogs love me.", ("the", "42700", 95.48), ("dogs", "42900", 33.60),
                ("love", "43150", 39.16), ("me", "42850", 257.44), gap=0.4)
    t += [ask("Case closed.", "[dry] Case closed.", DRONE, 66.0, tail=1.6,
              overlay=[{"gfx": {"type": "label", "text": "WATCH\nTHE FULL\nVIDEO", "size": 250, "y": 0.27},
                        "at": 0.9, "duration": 1.6}])]
    return t


if __name__ == "__main__":
    # v2: same Short, every word cut precisely (wordmix_precise); v1 stays as it is
    write_plan("interrogation_v2", plan(), ("trouble", "lofi_day"))
