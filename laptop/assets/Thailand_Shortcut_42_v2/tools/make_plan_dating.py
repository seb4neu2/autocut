#!/usr/bin/env python3
"""Writes plan_wordmix_dating.json: "The Dating Profile". The narrator reads the user's dating
profile, very seriously, over colour freeze frames; the user answers in a word mashup.
Build:  python pipeline/build_plan.py D:\\Backup\\VlogX\\plan_wordmix_dating.json D:\\Backup\\VlogX
"""

from wordmix_common import answer, ask, label, write_plan


def plan() -> list:
    t = [ask("Meet Sebastian. Forty two. Adventurer. Looking for love.",
             "[warm, smooth, a little too sincere] Meet Sebastian. Forty two. Adventurer. [short pause] "
             "Looking for love.", "42750", 3.0, bw=False, music="lofi_day",
             overlay=[label("DATING\nPROFILE", 0.0, 2.4)])]
    t += answer("Hello. I'm Sebastian. Forty-two.", ("hello", "42700", 10.82), ("i'm", "42700", 154.36),
                ("sebastian", "43100", 159.92), ("forty-two", "42700", 11.21), word_gap=0.12, gap=0.3)
    t += [ask("Tell us about yourself.", "Tell us about yourself.", "42700", 40.0, bw=False)]
    t += answer("I have one big bag.", ("i", "42700", 37.58), ("have", "42700", 144.08), ("one", "42700", 73.08),
                ("big", "43150", 52.15), ("bag", "42700", 39.94), gap=0.2)
    t += answer("Hammock.", ("hammock", "42700", 285.51), gap=0.25)
    t += answer("No water.", ("no", "42700", 28.10), ("water", "42700", 152.34), gap=0.3)
    t += [ask("Hobbies?", "[curious] Hobbies?", "42850", 14.0, bw=False)]
    t += answer("Trash. Dogs. Wine.", ("trash", "42750", 40.14), ("dogs", "42900", 33.60),
                ("wine", "43250", 22.38), word_gap=0.3, gap=0.3)
    t += [ask("Do you drink?", "Do you drink?", "43100", 64.0, bw=False)]
    t += [{"clip": "43100_DJI_20240318_0099.MP4", "start": 88.36, "end": 91.04, "text": "I don't drink at all. Zero. Zero.",
           "pad_after": 0.15}]
    t += [ask("Your ideal first date?", "[intrigued] Your ideal first date?", "DJI_0300.MP4", 45.0, bw=False)]
    t += answer("Dogs.", ("dogs", "42900", 33.60), gap=0.25)
    t += answer("One lake.", ("one", "42700", 39.35), ("lake", "42700", 31.73), gap=0.25)
    t += answer("No boat.", ("no", "43050", 149.20), ("boat", "42700", 125.99), gap=0.3)
    t += [ask("Where do you sleep?", "Where do you sleep?", "43150", 168.0, bw=False)]
    t += answer("In the trees.", ("in", "42700", 199.68), ("the", "42700", 95.48), ("trees", "42700", 200.33),
                gap=0.3)
    t += [ask("Ladies... he is available.", "[dry] Ladies... [short pause] he is available.",
              "43050", 234.0, bw=False, sfx=[{"id": "crickets", "at": 1.2}])]
    t += answer("Bye.", ("bye", "42750", 101.74), gap=1.6)
    t[-1]["overlay"] = [label("WATCH\nTHE FULL\nVIDEO", 0.2, 1.6, y=0.27)]
    return t


if __name__ == "__main__":
    write_plan("dating", plan(), ("lofi_day",))
