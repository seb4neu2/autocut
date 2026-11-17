#!/usr/bin/env python3
"""Stage 4 (v2): build a full CapCut draft from an edit plan (plan.json).

Where build_draft.py lays clips on one track, this assembles a produced edit:

  main video   dialogue clips (auto punch-in zooms on jump cuts), b-roll (speed ramps),
               freeze frames, placeholders, CapCut transitions
  overlays     title card, HUD, map, stickers, end card: editable CapCut text, with a
               graphics.py PNG behind it only where a panel or shape is needed
  captions     word-timed from the *verified* cut audio (verify_cuts.py), emphasis words
               highlighted, swearing censored; narration captions in a second style
  chapters     editable CapCut text labels at each section start
  audio        narration (ElevenLabs TTS), sound effects (ElevenLabs SFX), censor bleeps
               (source audio dipped under each bleep), music cues (ElevenLabs Music) that
               crossfade between sections and duck under speech

Plan format: see README ("Stage 4 v2"). Generated assets are cached in assets/<name>/.
"""

import argparse
import json
import re
import subprocess
from pathlib import Path

import pycapcut as cc
from pycapcut import KeyframeProperty as KP

import assets
import graphics
import reframe
from build_draft import (PAD_AFTER, PAD_BEFORE, load_config, load_words, make_placeholder, snap,
                         to_windows_path)

SEC = 1_000_000
PROFANITY = re.compile(r"^(mother)?fuck\w*$|^(bull)?shit\w*$|^bastard\w*$|^bitch\w*$|^asshole\w*$|^kurw\w*$", re.I)
EMPHASIS_DEFAULT = ["never", "shortcut", "shortcuts", "far", "dogs", "doggies", "dog", "ridiculous", "crazy",
                    "beautiful", "amazing", "baht", "water", "tired", "path", "destination", "view", "zero"]
CANVAS = {"landscape": (3840, 2160), "vertical": (1080, 1920)}
SFX_LEAD, SFX_UNDER_NARR = 0.65, 0.22  # a sound at a narration line's start: seconds ahead of it, max volume
CHAPTER_DROP = 0.28  # how far (in half canvas heights) a top-left card moves down under a chapter label


def us(t: float) -> int:
    return int(round(t * SEC))


def clip_range(item: dict, videos_dir: Path, words_cache: dict) -> tuple[float, float, list[dict]]:
    """Final source range of a dialogue clip (snapped to words, padded) — shared with verify_cuts.py."""
    video = videos_dir / item["clip"]
    if item["clip"] not in words_cache:
        words_cache[item["clip"]] = load_words(video)
    words = words_cache[item["clip"]]
    if item.get("snap", True):
        s = max(snap(item["start"], words, "start") - item.get("pad_before", PAD_BEFORE), 0.0)
        e = min(snap(item["end"], words, "end") + item.get("pad_after", PAD_AFTER), media_duration(video) - 0.05)
    else:  # exact times (single-word cuts already trimmed on the audio)
        s = max(item["start"] - item.get("pad_before", 0.0), 0.0)
        e = min(item["end"] + item.get("pad_after", 0.0), media_duration(video) - 0.05)
    return round(s, 3), round(e, 3), words


_durations: dict[Path, float] = {}


def media_duration(path: Path) -> float:
    if path not in _durations:
        _durations[path] = assets.audio_duration(path)
    return _durations[path]


def cut_key(item: dict, s: float, e: float) -> str:
    return f'{item["clip"]}|{s:.3f}|{e:.3f}'


def censor(word: str) -> str:
    m = re.match(r"^(\W*)(\w+)(.*)$", word)
    if not m:
        return word
    pre, core, post = m.groups()
    low = core.lower()
    if "fuck" in low:
        i = low.index("fuck")
        core = core[:i + 1] + "***" + core[i + 4:]
    elif "shit" in low:
        i = low.index("shit")
        core = core[:i + 2] + "*" + core[i + 3:]
    else:
        core = core[0] + "*" * (len(core) - 1)
    return pre + core + post


def chunk_words(words: list[dict], max_words: int = 3, max_len: float = 1.6) -> list[dict]:
    """Group timed words into short caption chunks, breaking at punctuation."""
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        text = w["text"]
        if (len(cur) >= max_words or text.endswith((".", "?", "!", ",")) or
                cur[-1]["end"] - cur[0]["start"] > max_len):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return [{"words": c, "start": c[0]["start"], "end": c[-1]["end"]} for c in chunks]


class Tracks:
    """Named tracks with first-free allocation so overlapping segments spill onto extra tracks."""

    def __init__(self, script):
        self.script, self.busy = script, {}

    def add(self, kind: cc.TrackType, base: str, seg, start: float, end: float, max_tracks: int = 4):
        for i in range(max_tracks):
            name = base if i == 0 else f"{base}{i + 1}"
            spans = self.busy.get(name)
            if spans is None:
                self.script.add_track(kind, name, relative_index=len(self.busy) + 1)
                self.busy[name] = spans = []
            if all(end <= a + 1e-6 or start >= b - 1e-6 for a, b in spans):
                spans.append((start, end))
                self.script.add_segment(seg, name)
                return
        raise RuntimeError(f"no free {base} track for {start:.2f}-{end:.2f}")


class StyledText(cc.TextSegment):
    """Text segment in which character ranges can differ in colour, size or font (CapCut rich text).
    spans: [(start, end, {"color": (r, g, b), "size": float, "font": cc.FontType})]"""

    def __init__(self, *a, spans=(), **kw):
        super().__init__(*a, **kw)
        self.spans = list(spans)

    def export_material(self):
        mat = super().export_material()
        if not self.spans:
            return mat
        content = json.loads(mat["content"])
        base = content["styles"][0]
        cuts = sorted({0, len(self.text), *(p for s, e, _ in self.spans for p in (s, e))})
        styles = []
        for s, e in zip(cuts, cuts[1:]):
            st = json.loads(json.dumps(base))
            st["range"] = [s, e]
            for a, b, change in self.spans:
                if a <= s and e <= b:
                    if "color" in change:
                        st["fill"]["content"]["solid"]["color"] = list(change["color"])
                        st["useLetterColor"] = True
                    if "size" in change:
                        st["size"] = change["size"]
                    if "font" in change:
                        f = change["font"].value
                        st["font"] = {"id": f.resource_id, "path": "C:/%s.ttf" % f.name}
            styles.append(st)
        content["styles"] = styles
        mat["content"] = json.dumps(content, ensure_ascii=False)
        mat["is_rich_text"] = True
        return mat


# CapCut 9.2's own rectangle mask. pycapcut writes an older resource id (6791700809454195207) without
# an effect path, and CapCut 9.2 silently drops that mask when it opens the draft (Vietnam v3 map had
# no mask; the user added it by hand, 2026-10-23). These fields are copied from the user's hand-made mask.
CAPCUT_RECT_MASK = {
    "resource_id": "7374021450748924432", "constant_material_id": "70F1793D-F80C-4bec-BD94-E3CA6179B344",
    "name": "Rectangle", "resource_type": "rectangle", "category": "video", "category_name": "",
    "category_id": "", "panel": "", "is_old_version": False, "loader_work_space": "", "track_segment": "",
    "contour_path": None, "source_platform": 0,
}


def rect_mask(seg, round_corner: float):
    """Rectangle mask exactly the clip's size with round corners (0-100), as CapCut 9.2 writes it."""
    seg.add_mask(cc.MaskType.矩形, size=1.0, rect_width=1.0, round_corner=round_corner)
    base = seg.mask.export_json
    cached = sorted(Path.home().glob("AppData/Local/CapCut/User Data/Cache/effect/*/02b8999168d121538a98ea59127483ef"))
    path = cached[-1].as_posix() if cached else ""
    seg.mask.export_json = lambda: {**base(), **CAPCUT_RECT_MASK, "path": path}
    return seg


def move_masks(draft_json: Path):
    """pycapcut lists masks under materials.masks; CapCut 9.2 only reads materials.common_mask."""
    d = json.loads(draft_json.read_text(encoding="utf-8"))
    mats = d["materials"]
    if mats.get("masks"):
        mats["common_mask"] = mats.get("common_mask", []) + mats["masks"]
        mats["masks"] = []
        draft_json.write_text(json.dumps(d, ensure_ascii=False, indent=4), encoding="utf-8")


def find_spans(text: str, highlight: dict) -> list:
    """{"phrase": [r, g, b]} -> colour spans for the phrases that occur in `text`."""
    return [(i, i + len(p), {"color": tuple(c)}) for p, c in highlight.items() if (i := text.find(p)) >= 0]


FORTY_TWO = re.compile(r"forty[- ]two|(?<![0-9,.])42(?![0-9])|zweiundvierzig|cuarenta y dos|czterdzie[sś]ci dwa", re.I)


def forty_two_spans(text: str) -> list:
    """The channel number is always orange, in any language it is said in (CLAUDE.md)."""
    return [(m.start(), m.end(), {"color": graphics.ORANGE_F}) for m in FORTY_TWO.finditer(text)]


def fill_scale(mat_w: int, mat_h: int, cw: int, ch: int) -> float:
    """CapCut fits material inside the canvas; this is the extra scale that makes it fill instead."""
    ma, ca = mat_w / mat_h, cw / ch
    return round(max(ma / ca, ca / ma), 4)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("videos_dir", type=Path)
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "config.yaml")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--no-music", action="store_true", help="Skip music generation/placement (faster iteration)")
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    name = plan["name"]
    config = load_config(args.config)
    mappings = config.get("path_mappings") or []
    aname = plan.get("assets", name)  # share cached assets (e.g. a Short cut from the main video)
    out_dir = assets.asset_dir(aname)
    cw, ch = CANVAS[plan.get("canvas", "landscape")]
    vertical = ch > cw
    fps = plan.get("fps", 60)
    voice = plan.get("narrator_voice")
    emphasis = set(w.lower() for w in plan.get("emphasis", []))  # plain white captions unless the plan lists words
    # footage file -> corrected copy to show instead (e.g. rotation metadata fixed); transcripts and
    # audio for verification stay with the original in videos_dir
    media = plan.get("media", {})

    def media_path(src: str) -> Path:
        return Path(media[src]) if src in media else args.videos_dir / src
    cutwords = {}
    cw_file = out_dir / "cutwords.json"
    if cw_file.exists():
        cutwords = json.loads(cw_file.read_text(encoding="utf-8"))

    # ---------- layout pass: durations, narration lengths --------------------------------
    words_cache: dict = {}
    timeline, t = [], 0.0
    for item in plan["timeline"]:
        entry = {"item": item, "start": t}
        narr = item.get("narration")
        if narr:
            mp3, sentences = assets.narration(aname, narr["text"], narr.get("voice", voice),
                                              tagged=narr.get("tagged"), file=narr.get("file"),
                                              **plan.get("narrator_settings", {}))
            entry["narr"] = (mp3, sentences, assets.audio_duration(mp3))
        if "clip" in item:
            s, e, words = clip_range(item, args.videos_dir, words_cache)
            entry.update(kind="clip", src=(s, e), dur=e - s)
        elif "broll" in item:
            speed = item.get("speed", 1.0)
            entry.update(kind="broll", src=(item["start"], item["end"]), dur=(item["end"] - item["start"]) / speed)
        elif "freeze" in item:
            d = item.get("duration")
            if d is None:
                d = narr.get("offset", 0.2) + entry["narr"][2] + item.get("tail", 0.35)
            entry.update(kind="freeze", dur=d)
        elif "placeholder" in item:
            entry.update(kind="placeholder", dur=float(item["duration"]))
        else:
            raise ValueError(f"unknown timeline item: {item}")
        if entry.get("narr") and entry["kind"] != "freeze":
            over = narr.get("offset", 0) + entry["narr"][2] - entry["dur"]
            if over > 0.05:
                print(f"  note: narration '{narr['text'][:40]}...' runs {over:.1f}s past its item")
        timeline.append(entry)
        t += entry["dur"]
    total = t

    # ---------- draft + tracks ----------------------------------------------------------
    draft_dir = Path(config["draft_output_dir"]).expanduser()
    folder = cc.DraftFolder(str(draft_dir))
    try:
        script = folder.create_draft(name, cw, ch, fps, allow_replace=args.replace)
    except FileExistsError:
        raise SystemExit(f"Draft '{name}' exists in {draft_dir}; pass --replace to overwrite it.")
    script.add_track(cc.TrackType.video, "main")
    tracks = Tracks(script)
    materials: dict[str, cc.VideoMaterial] = {}

    def video_material(path: Path) -> cc.VideoMaterial:
        k = str(path)
        if k not in materials:
            m = cc.VideoMaterial(str(path))
            m.path = to_windows_path(path, mappings)
            script.add_material(m)
            materials[k] = m
        return materials[k]

    def audio_seg(path: Path, start: float, dur: float | None = None, volume: float = 1.0, src_start: float = 0.0):
        mat = cc.AudioMaterial(str(path))
        avail = mat.duration / SEC - src_start
        d = min(dur if dur is not None else avail, avail)
        seg = cc.AudioSegment(mat, cc.trange(us(start), us(d)), source_timerange=cc.trange(us(src_start), us(d)),
                              volume=volume)
        return seg, d

    def text_style(size, color=(1, 1, 1), bold=True, italic=False):
        return cc.TextStyle(size=size, color=color, bold=bold, italic=italic, align=1, auto_wrapping=True,
                            max_line_width=0.8 if vertical else 0.7)

    cap_y = -0.42 if vertical else -0.618   # landscape values as the user set them by hand in Thailand v5
    cap_size = 11.0 if vertical else 8.075
    border = cc.TextBorder(color=(0, 0, 0), width=55)
    beep = assets.beep(aname)
    chapters, chapter_no = [], 0
    prev_src, alt = None, False
    over_pos: dict[str, float] = {}

    for idx, e in enumerate(timeline):
        item, t0, dur, kind = e["item"], e["start"], e["dur"], e["kind"]
        seg, over = None, None

        # --- main track -----------------------------------------------------------------
        if kind in ("clip", "broll"):
            src_name = item.get("clip") or item.get("broll")
            s, e_ = e["src"]
            pic_s = s   # where the picture starts in its source
            over = item.get("over") if kind == "clip" else None
            if over:  # the clip is heard, but another shot is seen (voice over b-roll); it runs on
                src_name = over["broll"]  # from where the previous "over" of the same shot stopped
                pic_s = over.get("start", over_pos.get(src_name, 0.0))
                over_pos[src_name] = pic_s + dur
            mat = video_material(media_path(src_name))
            # "fit": the whole picture across the width of a vertical canvas, CapCut's background blur behind it
            # (for wide group shots that a vertical crop would cut apart)
            base = fill_scale(mat.width, mat.height, cw, ch) if vertical and not item.get("fit") else 1.0
            zoom = item.get("zoom")  # no zoom unless the plan asks for one and has a reason (CLAUDE.md)
            if zoom == "auto":  # hide jump cuts: alternate framing when consecutive cuts share a source
                alt = (not alt) if prev_src == src_name else False
                z = 1.18 if alt else 1.0
            elif zoom == "punch":
                z = 1.3
            else:
                z = float(zoom) if isinstance(zoom, (int, float)) else 1.0
            prev_src = src_name if kind == "clip" else None
            vol = item.get("volume", 1.0 if kind == "clip" else 0.0)
            tx, ty = 0.0, float(item.get("y", 0.0))
            rot = float((over or item).get("rotate", 0))
            if over:
                tx = float(over.get("x", 0.0))
            elif "x" in item:
                tx = float(item["x"])
            elif vertical and plan.get("auto_reframe", True) and kind == "clip":
                fx = reframe.face_x(media_path(src_name), s, e_, out_dir / "reframe.json")
                if fx is not None:  # shift the crop so the face sits in the middle, without exposing edges
                    disp_w = cw * base * z
                    limit = (disp_w - cw) / cw
                    tx = max(-limit, min(limit, -(fx - 0.5) * disp_w / (cw / 2)))
            seg = cc.VideoSegment(mat, cc.trange(us(t0), us(dur)), source_timerange=cc.trange(us(pic_s), us(e_ - s)),
                                  volume=0.0 if over else vol, clip_settings=cc.ClipSettings(scale_x=base * z, scale_y=base * z,
                                                                            transform_x=tx, transform_y=ty,
                                                                            rotation=rot))
            if zoom == "push":
                seg.add_keyframe(KP.uniform_scale, 0, base)
                seg.add_keyframe(KP.uniform_scale, us(dur), base * 1.12)
            if item.get("pan"):  # [x from, x to]: slow sideways move across a wide shot (vertical drafts), in "x" units
                seg.add_keyframe(KP.position_x, 0, float(item["pan"][0]))
                seg.add_keyframe(KP.position_x, us(dur), float(item["pan"][1]))
        elif kind == "freeze":
            frame = out_dir / f'freeze_{Path(item["freeze"]).stem}_{item["at"]:.2f}.png'
            if not frame.exists():
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f'{item["at"]:.3f}', "-i",
                                str(media_path(item["freeze"])), "-frames:v", "1", str(frame)], check=True)
            mat = video_material(frame)
            base = fill_scale(mat.width, mat.height, cw, ch) if vertical and not item.get("fit") else 1.0
            seg = cc.VideoSegment(mat, cc.trange(us(t0), us(dur)), source_timerange=cc.trange(0, us(dur)),
                                  clip_settings=cc.ClipSettings(scale_x=base, scale_y=base))
            seg.add_keyframe(KP.uniform_scale, 0, base * 1.0)
            seg.add_keyframe(KP.uniform_scale, us(dur), base * 1.1)
            if item.get("bw", True):
                seg.add_keyframe(KP.saturation, 0, -1.0)
            prev_src = None
        elif kind == "placeholder":
            ph = out_dir / f"placeholder_{idx:03}.mp4"
            make_placeholder(item["placeholder"], dur, ph)
            mat = video_material(ph)
            seg = cc.VideoSegment(mat, cc.trange(us(t0), us(dur)), source_timerange=cc.trange(0, us(dur)))
            prev_src = None

        mutes = []  # swear words: (start, end) inside the clip, each becomes its own muted piece

        # --- bleeps + captions for dialogue ----------------------------------------------
        if kind == "clip":
            s, e_ = e["src"]
            key = cut_key(item, s, e_)
            if not item.get("auto_captions", True):  # every caption of this clip is given in the plan
                rel = []
            elif key in cutwords:   # verified words, already relative to the clip start
                rel = [w for w in cutwords[key] if w["type"] == "word"]
            else:
                rel = [{"text": w.get("text", w.get("word", "")), "start": w["start"] - s, "end": w["end"] - s,
                        "type": "word"} for w in e_words(args.videos_dir, item, words_cache)
                       if s <= w["start"] < e_]
            for ov in item.get("captions", []):  # manual caption text for a source-time range
                a, b = ov["from"] - s, ov["to"] - s
                rel = [w for w in rel if not (a - 0.05 <= w["start"] < b)]
                rel.append({"text": ov["text"], "start": max(a, 0), "end": min(b, dur), "type": "word", "manual": True})
            rel.sort(key=lambda w: w["start"])
            vol = item.get("volume", 1.0)
            for w in rel:
                core = re.sub(r"[^\w']", "", w["text"]).lower()
                if not w.get("manual") and PROFANITY.match(core):
                    ws, we = max(w["start"] - 0.03, 0.0), min(w["end"] + 0.05, dur)
                    if mutes and ws <= mutes[-1][1]:
                        ws = mutes[-1][1]
                    if we - ws < 0.05:
                        continue
                    mutes.append((ws, we))
                    bseg, _ = audio_seg(beep, t0 + ws, we - ws, volume=0.3)
                    tracks.add(cc.TrackType.audio, "bleep", bseg, t0 + ws, t0 + we)
                    w["text"] = censor(w["text"])
            if item.get("caption", True):
                chunks = []
                for w in rel:
                    if w.get("manual"):
                        chunks.append({"words": [w], "start": w["start"], "end": w["end"]})
                chunks_auto = chunk_words([w for w in rel if not w.get("manual")])
                chunks = sorted(chunks + chunks_auto, key=lambda c: c["start"])
                for i, c in enumerate(chunks):
                    a = max(c["start"], 0.0)
                    nxt = chunks[i + 1]["start"] if i + 1 < len(chunks) else dur
                    b = min(max(c["end"] + 0.25, a + 0.4), nxt, dur)
                    if b - a < 0.08:
                        continue
                    text = " ".join(w["text"] for w in c["words"]).strip()
                    hot = any(re.sub(r"[^\w]", "", w["text"]).lower() in emphasis for w in c["words"])
                    tseg = StyledText(text, cc.trange(us(t0 + a), us(b - a)), spans=forty_two_spans(text),
                                      font=cc.FontType.Poppins_Bold,
                                      style=text_style(cap_size * (1.15 if hot else 1.0),
                                                       graphics.YELLOW_F if hot else (1, 1, 1)),
                                      border=border, clip_settings=cc.ClipSettings(transform_y=cap_y))
                    if hot:
                        tseg.add_animation(cc.TextIntro.弹入, 150000)
                    tracks.add(cc.TrackType.text, "captions", tseg, t0 + a, t0 + b)

            # other people's lines (e.g. translated Vietnamese) on the left side, apart from the main captions
            for sc in item.get("side_captions", []):
                a, b = max(sc["from"] - s, 0.0), min(sc["to"] - s, dur)
                if b - a < 0.08:
                    continue
                tseg = StyledText(sc["text"], cc.trange(us(t0 + a), us(b - a)), spans=forty_two_spans(sc["text"]),
                                  font=cc.FontType.Poppins_Bold,
                                  style=cc.TextStyle(size=cap_size, color=(1, 1, 1), bold=True, align=1,
                                                     auto_wrapping=True, max_line_width=0.8 if vertical else 0.3),
                                  # vertical: centred above the picture (in the blur of a "fit" shot), not at the side
                                  border=border, clip_settings=cc.ClipSettings(transform_x=sc.get("x", 0.0 if vertical else -0.62),
                                                                               transform_y=sc.get("y", 0.42 if vertical else -0.1)))
                tracks.add(cc.TrackType.text, "side_captions", tseg, t0 + a, t0 + b)

        # the swear word is cut out as its own clip with volume 0 (easy to see and undo in CapCut);
        # the beep plays over it. A "push" zoom is dropped on such a clip, pieces cannot share it.
        pieces = [seg]
        if over:  # the voice goes on its own track, cut into pieces around swear words like the video below
            cuts = [0.0] + [t for m in mutes for t in m] + [dur]
            for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
                if b - a < 0.001:
                    continue
                vseg, _ = audio_seg(args.videos_dir / Path(item["clip"]).with_suffix(".mp3"), t0 + a, b - a,
                                    volume=0.0 if i % 2 else vol, src_start=s + a)
                tracks.add(cc.TrackType.audio, "voice", vseg, t0 + a, t0 + b)
        elif mutes:
            cuts = [0.0] + [t for m in mutes for t in m] + [dur]
            marks = [us(t0)] + [us(t0 + c) for c in cuts[1:-1]] + [us(t0) + us(dur)]
            pieces = []
            for i, (a, b) in enumerate(zip(marks, marks[1:])):
                if b - a < 1000:
                    continue
                pieces.append(cc.VideoSegment(mat, cc.trange(a, b - a),
                                              source_timerange=cc.trange(us(pic_s) + a - us(t0), b - a),
                                              volume=0.0 if i % 2 else vol,
                                              clip_settings=cc.ClipSettings(scale_x=base * z, scale_y=base * z,
                                                                            transform_x=tx, transform_y=ty,
                                                                            rotation=rot)))
        if item.get("transition"):
            pieces[-1].add_transition(getattr(cc.TransitionType, item["transition"]),
                                      duration=us(item.get("transition_duration", 0.5)))
        for piece in pieces:
            if item.get("fit"):
                piece.add_background_filling("blur", 0.375)
            script.add_segment(piece, "main")

        # --- one caption over several items (a sentence built from single-word cuts) -------
        if item.get("line"):
            last = timeline[min(idx + item.get("line_items", 1), len(timeline)) - 1]
            b = last["start"] + last["dur"]
            tseg = StyledText(item["line"], cc.trange(us(t0), us(b - t0)), spans=forty_two_spans(item["line"]),
                              font=cc.FontType.Poppins_Bold, style=text_style(cap_size), border=border,
                              clip_settings=cc.ClipSettings(transform_y=cap_y))
            tracks.add(cc.TrackType.text, "captions", tseg, t0, b)

        # --- narration (+ its captions) --------------------------------------------------
        if e.get("narr"):
            mp3, sentences, ndur = e["narr"]
            nt = t0 + item["narration"].get("offset", 0.2)
            nvol = item["narration"].get("volume")
            if nvol is None:  # same loudness for every line when the plan sets a target, else full volume
                nvol = assets.volume_for(mp3, plan["narration_lufs"]) if "narration_lufs" in plan else 1.0
            nseg, _ = audio_seg(mp3, nt, volume=nvol)
            tracks.add(cc.TrackType.audio, "narration", nseg, nt, nt + ndur)
            for i, sn in enumerate(sentences):
                a = nt + sn["start"]
                b = nt + (sentences[i + 1]["start"] if i + 1 < len(sentences) else ndur)
                cap = sn["text"].replace("A.I.", "AI")  # spoken as letters, written the way the user wrote it
                if sn["text"].endswith("A.I."):  # that dot also ended the sentence
                    cap += "."
                tseg = StyledText(cap, cc.trange(us(a), us(b - a)), font=cc.FontType.Poppins_Bold,
                                  style=text_style(cap_size, graphics.YELLOW_F, italic=True),
                                  border=border, clip_settings=cc.ClipSettings(transform_y=cap_y),
                                  spans=forty_two_spans(cap) +
                                  find_spans(cap, item["narration"].get("highlight", {})))
                tracks.add(cc.TrackType.text, "narration_captions", tseg, a, b)

        # --- sfx -------------------------------------------------------------------------
        for fx in item.get("sfx", []):
            spec = plan["sfx"][fx["id"]]
            if spec.get("file"):  # a recording in the asset folder (e.g. a real bird call), not generated
                path = out_dir / spec["file"]
            else:
                path = assets.sfx(aname, spec["prompt"], spec.get("duration"), name=spec.get("name"))
            at = t0 + dur - 0.15 if fx.get("at") == "end" else t0 + float(fx.get("at", 0))
            at += fx.get("shift", 0.0)  # e.g. "end" with shift -2.1: a sting inside the clip's last words
            vol = fx.get("volume", spec.get("volume", 0.8))
            if e.get("narr") and fx.get("at") != "end" and spec.get("lead"):  # "lead": stings, not pops or chimes
                # a sound that would start with the narrator's first words plays just before them, quieter
                # (user, 2026-10-22, Vietnam v2: stings moved ~0.65 s earlier, volume 0.6 -> 0.2-0.24)
                nt = t0 + item["narration"].get("offset", 0.2)
                if abs(at - nt) < 0.5:
                    at, vol = nt - SFX_LEAD, min(vol, SFX_UNDER_NARR)
            fseg, fd = audio_seg(path, max(at, 0), fx.get("max", spec.get("max")), volume=vol,
                                 src_start=fx.get("skip", spec.get("skip", 0.0)))
            tracks.add(cc.TrackType.audio, "sfx", fseg, max(at, 0), max(at, 0) + fd)

        # --- overlays --------------------------------------------------------------------
        for ov in item.get("overlay", []):
            if "video" in ov:  # picture-in-picture clip from the asset folder, e.g. the animated route map
                a = t0 + ov.get("at", 0.0)
                vmat = video_material(out_dir / ov["video"])
                d = min(ov.get("duration", vmat.duration / SEC), vmat.duration / SEC)
                vseg = cc.VideoSegment(vmat, cc.trange(us(a), us(d)), source_timerange=cc.trange(0, us(d)), volume=0.0,
                                       clip_settings=cc.ClipSettings(scale_x=ov.get("scale", 1.0),
                                                                     scale_y=ov.get("scale", 1.0),
                                                                     transform_x=ov.get("x", 0.0),
                                                                     transform_y=ov.get("y", 0.0)))
                if ov.get("round", 25 if "map" in ov["video"].lower() else None) is not None:
                    # rectangle mask exactly the clip's size, round corners 25 by default on the route map (CLAUDE.md)
                    rect_mask(vseg, ov.get("round", 25))
                vseg.add_animation(cc.IntroType.渐显, us(0.3))
                vseg.add_animation(cc.OutroType.渐隐, us(0.3))
                tracks.add(cc.TrackType.video, "overlay", vseg, a, a + d)
                continue
            # all wording is CapCut text; an image is used only for the shapes behind it
            png, texts = graphics.layout(ov["gfx"], cw, ch, out_dir)
            a = t0 + ov.get("at", 0.0)
            d = ov.get("duration", dur - ov.get("at", 0.0))
            t_in, t_out = min(us(0.4), us(d / 3)), min(us(0.35), us(d / 3))
            # a top-left card shown while this item's chapter label is up goes lower, under the label
            # (user, 2026-10-22: "SOFT CAKE REVIEW" sat under "09 · THE PARTY" in Vietnam v2)
            where = ov["gfx"].get("where", "top-left" if ov["gfx"]["type"] in ("hud", "info") else "")
            label_end = t0 + 0.2 + min(3.0, max(dur, 1.5))
            drop = (CHAPTER_DROP if item.get("section") and item.get("section_label", True)
                    and where == "top-left" and a < label_end else 0.0)
            if png:  # fades with its text; a zoom would slide the panel out from under the words
                oseg = cc.VideoSegment(video_material(png), cc.trange(us(a), us(d)),
                                       source_timerange=cc.trange(0, us(d)),
                                       clip_settings=cc.ClipSettings(transform_y=-drop))
                oseg.add_animation(cc.IntroType.渐显, t_in)
                oseg.add_animation(cc.OutroType.渐隐, t_out)
                tracks.add(cc.TrackType.video, "overlay", oseg, a, a + d)
            unit = graphics.px_per_size(cw, ch)
            for tx in texts:
                fonts = {k: getattr(cc.FontType, v[0]) for k, v in graphics.TEXT_FONTS.items()}
                spans = [(s, e, {**({"color": c["color"]} if "color" in c else {}),
                                 **({"size": c["px"] / unit} if "px" in c else {}),
                                 **({"font": fonts[c["font"]]} if "font" in c else {})})
                         for s, e, c in tx.get("spans", [])]
                bg = tx.get("background")
                tseg = StyledText(
                    tx["text"], cc.trange(us(a), us(d)), font=fonts[tx["font"]], spans=spans,
                    style=cc.TextStyle(size=tx["px"] / unit, color=tx["color"], align=tx.get("align", 1)),
                    border=cc.TextBorder(color=(0, 0, 0), width=tx["border"]) if tx.get("border") else None,
                    background=cc.TextBackground(**bg) if bg else None,
                    clip_settings=cc.ClipSettings(transform_x=(tx["x"] - cw / 2) / (cw / 2),
                                                  transform_y=(ch / 2 - tx["y"]) / (ch / 2) - drop,
                                                  rotation=tx.get("rotation", 0.0)))
                intro = ov.get("in") if ov.get("in") in cc.TextIntro.__members__ else tx.get("intro", "渐显")
                tseg.add_animation(getattr(cc.TextIntro, intro), t_in)
                tseg.add_animation(cc.TextOutro.渐隐, t_out)
                tracks.add(cc.TrackType.text, "overlay_text", tseg, a, a + d, max_tracks=8)

        # --- chapter labels --------------------------------------------------------------
        if item.get("section"):
            chapter_no += 1
            chapters.append((t0, item["section"]))
            if item.get("section_label", True):
                label = f'{chapter_no:02d} · {item["section"].upper()}'
                d = min(3.0, max(dur, 1.5))
                tseg = cc.TextSegment(label, cc.trange(us(t0 + 0.2), us(d)), font=cc.FontType.BebasNeue,
                                      style=cc.TextStyle(size=7.0 if not vertical else 9.0, color=(1, 1, 1), align=0),
                                      background=cc.TextBackground(color="#000000", alpha=0.55, round_radius=0.35),
                                      clip_settings=cc.ClipSettings(transform_x=-0.62 if not vertical else 0.0,
                                                                    transform_y=0.82 if not vertical else 0.62))
                tseg.add_animation(cc.TextIntro.向右滑动, 300000)
                tseg.add_animation(cc.TextOutro.渐隐, 300000)
                tracks.add(cc.TrackType.text, "chapters", tseg, t0 + 0.2, t0 + 0.2 + d)

    # ---------- music: cues crossfade across two tracks, ducked under speech -------------
    if not args.no_music and plan.get("music"):
        cues, cur = [], None
        for e in timeline:
            m = e["item"].get("music")
            if m is None:
                continue
            if cur:
                cur["end"] = e["start"]
                cues.append(cur)
            cur = None if m == "stop" else {"id": m, "start": e["start"]}
        if cur:
            cur["end"] = total
            cues.append(cur)
        for n, cue in enumerate(cues):
            spec = plan["music"][cue["id"]]
            tail = 0.0 if n == len(cues) - 1 else 1.5
            length = cue["end"] - cue["start"] + tail
            if spec.get("file"):  # pinned: keep a track you liked even if the section length changes
                mp3 = out_dir / spec["file"]
                if length > assets.audio_duration(mp3) + 0.5:
                    print(f"  note: pinned music '{spec['file']}' is shorter than its section ({length:.1f}s)")
            else:
                mp3 = assets.music(aname, spec["prompt"], length + 2, name=spec.get("name"))
            mseg, md = audio_seg(mp3, cue["start"], length, volume=1.0, src_start=spec.get("skip", 0.0))
            mseg.add_fade(us(spec.get("fade_in", 0.4)), us(1.5 if tail else 2.5))
            level_dialog, level_open = spec.get("dialog", 0.12), spec.get("open", 0.5)
            last = None
            for e in timeline:
                a, b = e["start"], e["start"] + e["dur"]
                if b <= cue["start"] or a >= cue["start"] + md:
                    continue
                talky = (e["kind"] == "clip" and e["item"].get("volume", 1.0) > 0) or e.get("narr")
                lvl = e["item"].get("music_level", level_dialog if talky else level_open)
                off = max(a - cue["start"], 0.0)
                if last is None:
                    mseg.add_keyframe(us(off), lvl)
                elif abs(lvl - last) > 1e-3:
                    mseg.add_keyframe(us(max(off - 0.25, 0.0)), last)
                    mseg.add_keyframe(us(off), lvl)
                last = lvl
            tracks.add(cc.TrackType.audio, "music", mseg, cue["start"], cue["start"] + md, max_tracks=2)

    script.save()
    move_masks(Path(script.save_path))

    m, s = divmod(total, 60)
    lines = [f"{int(a // 60)}:{int(a % 60):02d} {title}" for a, title in chapters]
    if lines:  # a Short without chapters must not wipe the main video's list in a shared asset folder
        (out_dir / "chapters.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Draft '{name}' ({cw}x{ch} @ {fps}fps, {int(m)}:{s:04.1f}) written to {draft_dir}")
    print("Chapters:\n  " + "\n  ".join(lines))


def e_words(videos_dir: Path, item: dict, words_cache: dict) -> list[dict]:
    """Source-transcript words for a clip (fallback when the cut hasn't been verified)."""
    video = videos_dir / item["clip"]
    el = video.with_suffix(".elevenlabs.json")
    if el.exists():
        return [w for w in json.loads(el.read_text(encoding="utf-8"))["words"] if w["type"] == "word"]
    return words_cache.get(item["clip"], [])


if __name__ == "__main__":
    main()
