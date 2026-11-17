"""Writes plan.json for the Dray Nur video (version 1: 'No hotel, no plan')."""
import json
from pathlib import Path

FOLDER = Path(r"C:\Users\niu\Desktop\Sort\2026-04-12_DrayNur")
UP = r"C:\Work\AutoCut\assets\Vietnam_NoHotel_Waterfall\upright"

D = {n: f for n, f in {
    1: "DJI_20260412100500_0001_D.MP4", 2: "DJI_20260412103747_0002_D.MP4", 4: "DJI_20260412104206_0004_D.MP4",
    5: "DJI_20260412104554_0005_D.MP4", 6: "DJI_20260412110617_0006_D.MP4", 9: "DJI_20260412115049_0009_D.MP4",
    10: "DJI_20260412125426_0010_D.MP4", 11: "DJI_20260412125803_0011_D.MP4", 12: "DJI_20260412223930_0012_D.MP4",
    13: "DJI_20260412224238_0013_D.MP4", 15: "DJI_20260412224412_0015_D.MP4", 18: "DJI_20260412231449_0018_D.MP4",
    20: "DJI_20260413001105_0020_D.MP4", 21: "DJI_20260413003058_0021_D.MP4", 23: "DJI_20260413030734_0023_D.MP4",
    24: "DJI_20260413031103_0024_D.MP4"}.items()}


def P(tail: str) -> str:
    return next(f.name for f in FOLDER.glob(f"PXL_*{tail}*.mp4"))


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


CAM, FIRE_SELFIE, RIVER_NIGHT = P("124820870"), P("123539857"), P("123913035")
DINNER, CAKE, PARTY, BONFIRE, SMOKE = P("132838375"), P("130621596"), P("135728480"), P("135658744"), P("135057678")
WALK, MET, HAMMOCK, WAKE, BYE, BREAKFAST = P("103028669"), P("113133449"), P("162245757"), P("222012722"), P("004452035"), P("233443949")

LOFI = ("Lo-fi hip hop beat like a chill study livestream: deep warm sub bass, dusty laid-back boom-bap drums, "
        "{mood}, soft vinyl crackle, instrumental, no vocals")

timeline = [
    # ---- cold open ---------------------------------------------------------------------
    clip(CAM, 18.88, 24.24, "So the guys found my camera. Thank you very much.", section="Cold open",
         section_label=False),
    clip(D[11], 64.90, 75.92, "In Europe, somebody would sell it as a used one and make money on it, but, yeah, "
                              "the people here are different."),
    freeze(CAM, 21.0, "This is Sebastian. A few hours earlier he had a scooter, a waterfall to find... "
                      "and no hotel, no plan, and no idea he was about to lose his camera.", sfx=[sfx("scratch")]),
    clip(D[2], 66.74, 71.22, "I'm tired, and I have no hotel or hostel.", zoom="punch", transition="闪白",
         transition_duration=0.4, sfx=[sfx("whoosh", "end")]),
    broll(D[2], 14.0, 19.5, volume=0.5, sfx=[sfx("impact")], overlay=[gfx(
        {"type": "title", "title": "No Hotel, No Plan", "subtitle": "Central Highlands · Vietnam",
         "kicker": "one night with strangers"}, at=0.15, duration=5.0)]),

    # ---- the ride ----------------------------------------------------------------------
    clip(D[1], 43.69, 49.13, "I just made like thirty minutes of driving, and everything is fine.",
         section="The Ride", music="lofi_day"),
    clip(D[1], 58.28, 64.96, "Like after ten minutes being outside of the city, the temperature changed from"),
    clip(D[1], 67.46, 72.54, "thirty-two degrees to maybe twenty-eight,", sfx=[sfx("pop", 0.3)], overlay=[gfx(
        {"type": "sticker", "text": "32° → 28°", "sub": "ten minutes out of town"}, at=0.3, duration=4.5,
        **{"in": "向下甩入"})]),
    broll(D[1], 99.5, 104.5, volume=0.3),
    clip(D[1], 114.48, 123.08, "I'm going to a waterfall, and let's see how it is there, if it's dry or not. "
                               "But there are mountains here. I feel already colder. I'm so happy."),

    # ---- the waterfall -----------------------------------------------------------------
    clip(WALK, 15.13, 19.55, "The waterfall definitely is dry. I think so. Or I don't know.", section="The Waterfall"),
    clip(WALK, 111.66, 117.50, "Oh, waterfall. And it's not dry. It's definitely not dry."),
    broll(D[2], 20.0, 31.0, volume=0.4, music="reveal", transition="叠化", transition_duration=0.6),
    broll(D[2], 43.0, 51.0, volume=0.4),
    clip(D[2], 6.86, 10.42, "But I want to swim there.", music="lofi_swim"),
    clip(D[2], 105.75, 107.91, "Well, I don't know if swimming is allowed."),
    clip(D[4], 43.07, 44.13, "Okay, let's go swimming."),
    clip(D[4], 66.60, 68.00, "They are recording me."),
    clip(D[4], 73.66, 76.78, "When I'm somewhere, the people record me all the time."),
    broll(D[5], 214.0, 224.0, volume=0.6),
    clip(D[5], 225.04, 232.64, "The water is nice. Quite cold. Not very cold, but very, very, oh, good."),
    clip(D[5], 234.20, 239.40, "Oh, I need to pee. And my father told me I should never pee into the water.",
         sfx=[sfx("sting", "end")]),
    clip(D[5], 256.10, 261.66, "Yeah, let's listen to my father. Possibly he is right."),
    clip(D[5], 270.88, 275.88, "But I have to go somewhere now. Okay.", sfx=[sfx("crickets", "end")]),

    # ---- the fisherman -----------------------------------------------------------------
    clip(D[6], 25.00, 35.64, "Hello, mister. Fish. Fish. Show me. I want to see. How many fish do you have?",
         section="The Fisherman"),
    clip(D[6], 82.14, 87.14, "Do you guys see how muscular this guy is? And he doesn't go to the gym."),
    clip(D[6], 92.35, 95.57, "He has food for free, gym for free,", sfx=[sfx("pop", 0.2)], overlay=[gfx(
        {"type": "hud", "title": "LOCAL FISHERMAN", "rows": [["FOOD", "FREE"], ["GYM", "FREE"], ["EXPERIENCE", "MAX"]],
         "highlight": 1}, at=0.2, duration=5.2)]),
    clip(D[6], 105.79, 107.09, "and a lot of experience.", sfx=[sfx("levelup", 0.2)]),

    # ---- thrown out --------------------------------------------------------------------
    clip(D[6], 163.33, 172.73, "I cooled off. I would like to swim longer, but the guy already said it's not allowed "
                               "after 18:00.", section="Thrown Out", music="trouble"),
    clip(D[6], 174.77, 182.31, "When I paid for the entry, it was like for 50,000 Vietnamese dong.",
         sfx=[sfx("chaching", 3.2)], overlay=[gfx({"type": "sticker", "text": "50,000 VND", "sub": "entry fee"},
                                                  at=3.2, duration=3.6, **{"in": "向下甩入"})]),
    clip(D[6], 185.10, 193.68, "And I asked if I can stay here 'til the sunset. And the guy said, yes. "
                               "And another guy just throwed me out."),
    clip(D[6], 204.13, 210.57, "Maybe people die here after night. They drink alcohol, and then they swim and die."),
    freeze(D[6], 206.0, "He was guessing. But the next morning, a local told him: years ago, when the water ran high, "
                        "people really did drown here.", sfx=[sfx("sting", 0.1)]),
    clip(D[6], 213.41, 221.83, "because of a few stupid people who do unresponsible stuff, they have to have rules."),
    clip(D[6], 250.60, 251.22, "Bullshit.", zoom="punch"),
    clip(D[6], 260.94, 264.18, "Okay, I'm going. I still need to find a place to sleep.", sfx=[sfx("pop", 1.2)],
         overlay=[gfx({"type": "hud", "title": "MISSION: FIND A BED", "rows": [["HOTEL", "NONE"], ["PLAN", "NONE"],
                                                                                ["DAYLIGHT", "FADING"]],
                       "highlight": 2}, at=1.2)]),
    clip(D[6], 382.03, 387.25, "I'm so happy I have a scooter. I can go wherever I want and do whatever I want."),

    # ---- the stranger ------------------------------------------------------------------
    clip(MET, 2.40, 9.24, "So I just met a Vietnamese friend. He just was swimming in the waterfall also.",
         section="The Stranger"),
    clip(MET, 10.60, 20.80, "And he invited me to a restaurant, and he said he will search for a place to camp and "
                            "maybe we will camp together."),
    clip(MET, 36.64, 37.32, "Adventure.", zoom="punch", sfx=[sfx("whoosh", "end")]),
    broll(D[9], 44.0, 58.0, speed=1.4, volume=0.25, music="lofi_night", sfx=[sfx("scooter", 0.2)],
          narration={"text": "So, to recap: it is dark, he has known this man for less than an hour, and he is "
                             "following his tail light to a place he has never seen.", "offset": 0.4}),
    broll(D[9], 134.0, 144.0, speed=1.4, volume=0.25),

    # ---- the camp ----------------------------------------------------------------------
    clip(FIRE_SELFIE, 37.22, 48.33, "So today is exactly why I live for. Fire, water and a friend.",
         section="The Camp"),
    clip(RIVER_NIGHT, 10.59, 15.07, "cooling off in the cold water after a long day."),
    clip(RIVER_NIGHT, 42.11, 47.51, "He made the fire, but I found the wood. That was good because the fire of him "
                                    "was almost dead."),
    clip(RIVER_NIGHT, 55.79, 62.83, "Just for the mosquitoes, I make myself beautiful for them, that they don't "
                                    "understand that I'm here."),
    clip(RIVER_NIGHT, 86.16, 91.10, "If they think I'm the river, they don't attack me."),

    # ---- the camera --------------------------------------------------------------------
    freeze(RIVER_NIGHT, 88.0, "One problem. Somewhere along the way, his camera had gone missing. "
                              "And then three boys from the village walked into the firelight.",
           section="The Camera", sfx=[sfx("sting", 0.1)]),
    clip(CAM, 48.56, 52.32, "What do you want to say for YouTube?"),
    clip(CAM, 58.12, 66.26, "Say hello. Hello. Hello. Hello. Okay. Hello. Hello."),
    clip(D[11], 36.96, 45.76, "So guys, they found my camera and they came here and brought it here."),
    clip(D[11], 46.80, 58.20, "Do you imagine? This in Europa, there is no password in the camera. There is nothing. "
                              "They just came here and returned it"),
    clip(D[11], 58.94, 64.02, "without asking for money, without doing anything."),
    freeze(CAM, 62.0, "According to his friend, the boys had been looking for him the whole evening.", bw=False),
    clip(D[10], 60.24, 66.34, "And this is my YouTube. I'm just beginning, but I have 99 followers."),
    clip(D[11], 7.00, 15.32, "A new subscriber. Thank you very much. Now the whole village will be informed. New fan. "
                             "New fan, yes.", sfx=[sfx("levelup", 0.3)],
         overlay=[gfx({"type": "sticker", "text": "+1 SUBSCRIBER", "sub": "99 → 100"}, at=0.3, duration=4.0,
                      **{"in": "向下甩入"})]),
    clip(D[11], 81.10, 86.40, "Thank you very much for the camera, guys. I will not forget that."),

    # ---- the party ---------------------------------------------------------------------
    clip(CAKE, 31.51, 38.41, "This is a soft cake, very good. You can try. Everybody can take.",
         section="The Party", music="lofi_fire"),
    clip(DINNER, 96.67, 102.25, "Okay, I can open this. We have some rice, we have some meat, we have some chopsticks."),
    clip(DINNER, 208.67, 224.43, "Not good for you. Why? I think not good. This is from today. I bought it today. "
                                 "Today? Yes, today. Not good."),
    clip(DINNER, 237.11, 248.15, "I have bad feeling. You know bad feeling? I have no bad feeling. "
                                 "Bad feeling in Vietnam. Don't, don't think negative, man.",
         sfx=[sfx("sting", "end")]),
    clip(DINNER, 328.45, 342.97, "So, this is my dinner. They said the food is not good, but I bought it today. "
                                 "And it's good. They don't want to eat. I don't know why. Mm, it's very delicious."),
    clip(PARTY, 0.58, 6.66, "So this is our party. The kids have now a game. Who makes the biggest fire?"),
    broll(BONFIRE, 2.0, 13.0, volume=0.7),
    clip(PARTY, 24.47, 27.67, "Big fire. Very big fire."),

    # ---- the cigarettes ----------------------------------------------------------------
    clip(SMOKE, 0.02, 10.30, "So there have been actually like one, two, three kids, uh, smoking, and I throw the "
                             "cigarettes in the fire.", section="The Cigarettes", zoom=1.25, x=0.25),
    clip(SMOKE, 11.42, 13.42, "I don't know if it's a good idea, but, uh...", zoom=1.25, x=0.25),
    clip(SMOKE, 16.82, 23.44, "I asked how old they are. They... I asked them, and they are like 10 or even younger.",
         zoom=1.25, x=0.25),
    freeze(SMOKE, 20.0, "He also broke their vape. Remember that. It comes back at breakfast.",
           sfx=[sfx("sting", 0.1)]),
    clip(HAMMOCK, 0.22, 5.08, "I'm sleeping in my hammock. I'm sleeping in my hammock. Good night."),

    # ---- the morning -------------------------------------------------------------------
    broll(D[12], 69.0, 82.0, volume=0.5, section="The Morning", music="lofi_morning", transition="叠化",
          transition_duration=0.8,
          narration={"text": "Half past five in the morning. Hotel rating: zero stars. "
                             "Stars visible from the bed: all of them.", "offset": 1.2}),
    clip(WAKE, 1.34, 10.56, "Oh, but the night was so starry, star, starry. There were, there, there have been so "
                            "many stars."),
    clip(WAKE, 12.74, 22.86, "I slept actually quite good. It was a little bit cold. I had no blanket, uh, to cover "
                             "myself."),
    clip(WAKE, 32.34, 46.92, "look, I used my, uh, winter jacket and a winter rain jacket. I put my feet inside of my "
                             "rain jacket, and then I dressed another jacket, and that was okay."),
    clip(WAKE, 73.40, 76.78, "Good morning, Vietnam."),
    clip(D[12], 154.56, 167.22, "One time. When you hear it one time, you will never forget it. The bird sounds like "
                                "he is saying in English, For real. For real."),
    clip(D[13], 8.65, 10.25, "For real. For real.", music_level=0.04),

    # ---- the hammer --------------------------------------------------------------------
    clip(D[15], 40.36, 46.88, "My new friend said that I'm Kung Fu Panda. I don't know why. Why I am Kung Fu Panda? "
                              "Why did you say I'm Kung Fu Panda?", section="The Hammer"),
    clip(D[15], 116.82, 119.32, "To w naszej rodzinie tylko dziadziuś robił.",
         captions=[{"from": 116.5, "to": 119.7, "text": "In our family, only grandpa did this."}]),
    clip(D[15], 127.22, 136.14, "Już nawet w bardzo podeszłym wieku, ale codziennie wychodził na swój balkon i robił "
                                "ćwiczenia.",
         captions=[{"from": 127.0, "to": 130.9, "text": "Even when he was very old,"},
                   {"from": 130.9, "to": 134.0, "text": "every day he went out on his balcony"},
                   {"from": 134.0, "to": 136.6, "text": "and did his exercises."}]),
    clip(D[15], 763.47, 768.19, "And it's easy, you know, it's just a hammer. One hammer, and you have all training "
                                "you need.", sfx=[sfx("pop", 0.3)],
         overlay=[gfx({"type": "hud", "title": "RIVERSIDE GYM", "rows": [["EQUIPMENT", "1 HAMMER"],
                                                                          ["MEMBERSHIP", "FREE"], ["VIEW", "RIVER"]],
                       "highlight": 0}, at=0.3)]),
    broll(D[15], 660.0, 674.0, speed=2.0),
    broll(D[15], 786.0, 802.0, speed=2.0),
    clip(D[15], 812.40, 816.34, "High five. Very good."),

    # ---- the breakfast -----------------------------------------------------------------
    clip(BREAKFAST, 0.60, 5.82, "Ready to go eat breakfast? Let's go.", section="The Breakfast", music="lofi_warm"),
    clip(D[20], 12.33, 13.83, "So you have to tell me about the soup."),
    clip(D[20], 23.07, 31.85, "What kind of soup is this? Mister. The name. What is the name of the soup? "
                              "Vietnam soup."),
    broll(D[20], 296.0, 304.0, narration={"text": "For the serious part of breakfast, they needed a translator. "
                                                  "They chose an A.I.", "offset": 0.3}),
    clip(D[20], 578.32, 587.42, "Bạn muốn đến hồ lớn mà bạn đã chỉ cho tôi trên bản đồ. Ở đó có rất nhiều thứ để chơi "
                                "như đi thuyền, đạp xe quanh hồ hoặc chỉ đơn giản là ngồi thư giãn và ngắm cảnh.",
         captions=[{"from": 578.0, "to": 581.2, "text": "(the A.I., instead of translating:)"},
                   {"from": 581.2, "to": 587.9, "text": "\"At the lake you can go boating, cycle around it, "
                                                         "or just relax and enjoy the view...\""}]),
    clip(D[20], 666.66, 669.14, "Wrong. OK. Stupid.", zoom="punch", sfx=[sfx("crickets", "end")]),

    # ---- the debt ----------------------------------------------------------------------
    clip(D[20], 444.51, 451.17, "So, um, the kids yesterday, we destroyed their vape. I destroyed their vape.",
         section="The Debt"),
    clip(D[20], 467.07, 472.25, "They haven't been happy about it. And we said that we buy them something. Yes."),
    clip(D[20], 538.26, 547.94, "Đấy là tài sản rất lớn với chúng. Nhưng chúng biết bạn muốn tốt cho chúng. "
                                "Bạn là người tốt. Chúng không ghét bạn. Chỉ buồn thôi. Rất buồn.",
         music_level=0.07,
         captions=[{"from": 538.0, "to": 540.8, "text": "\"That is a very big possession for them.\""},
                   {"from": 540.8, "to": 543.65, "text": "\"But they know you want what's good for them.\""},
                   {"from": 543.7, "to": 544.7, "text": "\"You are a good person.\""},
                   {"from": 544.75, "to": 545.8, "text": "\"They don't hate you.\""},
                   {"from": 545.85, "to": 547.2, "text": "\"They're just sad.\""},
                   {"from": 547.25, "to": 548.4, "text": "\"Very sad.\""}]),
    freeze(D[20], 546.5, "They had promised one of the boys a carton of Milo. But the shop was closed. So his friend "
                         "had another idea: one hundred thousand dong, split fifty-fifty, sent straight to the kids.",
           sfx=[sfx("chaching", 9.0)],
           overlay=[gfx({"type": "sticker", "text": "100,000 VND", "sub": "50 / 50"}, at=9.0, duration=4.0,
                        **{"in": "向下甩入"})]),
    clip(D[21], 101.98, 119.95, "Chú đây, chú ra hiệu tạp hóa nhưng cô ấy chưa mở cửa. Chúng mày gửi cho chú số tài "
                                "khoản. Người bạn nước ngoài của chú đã chuyển tiền cho chú và bây giờ chú chuyển "
                                "cho chúng mày.",
         music_level=0.07,
         captions=[{"from": 101.7, "to": 108.9, "text": "\"It's uncle. I went to the shop, but she hasn't opened yet.\""},
                   {"from": 108.9, "to": 115.0, "text": "\"Send me your account number.\""},
                   {"from": 115.0, "to": 120.4, "text": "\"My foreign friend sent me the money, "
                                                         "and now I'm sending it to you.\""}]),
    clip(D[21], 220.29, 224.11, "Hopefully they will not buy a vape for it.", zoom="punch",
         sfx=[sfx("sting", "end")]),
    clip(BYE, 0.32, 8.56, "And say goodbye. So thank you very much for the best adventure that I had till now. "
                          "Okay. Thank you. Thank you.",
         captions=[{"from": 1.7, "to": 4.3, "text": "Thank you very much for the best adventure"},
                   {"from": 4.3, "to": 7.1, "text": "that I've had till now."}]),

    # ---- outro -------------------------------------------------------------------------
    broll(D[23], 100.0, 118.0, volume=0.2, section="Outro", sfx=[sfx("levelup", 0.6)],
          narration={"text": "Final score. Hotels booked: zero. Cameras lost: one. Cameras returned: one. "
                             "New subscribers: one. And one debt to the village kids... on its way.", "offset": 0.6},
          overlay=[gfx({"type": "hud", "title": "TRIP REPORT", "rows": [["HOTELS BOOKED", "0"], ["CAMERAS LOST", "1"],
                                                                         ["CAMERAS RETURNED", "1"],
                                                                         ["NEW SUBSCRIBERS", "+1"]],
                        "highlight": 2}, at=0.6, duration=16.0)]),
    broll(D[24], 20.0, 35.0, volume=0.2, overlay=[gfx(
        {"type": "end", "title": "For real, for real", "lines": ["Thanks for watching", "See you in the next one"]},
        at=0.0, duration=15.0, **{"in": "渐显"})]),
]

sfx_lib = {
    "scratch": ("vinyl record scratch stop, comedic freeze frame", 1.2, 0.7),
    "whoosh": ("fast cinematic whoosh swoosh transition", 1.0, 0.6),
    "impact": ("deep cinematic trailer boom impact hit with long reverb tail", 3.0, 0.8),
    "chaching": ("cash register cha-ching with coins", 1.2, 0.7),
    "crickets": ("awkward silence, crickets chirping, comedic", 2.5, 0.6),
    "levelup": ("retro 8-bit video game level up power-up chime", 1.5, 0.5),
    "pop": ("soft user interface pop blip notification", 0.5, 0.5),
    "sting": ("comedic dramatic orchestral sting dun dun dunnn", 2.2, 0.6),
    "scooter": ("small motor scooter engine revving and driving away", 2.5, 0.45),
}

plan = {
    "name": "Vietnam_NoHotel_Waterfall",
    "canvas": "landscape",
    "fps": 60,
    "narrator_voice": "JBFqnCBsd6RMkjVDRZzb",
    "emphasis": ["camera", "waterfall", "dry", "fire", "water", "friend", "hammer", "vape", "subscriber", "adventure",
                 "stars", "mosquitoes", "pee", "free", "sad", "beautiful", "delicious", "happy", "cold", "scooter",
                 "europe", "cigarettes", "die", "river", "starry", "panda", "stupid", "wrong"],
    "media": {f: rf"{UP}\{f}" for f in (P("102811861"), MET, CAM, CAKE, D[11], DINNER)},
    "sfx": {k: {"prompt": p, "duration": d, "volume": v, "name": p} for k, (p, d, v) in sfx_lib.items()},
    "music": {
        "lofi_day": {"file": "music_lofi-hiphop-deep-bass-chill-day_140s_8ac9478c2d22.mp3", "dialog": 0.13,
                     "open": 0.45, "fade_in": 0.3},
        "reveal": {"file": "music_epic-cinematic-reveal-strings-choir-drums_25s_3dad2bb3fc38.mp3", "dialog": 0.14,
                   "open": 0.7, "fade_in": 0.8},
        "lofi_swim": {"file": "music_lofi-hiphop-deep-bass-chill-day_140s_8ac9478c2d22.mp3", "skip": 46.0,
                      "dialog": 0.13, "open": 0.45, "fade_in": 0.6},
        "trouble": {"file": "music_comedic-suspense-pizzicato-marimba-tension_100s_323f53b710b6.mp3", "dialog": 0.09,
                    "open": 0.45},
        "lofi_night": {"file": "music_lofi-hiphop-deep-bass-late-night_165s_3c251802dd23.mp3", "dialog": 0.12,
                       "open": 0.42, "fade_in": 1.0},
        "lofi_fire": {"name": "lofi hiphop deep bass campfire night",
                      "prompt": LOFI.format(mood="warm nylon guitar and mellow Rhodes chords, cozy campfire night "
                                                 "mood, playful, 80 bpm"),
                      "dialog": 0.11, "open": 0.4, "fade_in": 1.0},
        "lofi_morning": {"name": "lofi hiphop deep bass sunrise morning",
                         "prompt": LOFI.format(mood="bright airy electric piano and soft flute, fresh hopeful "
                                                    "sunrise mood, 82 bpm"),
                         "dialog": 0.12, "open": 0.45, "fade_in": 1.5},
        "lofi_warm": {"name": "lofi hiphop deep bass warm heartfelt",
                      "prompt": LOFI.format(mood="warm felt piano and gentle jazzy guitar, heartfelt, tender and "
                                                 "a little nostalgic, 76 bpm"),
                      "dialog": 0.11, "open": 0.45, "fade_in": 1.0},
    },
    "timeline": timeline,
}

out = FOLDER / "plan.json"
out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
n_clip = sum("clip" in i for i in timeline)
print(f"wrote {out}: {len(timeline)} items, {n_clip} dialogue cuts")
