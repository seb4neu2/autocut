#!/usr/bin/env python3
"""Animated route map Buon Ma Thuot -> Dray Nur Waterfall, copied from the Thailand map script.

Inland, so no coastline: land with the real rivers, lakes and main roads from OpenStreetMap
and the real road route (OSRM, 20.9 km), all cached in ../map/data. Start point from Google
Timeline (left the south-west of Buon Ma Thuot at 16:37, at Dray Nur at 17:24, 2026-04-12).
The camera starts close on Buon Ma Thuot and pulls back while the route draws south-west;
a pin drops on the waterfall.

  python make_route_map.py                 4K60 clip without any text (for a CapCut draft)
  python make_route_map.py --labels        same with the labels baked in (to watch on its own)
  python make_route_map.py --width 1920    faster, smaller
  python make_route_map.py --stills 0.5 2.5 4.6 6.5   only save frames at these seconds
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DATA, OUT = HERE.parent / "map" / "data", HERE.parent / "map"
sys.path.insert(0, str(HERE.parents[2] / "pipeline"))
import graphics  # noqa: E402  (font files CapCut uses)

FPS, DURATION = 60, 7.0
T_START, T_ARRIVE = 0.7, 4.3          # the route draws between these seconds
LAT0, LAT1, LON_MID = 12.522, 12.66, 107.947  # final view (the base_map.png cache must be deleted when this changes)
BW, BH = 9600, 5400                   # base map; the opening view is a 1:1 crop of it
LON_SPAN = (LAT1 - LAT0) * 16 / 9 / math.cos(math.radians((LAT0 + LAT1) / 2))
LON0 = LON_MID - LON_SPAN / 2
START_VIEW = (108.0, 12.635)          # lon, lat the opening view is centred on (Buon Ma Thuot)

# BGR
LAND, LAND_HI, RIVER, LAKE, ROAD = (52, 74, 42), (66, 94, 54), (150, 128, 44), (130, 112, 40), (96, 116, 88)
YELLOW, ORANGE, WHITE, DARK = (74, 213, 255), (0, 128, 255), (255, 255, 255), (14, 12, 10)

LABELS = [  # text, anchor point (lon, lat), offset in 4K px, font, size in 4K px, colour RGB, appears at second
    ("BUÔN MA THUỘT", "start", (0, -90), "anton", 150, (255, 255, 255), 0.35, "ms"),
    ("ĐRAY NUR", "end", (-110, -150), "anton", 150, (255, 213, 74), 4.75, "rm"),
    ("WATERFALL", "end", (-112, -20), "bebas", 96, (255, 255, 255), 4.95, "rm"),
    ("21 KM", "frame", (2950, 1620), "anton", 260, (255, 213, 74), 5.2, "mm"),
    ("45 min by scooter", "frame", (2950, 1840), "poppins", 84, (255, 255, 255), 5.4, "mm"),
]


def to_px(lon, lat):
    return (np.asarray(lon) - LON0) / LON_SPAN * BW, (LAT1 - np.asarray(lat)) / (LAT1 - LAT0) * BH


def pts(geom) -> np.ndarray:
    x, y = to_px([p["lon"] for p in geom], [p["lat"] for p in geom])
    return np.stack([x, y], axis=1)


def rings(ways: list[list]) -> list[list]:
    """Join ways that share end points into closed rings."""
    ways, out = [list(w) for w in ways if len(w) > 1], []
    while ways:
        ring = ways.pop()
        while ring[0] != ring[-1]:
            for i, w in enumerate(ways):
                if w[0] == ring[-1]:
                    ring += w[1:]
                elif w[-1] == ring[-1]:
                    ring += w[-2::-1]
                else:
                    continue
                ways.pop(i)
                break
            else:
                break
        out.append(ring)
    return out


def build_base() -> np.ndarray:
    cache = OUT / "base_map.png"
    if cache.exists():
        return cv2.imread(str(cache))
    base = np.empty((BH, BW, 3), np.uint8)
    base[:] = LAND
    # soft light patches so the land is not flat
    rng = np.random.default_rng(7)
    noise = cv2.GaussianBlur(rng.random((BH // 8, BW // 8)).astype(np.float32), (0, 0), 18)
    noise = cv2.resize((noise - noise.min()) / (np.ptp(noise) + 1e-9), (BW, BH))
    for c in range(3):
        base[..., c] = (LAND[c] + (LAND_HI[c] - LAND[c]) * noise).astype(np.uint8)
    roads = json.loads((DATA / "roads.json").read_text(encoding="utf-8"))["elements"]
    for w in roads:
        if "geometry" in w:
            width = {"trunk": 14, "primary": 12, "secondary": 9}.get(w["tags"].get("highway"), 6)
            cv2.polylines(base, [pts(w["geometry"]).round().astype(np.int32)], False, ROAD, width, cv2.LINE_AA)
    water = json.loads((DATA / "rivers.json").read_text(encoding="utf-8"))["elements"]
    for e in water:
        if e["type"] == "way" and e.get("tags", {}).get("waterway") == "river" and "geometry" in e:
            cv2.polylines(base, [pts(e["geometry"]).round().astype(np.int32)], False, RIVER, 18, cv2.LINE_AA)
    for e in water:
        if e.get("tags", {}).get("natural") != "water":
            continue
        if e["type"] == "way" and "geometry" in e:
            cv2.fillPoly(base, [pts(e["geometry"]).round().astype(np.int32)], LAKE, cv2.LINE_AA)
        elif e["type"] == "relation":
            for role, colour in (("outer", LAKE), ("inner", LAND_HI)):
                ways = [[(p["lon"], p["lat"]) for p in m["geometry"]] for m in e.get("members", [])
                        if m.get("role") == role and "geometry" in m]
                polys = [np.stack(to_px(*zip(*r)), axis=1).round().astype(np.int32) for r in rings(ways) if len(r) > 3]
                if polys:
                    cv2.fillPoly(base, polys, colour, cv2.LINE_AA)
    cv2.imwrite(str(cache), base)
    return base


def ease(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def pop(t: float) -> float:
    """0 -> 1 with a small overshoot."""
    t = min(max(t, 0.0), 1.0)
    return 1 + 2.2 * (t - 1) ** 3 + 1.2 * (t - 1) ** 2


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--width", type=int, default=3840)
    ap.add_argument("--labels", action="store_true")
    ap.add_argument("--stills", type=float, nargs="*")
    args = ap.parse_args()
    W, H = args.width, args.width * 9 // 16
    k = W / 3840  # drawing scale

    base = build_base()
    half = cv2.resize(base, (BW // 2, BH // 2), interpolation=cv2.INTER_AREA)
    route_ll = json.loads((DATA / "route.json").read_text(encoding="utf-8"))["routes"][0]["geometry"]["coordinates"]
    route = np.stack(to_px(*zip(*route_ll)), axis=1)
    seg = np.hypot(*np.diff(route, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    start_pt, end_pt = route[0], route[-1]

    sx, sy = to_px(*START_VIEW)
    sx, sy = min(max(sx, 1920), BW - 1920), min(max(sy, 1080), BH - 1080)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vignette = 1 - 0.38 * np.clip((np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)) - 0.55) / 0.9, 0, 1) ** 1.5
    vignette = vignette[..., None]
    fonts = {key: lambda px, key=key: ImageFont.truetype(graphics._text_font_file(key), max(8, int(px))) for key in graphics.TEXT_FONTS}

    def frame(t: float) -> np.ndarray:
        # camera: zoom 1.0 (close on Phuket) -> 2.5 (whole map); zoom = base px per 4K px
        c = ease((t - T_START + 0.15) / (T_ARRIVE - T_START - 0.25))
        z = math.exp(math.log(1.0) + (math.log(2.5) - math.log(1.0)) * c)
        z *= 1 - 0.012 * ease((t - T_ARRIVE) / (DURATION - T_ARRIVE))  # slow push-in while holding
        cx, cy = sx + (BW / 2 - sx) * c, sy + (BH / 2 - sy) * c
        ox, oy = cx - 1920 * z, cy - 1080 * z
        src, zz = (half, z / 2) if z > 1.6 else (base, z)
        f = 2 if src is half else 1
        M = np.array([[zz / k, 0, ox / f], [0, zz / k, oy / f]], np.float32)
        img = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)

        def view(p):
            return (np.asarray(p, np.float64) - (ox, oy)) / z * k

        # route drawn so far
        p = ease((t - T_START) / (T_ARRIVE - T_START))
        dist = p * cum[-1]
        n = int(np.searchsorted(cum, dist, side="right"))
        head = start_pt
        if n >= 1 and p > 0:
            if n < len(route):
                a = (dist - cum[n - 1]) / max(seg[n - 1], 1e-9)
                head = route[n - 1] + (route[n] - route[n - 1]) * a
                line = np.vstack([route[:n], head])
            else:
                head, line = end_pt, route
            poly = (view(line) * 16).round().astype(np.int32)
            glow = np.zeros_like(img)
            cv2.polylines(glow, [poly], False, YELLOW, int(46 * k), cv2.LINE_AA, shift=4)
            img = cv2.addWeighted(img, 1.0, cv2.GaussianBlur(glow, (0, 0), 22 * k), 0.55, 0)
            cv2.polylines(img, [poly], False, DARK, int(30 * k), cv2.LINE_AA, shift=4)
            cv2.polylines(img, [poly], False, YELLOW, int(16 * k), cv2.LINE_AA, shift=4)

        def disc(pt, r, colour, thick=-1):
            x, y = view(pt)
            cv2.circle(img, (int(x * 16), int(y * 16)), int(max(r, 0.1) * k * 16), colour, thick if thick < 0 else max(1, int(thick * k)),
                       cv2.LINE_AA, shift=4)

        # start marker
        s = pop((t - 0.2) / 0.35)
        if t > 0.2:
            disc(start_pt, 40 * s, DARK)
            disc(start_pt, 31 * s, WHITE)
            disc(start_pt, 17 * s, YELLOW)
        # travelling head
        if 0 < p < 1:
            pulse = 0.5 + 0.5 * math.sin(t * 9)
            disc(head, 44 + 16 * pulse, YELLOW, 5)
            disc(head, 30, DARK)
            disc(head, 23, WHITE)
        # arrival: rings and a pin that drops in
        ta = t - T_ARRIVE
        if ta > 0:
            for delay in (0.0, 0.45, 0.9):
                r = (ta - delay) / 1.1
                if 0 < r < 1:
                    x, y = view(end_pt)
                    ov = img.copy()
                    cv2.circle(ov, (int(x), int(y)), int((40 + 230 * r) * k), ORANGE, max(1, int(9 * k)), cv2.LINE_AA)
                    img = cv2.addWeighted(ov, 1 - r, img, r, 0)
            d = min(ta / 0.32, 1.0)
            drop = (1 - d * d) * 520 * k
            bounce = math.sin(min(max((ta - 0.32) / 0.3, 0), 1) * math.pi) * 34 * k
            sq = pop(ta / 0.45)
            x, y = view(end_pt)
            y -= drop + bounce
            R = 62 * k * sq
            tip, centre = (x, y), (x, y - 2.05 * R)
            ang = math.asin(R / (2.05 * R))
            tangents = [(centre[0] + R * math.cos(a), centre[1] + R * math.sin(a))
                        for a in (math.pi / 2 - ang - math.pi / 2 + math.pi / 2, math.pi / 2 + ang)]
            for grow, colour in ((9 * k, DARK), (0, ORANGE)):
                tri = np.array([tip, (centre[0] + (R + grow) * math.cos(ang), centre[1] + (R + grow) * math.sin(ang)),
                                (centre[0] - (R + grow) * math.cos(ang), centre[1] + (R + grow) * math.sin(ang))])
                tri[0, 1] += grow * 1.6
                cv2.fillPoly(img, [(tri * 16).round().astype(np.int32)], colour, cv2.LINE_AA, shift=4)
                cv2.circle(img, (int(centre[0] * 16), int(centre[1] * 16)), int((R + grow) * 16), colour, -1, cv2.LINE_AA, shift=4)
            cv2.circle(img, (int(centre[0] * 16), int(centre[1] * 16)), int(R * 0.42 * 16), WHITE, -1, cv2.LINE_AA, shift=4)

        img = (img.astype(np.float32) * vignette).astype(np.uint8)

        if args.labels:
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dr = ImageDraw.Draw(layer)
            for text, anchor_pt, off, fkey, size, colour, at, anchor in LABELS:
                a = ease((t - at) / 0.3)
                if a <= 0:
                    continue
                ax, ay = (0, 0) if anchor_pt == "frame" else view(start_pt if anchor_pt == "start" else end_pt)
                x, y = ax + off[0] * k, ay + off[1] * k + (1 - a) * 30 * k
                dr.text((x, y), text, font=fonts[fkey](size * k), fill=colour + (int(255 * a),), anchor=anchor,
                        stroke_width=max(2, int(size * k * 0.07)), stroke_fill=(10, 12, 14, int(255 * a)))
            rgba = np.asarray(layer).astype(np.float32)
            al = rgba[..., 3:4] / 255
            img = (img * (1 - al) + rgba[..., 2::-1] * al).astype(np.uint8)
        return img

    if args.stills is not None:
        for t in args.stills:
            cv2.imwrite(str(OUT / f"still_{t:04.1f}s.jpg"), frame(t), [cv2.IMWRITE_JPEG_QUALITY, 88])
        return
    name = f"map_buon-ma-thuot-to-dray-nur_{'with-labels' if args.labels else 'no-text'}_{H}p.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
                           "-movflags", "+faststart", str(OUT / name)], stdin=subprocess.PIPE)
    total = int(DURATION * FPS)
    for i in range(total):
        ff.stdin.write(frame(i / FPS).tobytes())
        if i % 60 == 0:
            print(f"  {i}/{total}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(OUT / name)


if __name__ == "__main__":
    main()
