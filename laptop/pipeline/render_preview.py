#!/usr/bin/env python3
"""Preview video (MP4) of a CapCut draft, rendered with ffmpeg, without CapCut. For watching a cut on the
phone while away from the PC. Not the final export: no transitions, text animations or effects, fonts and
text sizes approximate (graphics.px_per_size), volume keyframes linear, rotation only in steps of 90.

  python pipeline/render_preview.py <draft name> <out.mp4> [--height 1280]

Main track: each clip trimmed and sped like in the draft, scaled and moved by its clip settings, with
CapCut's background blur where set. Other video tracks are laid on top (pictures, videos). Text segments
become pictures (rich text colours and sizes, black outline). Audio: the clips' own sound at their volume
plus every audio track with its volume keyframes.
"""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import graphics

ROOT = Path(r"C:\Users\niu\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")
FPS = 30
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def sec(us: int) -> float:
    return us / 1e6


def font_file(path: str) -> str:
    p = path.lower()
    for key, word in (("anton", "anton"), ("bebas", "bebas"), ("poppins", "poppins")):
        if word in p:
            try:
                return graphics._text_font_file(key)
            except KeyError:
                pass
    return graphics._text_font_file("poppins")


def text_picture(content: dict, max_w: float, unit: float, scale: float) -> Image.Image:
    """One CapCut text as a transparent picture: rich text per character (colour, size, font), centred lines,
    wrapped at max_w pixels, black outline like the CapCut stroke."""
    text = content["text"]
    styles = content.get("styles") or [{}]
    per_char = []
    for i in range(len(text)):
        st = next((s for s in styles if s.get("range", [0, len(text)])[0] <= i < s.get("range", [0, len(text)])[1]), styles[0])
        col = st.get("fill", {}).get("content", {}).get("solid", {}).get("color", [1, 1, 1])
        stroke = (st.get("strokes") or [{}])[0].get("width", 0.08)
        per_char.append((tuple(int(c * 255) for c in col), st.get("size", 10.0) * unit * scale,
                         font_file(st.get("font", {}).get("path", "")), stroke))
    fonts = {}

    def fnt(file, px):
        return fonts.setdefault((file, round(px)), ImageFont.truetype(file, max(6, round(px))))

    # words with their character styles, wrapped into lines
    lines, line, width = [], [], 0.0
    words = []
    for para in text.split("\n"):
        start = text.index(para) if para else 0
        tokens, pos = [], start
        for w in para.split(" "):
            tokens.append((w, pos)); pos += len(w) + 1
        words.append(tokens)
    for tokens in words:
        line, width = [], 0.0
        for w, pos in tokens:
            ww = sum(fnt(per_char[pos + k][2], per_char[pos + k][1]).getlength(c) for k, c in enumerate(w))
            sp = fnt(per_char[pos][2], per_char[pos][1]).getlength(" ") if w else 0
            if line and width + sp + ww > max_w and "\n" not in text:  # set line breaks (headlines) are kept as they are
                lines.append(line); line, width = [], 0.0
            line.append((w, pos, ww)); width += (sp if len(line) > 1 else 0) + ww
        lines.append(line)
    big = max(p[1] for p in per_char) if per_char else 20
    pad = int(big * 0.3)
    lh = big * 1.25
    lw = [sum(x[2] for x in ln) + (len(ln) - 1) * fnt(per_char[0][2], per_char[0][1]).getlength(" ") for ln in lines]
    img = Image.new("RGBA", (int(max(lw + [1]) + 2 * pad), int(lh * len(lines) + 2 * pad)))
    d = ImageDraw.Draw(img)
    for li, ln in enumerate(lines):
        x = pad + (img.width - 2 * pad - lw[li]) / 2
        y = pad + li * lh + lh / 2
        for w, pos, ww in ln:
            for k, c in enumerate(w):
                col, px, file, stroke = per_char[pos + k]
                f = fnt(file, px)
                d.text((x, y), c, font=f, fill=col + (255,), anchor="lm",
                       stroke_width=max(1, round(px * min(stroke, 0.15) * 0.9)), stroke_fill=(0, 0, 0, 255))
                x += f.getlength(c)
            x += fnt(per_char[pos][2], per_char[pos][1]).getlength(" ")
    return img


def vol_expr(seg: dict, base: float) -> str:
    """ffmpeg volume expression from the segment's volume keyframes (time in seconds from segment start)."""
    kfs = [k for ck in seg.get("common_keyframes", []) if ck.get("property_type") == "KFTypeVolume"
           for k in ck["keyframe_list"]]
    if not kfs:
        return f"{base:.4f}"
    pts = sorted((sec(k["time_offset"]), k["values"][0]) for k in kfs)
    expr = f"{pts[-1][1]:.4f}"
    for (t0, v0), (t1, v1) in reversed(list(zip(pts, pts[1:]))):
        expr = f"if(lt(t,{t1:.3f}),{v0:.4f}+({v1 - v0:.4f})*(t-{t0:.3f})/{max(t1 - t0, 1e-3):.3f},{expr})"
    return f"if(lt(t,{pts[0][0]:.3f}),{pts[0][1]:.4f},{expr})"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("out", type=Path)
    ap.add_argument("--height", type=int, default=1280)
    a = ap.parse_args()
    d = json.loads((ROOT / a.draft / "draft_content.json").read_text(encoding="utf-8"))
    CW, CH = d["canvas_config"]["width"], d["canvas_config"]["height"]
    H = a.height - a.height % 2
    W = round(CW * H / CH / 2) * 2
    k = W / CW                       # canvas pixels -> output pixels
    total = sec(d["duration"])
    mats = {m["id"]: m for m in d["materials"]["videos"]}
    auds = {m["id"]: m for m in d["materials"]["audios"]}
    texts = {m["id"]: m for m in d["materials"]["texts"]}
    blurs = {m["id"] for m in d["materials"].get("canvases", []) if m.get("type") == "canvas_blur"}
    unit = graphics.px_per_size(CW, CH)

    tmp = Path(tempfile.mkdtemp(prefix="preview_"))
    inputs, fc, vlabels, alabels = [], [], [], []

    def add_input(*args) -> int:
        inputs.extend(args)
        return sum(1 for x in inputs if x == "-i") - 1

    fc.append(f"color=c=black:s={W}x{H}:r={FPS}:d={total:.3f}[bg0]")
    cur = "bg0"
    n = 0
    video_tracks = [t for t in d["tracks"] if t["type"] == "video"]
    for ti, tr in enumerate(video_tracks):
        for s in tr["segments"]:
            m = mats.get(s["material_id"])
            if not m:
                continue
            a0, dur = sec(s["target_timerange"]["start"]), sec(s["target_timerange"]["duration"])
            src = s.get("source_timerange") or {"start": 0, "duration": s["target_timerange"]["duration"]}
            speed = s.get("speed", 1.0) or 1.0
            path = Path(m["path"])
            if path.suffix.lower() in IMAGE_EXT:
                i = add_input("-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(path))
                chain = f"[{i}:v]"
            else:
                i = add_input("-ss", f"{sec(src['start']):.3f}", "-t", f"{sec(src['duration']) + 0.1:.3f}", "-i", str(path))
                chain = f"[{i}:v]setpts=(PTS-STARTPTS)/{speed},"
                if ti == 0 and s.get("volume", 1.0) > 0:  # the clip's own sound
                    alabels.append((i, a0, dur, vol_expr(s, s.get("volume", 1.0)), speed))
            mw, mh = m.get("width") or 1920, m.get("height") or 1080
            clip = s.get("clip") or {}
            sc = (clip.get("scale") or {}).get("x", 1.0)
            fit = min(CW / mw, CH / mh)
            w, h = max(2, round(mw * fit * sc * k / 2) * 2), max(2, round(mh * fit * sc * k / 2) * 2)
            rot = round(clip.get("rotation", 0.0)) % 360  # CapCut turns clockwise
            turn = {90: ",transpose=1", 180: ",hflip,vflip", 270: ",transpose=2"}.get(rot, "")
            tx, ty = (clip.get("transform") or {}).get("x", 0.0), (clip.get("transform") or {}).get("y", 0.0)
            ow, oh = (h, w) if rot in (90, 270) else (w, h)
            x, y = round(W / 2 + tx * W / 2 - ow / 2), round(H / 2 - ty * H / 2 - oh / 2)
            sat = any(ck.get("property_type") == "KFTypeSaturation" for ck in s.get("common_keyframes", []))
            body = f"fps={FPS},scale={w}:{h}" + turn + (",hue=s=0" if sat else "") + f",format=yuva420p,trim=0:{dur:.3f},setpts=PTS-STARTPTS+{a0:.3f}/TB"
            if ti == 0 and any(r in blurs for r in s.get("extra_material_refs", [])):
                f2 = max(W / mw, H / mh)
                fc.append(f"{chain}split[v{n}a][v{n}b]")
                fc.append(f"[v{n}a]fps={FPS},scale={round(mw * f2 / 2) * 2}:{round(mh * f2 / 2) * 2},crop={W}:{H},"
                          f"boxblur=30:3,trim=0:{dur:.3f},setpts=PTS-STARTPTS+{a0:.3f}/TB[bl{n}]")
                fc.append(f"[{cur}][bl{n}]overlay=0:0:eof_action=pass:enable='between(t,{a0:.3f},{a0 + dur:.3f})'[c{n}x]")
                cur = f"c{n}x"
                chain = f"[v{n}b]"
            fc.append(f"{chain}{body}[v{n}]")
            px = [k for ck in s.get("common_keyframes", []) if ck.get("property_type") == "KFTypePositionX"
                  for k in ck["keyframe_list"]]
            if len(px) >= 2:  # a pan: x moves linearly between the first and last keyframe
                (t0k, x0k), (t1k, x1k) = [(sec(k["time_offset"]), k["values"][0]) for k in (px[0], px[-1])]
                xa, xb = W / 2 + x0k * W / 2 - ow / 2, W / 2 + x1k * W / 2 - ow / 2
                x = f"'{xa:.1f}+({xb - xa:.1f})*min(max((t-{a0 + t0k:.3f})/{max(t1k - t0k, 1e-3):.3f},0),1)'"
            fc.append(f"[{cur}][v{n}]overlay={x}:{y}:eof_action=pass:enable='between(t,{a0:.3f},{a0 + dur:.3f})'[c{n}]")
            cur = f"c{n}"
            n += 1
    # texts, in track order (captions under overlay text)
    for tr in [t for t in d["tracks"] if t["type"] == "text"]:
        for s in tr["segments"]:
            m = texts.get(s["material_id"])
            if not m:
                continue
            a0, dur = sec(s["target_timerange"]["start"]), sec(s["target_timerange"]["duration"])
            content = json.loads(m["content"])
            clip = s.get("clip") or {}
            sc = (clip.get("scale") or {}).get("x", 1.0)
            pic = text_picture(content, m.get("line_max_width", 0.82) * W, unit * k, sc)
            png = tmp / f"t{n}.png"
            pic.save(png)
            tx, ty = (clip.get("transform") or {}).get("x", 0.0), (clip.get("transform") or {}).get("y", 0.0)
            x, y = round(W / 2 + tx * W / 2 - pic.width / 2), round(H / 2 - ty * H / 2 - pic.height / 2)
            i = add_input("-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(png))
            fc.append(f"[{i}:v]format=rgba,setpts=PTS-STARTPTS+{a0:.3f}/TB[v{n}]")
            fc.append(f"[{cur}][v{n}]overlay={x}:{y}:eof_action=pass:enable='between(t,{a0:.3f},{a0 + dur:.3f})'[c{n}]")
            cur = f"c{n}"
            n += 1
    fc.append(f"[{cur}]format=yuv420p[vout]")
    # audio
    amix = []
    for j, (i, a0, dur, ve, speed) in enumerate(alabels):
        tempo = f",atempo={speed}" if abs(speed - 1) > 1e-3 else ""
        fc.append(f"[{i}:a]asetpts=PTS-STARTPTS{tempo},atrim=0:{dur:.3f},volume='{ve}':eval=frame,"
                  f"adelay={round(a0 * 1000)}:all=1[a{j}]")
        amix.append(f"[a{j}]")
    for tr in [t for t in d["tracks"] if t["type"] == "audio"]:
        for s in tr["segments"]:
            m = auds.get(s["material_id"])
            if not m:
                continue
            a0, dur = sec(s["target_timerange"]["start"]), sec(s["target_timerange"]["duration"])
            src = s.get("source_timerange") or {"start": 0}
            i = add_input("-ss", f"{sec(src['start']):.3f}", "-t", f"{dur + 0.05:.3f}", "-i", m["path"])
            j = len(amix)
            fc.append(f"[{i}:a]asetpts=PTS-STARTPTS,atrim=0:{dur:.3f},volume='{vol_expr(s, s.get('volume', 1.0))}':eval=frame,"
                      f"adelay={round(a0 * 1000)}:all=1[a{j}]")
            amix.append(f"[a{j}]")
    fc.append(f"{''.join(amix)}amix=inputs={len(amix)}:normalize=0:duration=longest,atrim=0:{total:.3f},"
              f"alimiter=limit=0.95[aout]")
    script = tmp / "graph.txt"
    script.write_text(";\n".join(fc), encoding="utf-8")
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-/filter_complex", str(script), "-map", "[vout]", "-map", "[aout]",
           "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(a.out)]
    subprocess.run(cmd, check=True)
    print(a.out, f"{a.out.stat().st_size / 1e6:.1f} MB, {total:.1f} s")


if __name__ == "__main__":
    main()
