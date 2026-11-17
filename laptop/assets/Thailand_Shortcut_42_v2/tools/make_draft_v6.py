#!/usr/bin/env python3
"""Builds the CapCut draft Thailand_Shortcut_42_v6 from the user's hand-edited v5 draft.

v5 was reworked by hand in CapCut (cuts, crops, volumes, music, captions, an own narration
take), far beyond what plan_v5.json describes. So v6 is not rebuilt from a plan: it is the
v5 draft itself with these changes applied:

  1. freeze frame + narration at the start of chapter 06 (everything after it moves later)
  2. a short narration about the water and the shared food over the fishing b-roll
  3. cold-open swear word cut into its own muted clip (the user did the others by hand)
  4. the automatic 1.18 jump-cut zooms removed (punch-ins and the user's own crops stay)
  5. cards in the brand yellow #F4C70F: rim, title and highlights; other card text white
  6. travel map: mask exactly the size of the clip; the old static map card under it removed
  7. caption typo (double space)

The v5 draft is only read. Run again with --replace to rebuild v6 (this discards hand edits in v6).
"""

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent
sys.path.insert(0, str(HERE.parents[2] / "pipeline"))
import assets  # noqa: E402
import graphics  # noqa: E402

DRAFTS = Path(os.environ["LOCALAPPDATA"]) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
SRC, DST = "Thailand_Shortcut_42_v5", "Thailand_Shortcut_42_v6"
FOOTAGE = Path(r"D:\Backup\VlogX")
VOICE = "i6icHCFicH3kzHTat04x"
NARRATION_LUFS = -23.7
US = 1_000_000

FREEZE_CLIP, FREEZE_AT = "43150_DJI_20240318_0100.MP4", 2.5  # first frame of the clip is black
LOCALS = {
    "text": "Thirty minutes after the swim, the owner of the place and his friends came to water the papaya plants. "
            "How did he get here without a boat? From above. Crazy, they said. Nobody does that.",
    "tagged": "Thirty minutes after the swim, the owner of the place and his friends came to water the papaya plants. "
              "[curious] How did he get here without a boat? [deadpan] From above. [amused] Crazy, they said. "
              "Nobody does that.",
}
WATER = {
    "text": "They gave him clean water. He shared the food he had brought.",
    "tagged": "[warm] They gave him clean water. He shared the food he had brought.",
    "over": "43200_DJI_20240318_0101.MP4",  # the fishing b-roll
}
HUDS = [  # the three HUD panels of plan_v5, to redraw their background in the brand colour
    {"type": "hud", "title": "MISSION: REACH THE LAKE", "rows": [["BUDGET", "0 BAHT"], ["WATER", "0.5 L"], ["GUIDES", "0"]], "highlight": 1},
    {"type": "hud", "title": "MISSION: REACH THE LAKE", "rows": [["BUDGET", "0 BAHT"], ["WATER", "0.5 L"], ["GUIDES", "2 DOGS"]], "highlight": 2},
    {"type": "hud", "title": "MISSION COMPLETE", "rows": [["BUDGET SPENT", "0 BAHT"], ["WATER LEFT", "0 L"], ["GUIDES", "2 GOOD DOGS"]], "highlight": 2},
]
BRAND = [0.957, 0.780, 0.059]
RECOLOUR = {(0.47, 1.0, 0.55): BRAND, (0.78, 0.8, 0.78): [1.0, 1.0, 1.0], (1.0, 0.835, 0.29): BRAND}


def new_id() -> str:
    return uuid.uuid4().hex


class Draft:
    def __init__(self, content: dict):
        self.c = content
        self.mat = {}  # id -> (list it lives in, material)
        for lst in content["materials"].values():
            if isinstance(lst, list):
                for m in lst:
                    if isinstance(m, dict) and "id" in m:
                        self.mat[m["id"]] = (lst, m)

    def track(self, name: str) -> dict:
        return next(t for t in self.c["tracks"] if t.get("name") == name)

    def path(self, seg: dict) -> str:
        return (self.mat[seg["material_id"]][1].get("path") or "").replace("\\", "/")

    def clone_material(self, mid: str) -> dict:
        lst, m = self.mat[mid]
        m2 = copy.deepcopy(m)
        old, m2["id"] = m2["id"], new_id()
        for k in ("material_id", "music_id", "local_material_id"):
            if m2.get(k) == old:
                m2[k] = m2["id"]
        lst.append(m2)
        self.mat[m2["id"]] = (lst, m2)
        return m2

    def clone(self, seg: dict) -> dict:
        """Copy of a segment with its own material and its own per-segment helper materials."""
        s = copy.deepcopy(seg)
        s["id"] = new_id()
        s["material_id"] = self.clone_material(seg["material_id"])["id"]
        s["extra_material_refs"] = [self.clone_material(r)["id"] if r in self.mat else r
                                    for r in seg.get("extra_material_refs", [])]
        for kf in s.get("common_keyframes") or []:
            kf["id"] = new_id()
            for k in kf["keyframe_list"]:
                k["id"] = new_id()
        return s

    def insert(self, track: dict, seg: dict) -> None:
        track["segments"].append(seg)
        track["segments"].sort(key=lambda s: s["target_timerange"]["start"])


def set_time(seg: dict, start: int, dur: int, src_start: int | None = None) -> None:
    seg["target_timerange"] = {"start": start, "duration": dur}
    if seg.get("source_timerange") is not None:
        seg["source_timerange"] = {"start": seg["source_timerange"]["start"] if src_start is None else src_start,
                                   "duration": dur}


def set_text(d: Draft, seg: dict, text: str) -> None:
    m = d.mat[seg["material_id"]][1]
    content = json.loads(m["content"])
    content["text"] = text
    content["styles"] = content["styles"][:1]
    content["styles"][0]["range"] = [0, len(text)]
    m["content"] = json.dumps(content, ensure_ascii=False)
    m["is_rich_text"] = False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replace", action="store_true")
    args = ap.parse_args()
    out = DRAFTS / DST
    if out.exists() and not args.replace:
        raise SystemExit(f"{DST} exists; pass --replace to overwrite it.")

    d = Draft(json.loads((DRAFTS / SRC / "draft_content.json").read_text(encoding="utf-8")))
    main_t, log = d.track("main"), []

    # ---- 3. cold open: the swear word becomes its own muted clip --------------------------
    first = main_t["segments"][0]
    beep = d.track("bleep")["segments"][0]["target_timerange"]
    assert first["target_timerange"]["start"] == 0 and beep["start"] < first["target_timerange"]["duration"]
    a, b, end = beep["start"], beep["start"] + beep["duration"], first["target_timerange"]["duration"]
    src0 = first["source_timerange"]["start"]
    first["common_keyframes"] = [k for k in first["common_keyframes"] if k["property_type"] != "KFTypeVolume"]
    word, rest = d.clone(first), d.clone(first)
    set_time(first, 0, a, src0)
    set_time(word, a, b - a, src0 + a)
    word["volume"], word["last_nonzero_volume"] = 0.0, 1.0
    set_time(rest, b, end - b, src0 + b)
    d.insert(main_t, word)
    d.insert(main_t, rest)
    log.append(f"swear split at {a / US:.2f}-{b / US:.2f}s")

    # ---- 4. automatic jump-cut zooms off ----------------------------------------------------
    n = 0
    for s in main_t["segments"]:
        sc = s["clip"]["scale"]
        if abs(sc["x"] - 1.18) < 1e-3 and abs(s["clip"]["transform"]["x"]) < 1e-6:
            sc["x"] = sc["y"] = 1.0
            n += 1
    log.append(f"{n} automatic 1.18 zooms removed")

    # ---- 5. brand colours on the cards ------------------------------------------------------
    hud_bg = iter(graphics.layout(spec, 3840, 2160, ASSETS)[0] for spec in HUDS)
    for s in sorted(d.track("overlay")["segments"], key=lambda s: s["target_timerange"]["start"]):
        m = d.mat[s["material_id"]][1]
        if "gfx_hud-background" in m["path"]:
            png = next(hud_bg)
            m["path"], m["material_name"] = str(png), png.name
    n = 0
    for lst, m in list(d.mat.values()):
        if lst is not d.c["materials"]["texts"]:
            continue
        content = json.loads(m["content"])
        for st in content["styles"]:
            col = st["fill"]["content"]["solid"]["color"]
            for old, new in RECOLOUR.items():
                if all(abs(x - y) < 0.01 for x, y in zip(col, old)):
                    st["fill"]["content"]["solid"]["color"] = list(new)
                    n += 1
        if "  " in content["text"]:  # 7. typo: double space
            i = content["text"].index("  ")
            content["text"] = content["text"][:i] + content["text"][i + 1:]
            for st in content["styles"]:
                st["range"] = [r - (r > i) for r in st["range"]]
            log.append(f"double space fixed: {content['text']!r}")
        m["content"] = json.dumps(content, ensure_ascii=False)
        if (m.get("background_color") or "").upper() == "#FFD54A":
            m["background_color"] = "#F4C70F"
    log.append(f"{n} card text colours changed, 3 HUD panels redrawn")

    # ---- 6. travel map: exact mask, old static card out -------------------------------------
    for m in d.c["materials"].get("common_mask", []):
        m["config"]["width"] = m["config"]["height"] = 1.0
    ov = d.track("overlay")
    before = len(ov["segments"])
    ov["segments"] = [s for s in ov["segments"] if "gfx_map-background" not in d.path(s)]
    log.append(f"map mask set to the clip size, {before - len(ov['segments'])} old map card removed")

    # ---- 1. freeze + narration at the start of chapter 06 -----------------------------------
    label = next(s for s in d.track("chapters")["segments"]
                 if "THE LOCALS" in json.loads(d.mat[s["material_id"]][1]["content"])["text"])
    first_clip = min((s for s in main_t["segments"] if d.path(s).endswith(FREEZE_CLIP)),
                     key=lambda s: s["target_timerange"]["start"])
    T = first_clip["target_timerange"]["start"]
    assert 0 <= label["target_timerange"]["start"] - T < US, "chapter label is not at the clip start"

    mp3, sentences = assets.narration(ASSETS.name, LOCALS["text"], VOICE, tagged=LOCALS["tagged"])
    ndur = int(round(assets.audio_duration(mp3) * US))
    D = int(0.2 * US) + ndur + int(0.35 * US)
    D -= D % 16667  # whole frames at 60 fps, near enough

    # everything from T on moves later; the chapter label stays with the chapter start
    spanning = []
    for t in d.c["tracks"]:
        for s in t["segments"]:
            tr = s["target_timerange"]
            if s is label:
                continue
            if tr["start"] >= T:
                tr["start"] += D
            elif tr["start"] + tr["duration"] > T + 1000:
                spanning.append((t, s))
    for t, s in spanning:  # music running through the freeze: let it play on, keep later levels in place
        assert t["type"] == "audio", f"unexpected clip across the insert point on track {t.get('name')}"
        rel = T - s["target_timerange"]["start"]
        s["target_timerange"]["duration"] += D
        s["source_timerange"]["duration"] += D
        for kf in s.get("common_keyframes") or []:
            for k in kf["keyframe_list"]:
                if k["time_offset"] > rel:
                    k["time_offset"] += D
        mat_path = d.path(s)
        src_end = s["source_timerange"]["start"] + s["source_timerange"]["duration"] - D
        for s2 in t["segments"]:  # the continuation of the same track picks up later in the file
            if s2 is not s and d.path(s2) == mat_path and abs(s2["source_timerange"]["start"] - src_end) < 50000:
                s2["source_timerange"]["start"] += D
        log.append(f"music '{Path(mat_path).name[:40]}' plays through the freeze")

    frame = ASSETS / f"freeze_{Path(FREEZE_CLIP).stem}_{FREEZE_AT:.2f}.png"
    if not frame.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{FREEZE_AT:.3f}", "-i", str(FOOTAGE / FREEZE_CLIP),
                        "-frames:v", "1", str(frame)], check=True)
    old_freeze = next(s for s in main_t["segments"] if "freeze_42700" in d.path(s))
    fz = d.clone(old_freeze)
    fm = d.mat[fz["material_id"]][1]
    fm["path"], fm["material_name"] = str(frame), frame.name
    set_time(fz, T, D, 0)
    for kf in fz["common_keyframes"]:  # same look as the other freezes: black and white, slow push
        kf["keyframe_list"][-1]["time_offset"] = D if len(kf["keyframe_list"]) > 1 else 0
    d.insert(main_t, fz)

    def add_narration(mp3: Path, sentences: list, at: int) -> int:
        tmpl = d.track("narration")["segments"][1]
        ns = d.clone(tmpl)
        nm = d.mat[ns["material_id"]][1]
        dur = int(round(assets.audio_duration(mp3) * US))
        nm["path"], nm["name"], nm["duration"] = str(mp3), mp3.name, dur
        set_time(ns, at, dur, 0)
        ns["volume"] = assets.volume_for(mp3, NARRATION_LUFS)
        ns["last_nonzero_volume"] = ns["volume"]
        d.insert(d.track("narration"), ns)
        caps = d.track("narration_captions")
        ctmpl = next(s for s in caps["segments"] if len(json.loads(d.mat[s["material_id"]][1]["content"])["styles"]) == 1)
        for i, sn in enumerate(sentences):
            a = at + int(sn["start"] * US)
            b = at + (int(sentences[i + 1]["start"] * US) if i + 1 < len(sentences) else dur)
            cs = d.clone(ctmpl)
            set_text(d, cs, sn["text"])
            set_time(cs, a, b - a)
            d.insert(caps, cs)
        return dur

    add_narration(mp3, sentences, T + int(0.2 * US))
    scratch = d.clone(next(s for s in d.track("sfx")["segments"] if "vinyl-record-scratch" in d.path(s)))
    scratch["target_timerange"]["start"] = T
    d.insert(d.track("sfx2"), scratch)  # "sfx" holds the music the user moved there
    log.append(f"freeze {D / US:.2f}s at {T / US:.2f}s with narration ({ndur / US:.2f}s)")

    # ---- 2. water narration over the fishing b-roll ------------------------------------------
    broll = next(s for s in main_t["segments"] if d.path(s).endswith(WATER["over"]))
    b0, b1 = broll["target_timerange"]["start"], broll["target_timerange"]["start"] + broll["target_timerange"]["duration"]
    mp3w, sw = assets.narration(ASSETS.name, WATER["text"], VOICE, tagged=WATER["tagged"])
    wdur = add_narration(mp3w, sw, b0 + int(1.2 * US))
    assert b0 + int(1.2 * US) + wdur < b1, "water narration does not fit its b-roll"
    for t in d.c["tracks"]:  # keep the music low under the narrator instead of lifting it for the b-roll
        for s in t["segments"]:
            tr = s["target_timerange"]
            if t["type"] == "audio" and "music_" in d.path(s) and tr["start"] < b0 and tr["start"] + tr["duration"] > b1:
                for kf in s.get("common_keyframes") or []:
                    for k in kf["keyframe_list"]:
                        if kf["property_type"] == "KFTypeVolume" and b0 - 100000 <= tr["start"] + k["time_offset"] <= b1 + 100000:
                            k["values"] = [min(k["values"][0], 0.14)]
    log.append(f"water narration ({wdur / US:.2f}s) at {(b0 + 1.2 * US) / US:.2f}s")

    # ---- write ----------------------------------------------------------------------------------
    d.c["duration"] = max(s["target_timerange"]["start"] + s["target_timerange"]["duration"]
                          for s in main_t["segments"])
    d.c["id"] = str(uuid.uuid4()).upper()
    prev, pos = None, 0
    for s in main_t["segments"]:  # the main track must have no gap and no overlap
        assert abs(s["target_timerange"]["start"] - pos) <= 2, (pos, s["target_timerange"], d.path(s))
        pos = s["target_timerange"]["start"] + s["target_timerange"]["duration"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    (out / "draft_content.json").write_text(json.dumps(d.c, ensure_ascii=False), encoding="utf-8")
    import pycapcut
    shutil.copy2(pycapcut.assets.get_asset_path("DRAFT_META_TEMPLATE"), out / "draft_meta_info.json")
    print("\n".join("  " + line for line in log))
    print(f"Draft '{DST}' ({int(d.c['duration'] / US // 60)}:{d.c['duration'] / US % 60:04.1f}) written to {DRAFTS}")


if __name__ == "__main__":
    main()
