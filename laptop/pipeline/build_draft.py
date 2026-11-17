#!/usr/bin/env python3
"""Stage 4: turn an edl.json into a CapCut draft (no cutting, no re-encoding).

Each EDL entry becomes a VideoSegment trimmed from the original source file
(source_timerange), placed back-to-back on one timeline track in EDL order
(target_timerange). When path_mappings in config.yaml is non-empty (pipeline
on Linux, CapCut on Windows), the source path stored in the draft is rewritten
from the Linux mount path to the Windows path CapCut will see; otherwise the
real local path is used as-is.

An entry of the form {"placeholder": "B-ROLL: drone reveal", "duration": 5}
becomes a dark title card with that text burned in, reserving the slot on the
timeline: in CapCut, right-click it -> Replace to drop the real footage in at
the same length.
"""

import argparse
import json
import subprocess
from bisect import bisect_left
from pathlib import Path

import yaml
import pycapcut as cc

SNAP_TOLERANCE = 0.35  # only snap to a word boundary this close (seconds)
PAD_BEFORE = 0.10      # breathing room so the first word's attack isn't clipped
PAD_AFTER = 0.25       # ...and the last word's tail isn't chopped
FONT_FILE = "C:/Windows/Fonts/arialbd.ttf"


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def to_windows_path(linux_path: Path, mappings: list[dict]) -> str:
    resolved = str(linux_path.resolve())
    if not mappings:
        return resolved
    for m in mappings:
        prefix = m["linux_prefix"].rstrip("/")
        if resolved.startswith(prefix):
            rest = resolved[len(prefix):].lstrip("/")
            win_prefix = m["windows_prefix"]
            if not win_prefix.endswith("\\"):
                win_prefix += "\\"
            return win_prefix + rest.replace("/", "\\")
    raise ValueError(f"No path mapping in config.yaml covers: {resolved}")


def detect_video(video_path: Path) -> tuple[int, int, int]:
    """Return (width, height, fps) of the first video stream; falls back to 1920x1080@30."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "0", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0", str(video_path)],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        # ffprobe may print the stream line more than once (e.g. DJI files) — use the first
        width, height, rate = out.splitlines()[0].split(",")[:3]
        num, den = rate.split("/")
        return int(width), int(height), round(int(num) / int(den))
    except Exception:
        return 1920, 1080, 30


def load_words(video_path: Path) -> list[dict]:
    """Load word-level timestamps for a video's transcript, preferring the paid
    ElevenLabs output (name.elevenlabs.json) over the free whisper one (name.words.json)."""
    elevenlabs_json = video_path.with_suffix(".elevenlabs.json")
    if elevenlabs_json.exists():
        data = json.loads(elevenlabs_json.read_text(encoding="utf-8"))
        return [
            {"start": w["start"], "end": w["end"]}
            for w in data.get("words", [])
            if w.get("type") == "word"
        ]
    words_json = video_path.with_suffix(".words.json")
    if not words_json.exists():
        return []
    return json.loads(words_json.read_text(encoding="utf-8"))


def snap(t: float, words: list[dict], key: str) -> float:
    """Snap timestamp t to the nearest word boundary (word start or end), if one is close."""
    if not words:
        return t
    boundaries = sorted(w[key] for w in words)
    i = bisect_left(boundaries, t)
    candidates = [b for b in (boundaries[i - 1] if i > 0 else None,
                              boundaries[i] if i < len(boundaries) else None) if b is not None]
    if not candidates:
        return t
    best = min(candidates, key=lambda b: abs(b - t))
    return best if abs(best - t) <= SNAP_TOLERANCE else t


def ffmpeg_filter_path(p: Path) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def make_placeholder(text: str, duration: float, out: Path) -> None:
    """Render a dark 1080p title card with `text` burned in (CapCut scales it to the canvas)."""
    text_file = out.with_suffix(".txt")
    text_file.write_text(text, encoding="utf-8")
    drawtext = (f"drawtext=fontfile='{ffmpeg_filter_path(Path(FONT_FILE))}'"
                f":textfile='{ffmpeg_filter_path(text_file)}':text_align=C"
                ":fontcolor=0xFFD54A:fontsize=54:line_spacing=18"
                ":x=(w-text_w)/2:y=(h-text_h)/2")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", f"color=c=0x1c1c1c:s=1920x1080:r=30:d={duration + 0.5:.3f}",
         "-vf", drawtext, "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(out)],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("edl", type=Path, help="Path to edl.json")
    parser.add_argument("videos_dir", type=Path, help="Folder containing the source videos + transcripts")
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "config.yaml")
    parser.add_argument("--draft-name", default="autocut")
    parser.add_argument("--replace", action="store_true",
                        help="Overwrite an existing draft with the same name (deletes it first)")
    args = parser.parse_args()

    config = load_config(args.config)
    mappings = config.get("path_mappings") or []
    draft_output_dir = Path(config["draft_output_dir"]).expanduser()
    draft_output_dir.mkdir(parents=True, exist_ok=True)
    placeholder_dir = Path(config.get("placeholder_dir") or Path(__file__).parent.parent / "placeholders")
    placeholder_dir = placeholder_dir.expanduser() / args.draft_name

    entries = json.loads(args.edl.read_text(encoding="utf-8"))
    if not entries:
        raise SystemExit("edl.json is empty")

    first_source = next(e["source"] for e in entries if "source" in e)
    src_width, src_height, fps = detect_video(args.videos_dir / first_source)
    width = config.get("video_width") or src_width
    height = config.get("video_height") or src_height

    folder = cc.DraftFolder(str(draft_output_dir))
    try:
        script = folder.create_draft(args.draft_name, width, height, fps, allow_replace=args.replace)
    except FileExistsError:
        raise SystemExit(f"A draft named '{args.draft_name}' already exists in {draft_output_dir}. "
                         "Pick another --draft-name, or pass --replace to overwrite it.")
    script.add_track(cc.TrackType.video)

    materials: dict[str, cc.VideoMaterial] = {}
    words_cache: dict[str, list[dict]] = {}
    cursor = 0.0
    placeholders = 0

    for entry in entries:
        if "placeholder" in entry:
            duration = float(entry["duration"])
            placeholder_dir.mkdir(parents=True, exist_ok=True)
            ph_path = placeholder_dir / f"placeholder_{entry.get('clip', placeholders + 1):03}.mp4"
            make_placeholder(entry["placeholder"], duration, ph_path)
            material = cc.VideoMaterial(str(ph_path))
            material.path = to_windows_path(ph_path, mappings)
            script.add_material(material)
            segment = cc.VideoSegment(material, cc.trange(f"{cursor:.3f}s", f"{duration:.3f}s"),
                                      source_timerange=cc.trange("0s", f"{duration:.3f}s"))
            script.add_segment(segment)
            cursor += duration
            placeholders += 1
            continue

        source_name = entry["source"]
        video_path = args.videos_dir / source_name

        material = materials.get(source_name)
        if material is None:
            material = cc.VideoMaterial(str(video_path))
            material.path = to_windows_path(video_path, mappings)
            script.add_material(material)
            materials[source_name] = material

        if source_name not in words_cache:
            words_cache[source_name] = load_words(video_path)
        words = words_cache[source_name]
        # per-entry pad_before/pad_after override the defaults, e.g. 0 when the next word follows immediately
        start = max(snap(entry["start"], words, "start") - entry.get("pad_before", PAD_BEFORE), 0.0)
        end = min(snap(entry["end"], words, "end") + entry.get("pad_after", PAD_AFTER), material.duration / 1e6)
        duration = max(end - start, 0.01)

        source_range = cc.trange(f"{start:.3f}s", f"{duration:.3f}s")
        target_range = cc.trange(f"{cursor:.3f}s", f"{duration:.3f}s")
        segment = cc.VideoSegment(material, target_range, source_timerange=source_range)
        script.add_segment(segment)

        cursor += duration

    script.save()
    m, s = divmod(cursor, 60)
    print(f"Draft '{args.draft_name}' ({width}x{height} @ {fps}fps, {int(m)}:{s:04.1f}, "
          f"{len(entries) - placeholders} clips + {placeholders} placeholders) written to {draft_output_dir}")
    if mappings:
        print("Copy that draft folder into CapCut's local drafts directory on Windows and open it there.")
    else:
        print("Open CapCut (or restart it if already open) — the draft should be in the project list.")


if __name__ == "__main__":
    main()
