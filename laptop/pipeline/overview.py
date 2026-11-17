#!/usr/bin/env python3
"""Stage 2c: one compact overview of a footage folder, for the stage-3 selection pass.

Writes into the folder:
  - overview.md          every clip in filming order: length, camera, speech status and
                         phrase-level lines with exact start/end times (from the word-level
                         transcript), with unreliable timings flagged ⚠
  - storyboard_N.jpg     frame sheets: 6 frames per talking clip, more for b-roll clips

Reading overview.md + the storyboard pages is all stage 3 needs: no follow-up lookups.
"""

import argparse
import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from extract_audio import find_videos

LONG_EVENT = 15.0   # an audio-event tag longer than this makes following word times suspect
FRAME_W, FRAME_H = 320, 180
COLS = 6
ROWS_PER_PAGE = 8


def probe(video: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "0", "-print_format", "json", "-show_format", "-show_streams", str(video)],
        capture_output=True, text=True,
    ).stdout
    data = json.loads(out or "{}")
    fmt = data.get("format", {})
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    rotation = 0
    for sd in v.get("side_data_list", []):
        rotation = int(sd.get("rotation", rotation) or 0)
    created = (fmt.get("tags", {}).get("creation_time") or v.get("tags", {}).get("creation_time") or "")
    return {
        "duration": float(fmt.get("duration", 0) or 0),
        "size": f'{v.get("width", "?")}x{v.get("height", "?")}' + (" portrait" if abs(rotation) == 90 else ""),
        "created": created[:19].replace("T", " "),
        "has_audio": any(s.get("codec_type") == "audio" for s in data.get("streams", [])),
    }


def clip_id(stem: str) -> str:
    """Short unique label: the clip counter for DJI names (DJI_<time>_0006_D -> 0006), else the stem's tail."""
    if stem.startswith(("DJI", "4")):
        parts = stem.split("_")
        return next((p for p in reversed(parts) if p.isdigit()), parts[-1])
    return stem[-6:]


def phrases(words: list[dict]) -> list[str]:
    """Group words into short phrases: break on pauses >0.7s, speaker change or sentence end."""
    lines, cur, suspect_from, prev_tiny = [], None, float("-inf"), False

    def flush():
        if cur and cur["text"].strip():
            flag = " ⚠" if cur["suspect"] else ""
            spk = f' {cur["spk"][-1]}' if cur["multi"] else ""
            lines.append(f'{cur["start"]:7.2f}-{cur["end"]:7.2f}{spk} {cur["text"].strip()}{flag}')

    speakers = {w.get("speaker_id") for w in words if w["type"] == "word"}
    for w in words:
        if w["type"] == "spacing":
            continue
        dur = w["end"] - w["start"]
        if w["type"] == "audio_event" and dur > LONG_EVENT:
            flush()
            lines.append(f'{w["start"]:7.2f}-{w["end"]:7.2f} {w["text"]} ({dur:.0f}s)')
            cur, suspect_from = None, w["end"]
            continue
        # squashed words come in clusters; one zero-length word on its own is harmless
        tiny = w["type"] == "word" and dur < 0.02
        suspect = (tiny and prev_tiny) or (0 <= w["start"] - suspect_from < 3.0)
        prev_tiny = tiny
        brk = cur and (w["start"] - cur["end"] > 0.7 or w.get("speaker_id") != cur["spk"]
                       or cur["text"].rstrip().endswith((".", "?", "!")))
        if cur is None or brk:
            flush()
            cur = {"start": w["start"], "end": w["end"], "spk": w.get("speaker_id", "s0"),
                   "text": w["text"], "suspect": suspect, "multi": len(speakers) > 1}
        else:
            cur["text"] += " " + w["text"]
            cur["end"] = w["end"]
            cur["suspect"] |= suspect
    flush()
    return lines


def grab_frame(video: Path, t: float, out: Path) -> bool:
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video),
                        "-frames:v", "1", "-vf", f"scale={FRAME_W}:{FRAME_H}:force_original_aspect_ratio=decrease,"
                        f"pad={FRAME_W}:{FRAME_H}:(ow-iw)/2:(oh-ih)/2", str(out)])
    return r.returncode == 0 and out.exists()


def storyboard(folder: Path, clips: list[dict]) -> list[Path]:
    font = ImageFont.load_default()
    rows: list[list[tuple[Path, str]]] = []
    with tempfile.TemporaryDirectory() as tmp:
        for c in clips:
            n = 6 if c["speech"] else min(12, max(6, round(c["duration"] / 20)))
            times = [c["duration"] * (i + 0.5) / n for i in range(n)]
            frames = []
            for i, t in enumerate(times):
                f = Path(tmp) / f'{c["id"]}_{i}.jpg'
                if grab_frame(c["path"], t, f):
                    frames.append((f, f'{c["id"]} @{t:.0f}s'))
            for i in range(0, len(frames), COLS):
                rows.append(frames[i:i + COLS])

        pages = []
        for p in range(0, len(rows), ROWS_PER_PAGE):
            page_rows = rows[p:p + ROWS_PER_PAGE]
            sheet = Image.new("RGB", (FRAME_W * COLS, FRAME_H * len(page_rows)), "black")
            draw = ImageDraw.Draw(sheet)
            for r, row in enumerate(page_rows):
                for col, (f, label) in enumerate(row):
                    x, y = col * FRAME_W, r * FRAME_H
                    sheet.paste(Image.open(f), (x, y))
                    draw.rectangle([x, y, x + 7 * len(label) + 8, y + 14], fill="black")
                    draw.text((x + 4, y + 2), label, fill="yellow", font=font)
            out = folder / f"storyboard_{len(pages) + 1}.jpg"
            sheet.save(out, quality=80)
            pages.append(out)
    return pages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--no-subfolders", action="store_true")
    parser.add_argument("--no-storyboard", action="store_true")
    args = parser.parse_args()

    clips = []
    for video in find_videos(args.folder, recursive=not args.no_subfolders):
        info = probe(video)
        speech_json = video.with_suffix(".speech.json")
        el_json = video.with_suffix(".elevenlabs.json")
        speech = el_json.exists()
        clips.append({
            "path": video, "rel": video.relative_to(args.folder).as_posix(),
            "id": clip_id(video.stem),
            "speech": speech, **info,
            "status": ("speech" if speech else
                       "no audio track" if not info["has_audio"] else
                       "no speech" if speech_json.exists() else "not transcribed"),
            "words": json.loads(el_json.read_text(encoding="utf-8"))["words"] if speech else [],
        })
    clips.sort(key=lambda c: (c["created"] or "9999", c["rel"]))

    lines = [f"# Overview: {args.folder}", "",
             f"{len(clips)} clips, {sum(c['duration'] for c in clips) / 60:.1f} min total. "
             "Filming order (camera creation time; phone clocks may be UTC). "
             "Times are seconds in the source clip. ⚠ = word timings unreliable there — verify the cut.", ""]
    broll = [c for c in clips if not c["speech"]]
    if broll:
        lines += ["## B-roll (no speech)", ""]
        lines += [f'- `{c["rel"]}` [{c["id"]}] {c["duration"]:.0f}s, {c["size"]}, {c["status"]}' for c in broll]
        lines.append("")
    for c in clips:
        if not c["speech"]:
            continue
        lines += [f'## `{c["rel"]}` [{c["id"]}]',
                  f'{c["duration"]:.0f}s, {c["size"]}, filmed {c["created"] or "?"}', ""]
        lines += phrases(c["words"])
        lines.append("")
    out = args.folder / "overview.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")

    if not args.no_storyboard:
        for page in storyboard(args.folder, clips):
            print(f"wrote {page}")


if __name__ == "__main__":
    main()
