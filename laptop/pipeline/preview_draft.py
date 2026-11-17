"""Rough preview of a CapCut draft at given times: main video (crop/fit + background blur), overlay
pictures and text boxes at their positions. Layout check only, fonts and effects are approximate.
  python preview_draft.py <draft name> <out.jpg> t1 t2 ...
"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(r"C:\Users\niu\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")
name, out, times = sys.argv[1], sys.argv[2], [float(t) for t in sys.argv[3:]]
d = json.loads((ROOT / name / "draft_content.json").read_text(encoding="utf-8"))
CW, CH = d["canvas_config"]["width"], d["canvas_config"]["height"]
vids = {m["id"]: m for m in d["materials"]["videos"]}
texts = {m["id"]: m for m in d["materials"]["texts"]}
canv = {m["id"]: m for m in d["materials"].get("canvases", [])}
FONT = r"C:\Windows\Fonts\arialbd.ttf"


def grab(path, t):
    p = Path(path)
    if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
        return Image.open(p).convert("RGBA")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(p), "-frames:v", "1", "-f", "image2pipe",
                          "-vcodec", "png", "-"], capture_output=True).stdout
    import io
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def place(img, frame, clip):
    sc = clip.get("scale", {}).get("x", 1.0)
    fit = min(CW / frame.width, CH / frame.height)
    w, h = max(1, int(frame.width * fit * sc)), max(1, int(frame.height * fit * sc))
    tx, ty = clip.get("transform", {}).get("x", 0), clip.get("transform", {}).get("y", 0)
    x = int(CW / 2 + tx * CW / 2 - w / 2); y = int(CH / 2 - ty * CH / 2 - h / 2)
    img.alpha_composite(frame.resize((w, h)), (0, 0)) if False else None
    layer = Image.new("RGBA", (CW, CH)); layer.paste(frame.resize((w, h)), (x, y)); img.alpha_composite(layer)


tiles = []
for t in times:
    us = t * 1e6
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 255))
    drawn_text = []
    for tr in d["tracks"]:
        for s in tr["segments"]:
            a, b = s["target_timerange"]["start"], s["target_timerange"]["start"] + s["target_timerange"]["duration"]
            if not a <= us < b:
                continue
            if tr["type"] == "video" and s["material_id"] in vids:
                m = vids[s["material_id"]]
                src_t = (s.get("source_timerange") or {"start": 0})["start"] / 1e6 + (us - a) / 1e6 * s.get("speed", 1.0)
                fr = grab(m["path"], src_t)
                if any(r in canv and canv[r].get("type") == "canvas_blur" for r in s.get("extra_material_refs", [])):
                    f = max(CW / fr.width, CH / fr.height)
                    bg = fr.resize((int(fr.width * f), int(fr.height * f))).filter(ImageFilter.GaussianBlur(40))
                    img.alpha_composite(bg.crop(((bg.width - CW) // 2, (bg.height - CH) // 2, (bg.width + CW) // 2, (bg.height + CH) // 2)))
                place(img, fr, s["clip"])
            elif tr["type"] == "text" and s["material_id"] in texts:
                m = texts[s["material_id"]]
                c = json.loads(m["content"])
                size = (c.get("styles") or [{}])[0].get("size", 10)
                drawn_text.append((c["text"], size, s["clip"]))
    dr = ImageDraw.Draw(img)
    for txt, size, clip in drawn_text:
        px = int(size * min(CW, CH) / 108 * 0.75)  # cap height ~ size unit; rough
        f = ImageFont.truetype(FONT, max(8, px))
        x = CW / 2 + clip["transform"]["x"] * CW / 2; y = CH / 2 - clip["transform"]["y"] * CH / 2
        dr.multiline_text((x, y), txt, font=f, fill=(255, 230, 80, 255), anchor="mm", align="center",
                          stroke_width=max(2, px // 12), stroke_fill=(0, 0, 0, 255))
    dr.text((10, 10), f"{t:.1f}s", font=ImageFont.truetype(FONT, 40), fill=(0, 255, 0, 255))
    tiles.append(img.convert("RGB").resize((CW // 3, CH // 3)))
cols = min(6, len(tiles)); rows = -(-len(tiles) // cols)
sheet = Image.new("RGB", (cols * tiles[0].width + (cols - 1) * 6, rows * tiles[0].height + (rows - 1) * 6), (40, 40, 40))
for i, tl in enumerate(tiles):
    sheet.paste(tl, ((i % cols) * (tl.width + 6), (i // cols) * (tl.height + 6)))
sheet.save(out, quality=88)
print(out)
