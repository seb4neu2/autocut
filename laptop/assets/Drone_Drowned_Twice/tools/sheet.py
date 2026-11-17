"""Contact sheet of chosen moments: sheet.py out_prefix "clipkey:t1,t2,..." ...  (clipkey = DJI counter, e.g. 0057)."""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

FOLDER = Path(r"C:\Users\niu\Desktop\How did i destroy my first done")
W, H, COLS, ROWS = 320, 180, 8, 6


def find(key: str) -> Path:
    return next(FOLDER.glob(f"*_{key}_D.MP4"))


out_prefix = sys.argv[1]
shots = []
for spec in sys.argv[2:]:
    key, times = spec.split(":")
    shots += [(key, float(t)) for t in times.split(",")]

with tempfile.TemporaryDirectory() as tmp:
    tiles = []
    for i, (key, t) in enumerate(shots):
        f = Path(tmp) / f"{i}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(find(key)), "-frames:v", "1",
                        "-vf", f"scale={W}:{H}", "-pix_fmt", "yuvj420p", str(f)])
        if f.exists():
            tiles.append((Image.open(f).copy(), f"{key} @{t:g}"))
    per = COLS * ROWS
    for p in range(0, len(tiles), per):
        page = tiles[p:p + per]
        sheet = Image.new("RGB", (W * COLS, H * ((len(page) + COLS - 1) // COLS)), "black")
        d = ImageDraw.Draw(sheet)
        for n, (img, label) in enumerate(page):
            x, y = (n % COLS) * W, (n // COLS) * H
            sheet.paste(img, (x, y))
            d.rectangle([x, y, x + 7 * len(label) + 8, y + 14], fill="black")
            d.text((x + 4, y + 2), label, fill="yellow")
        out = f"{out_prefix}_{p // per + 1}.jpg"
        sheet.save(out, quality=82)
        print(out)
