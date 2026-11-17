#!/usr/bin/env python3
"""Stage 1: extract audio from every video in a folder (and its subfolders) to a same-named .mp3."""

import argparse
import subprocess
import sys
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def find_videos(folder: Path, recursive: bool = True) -> list[Path]:
    files = folder.rglob("*") if recursive else folder.iterdir()
    return sorted(p for p in files if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS)


def has_audio(video: Path) -> bool:
    out = subprocess.run(
        ["ffprobe", "-v", "0", "-select_streams", "a", "-show_entries", "stream=index",
         "-of", "csv=p=0", str(video)],
        capture_output=True, text=True,
    ).stdout.strip()
    return bool(out)


def extract_one(video: Path, mp3: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video),
            "-vn", "-ac", "1", "-q:a", "4",
            str(mp3),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Folder containing source videos")
    parser.add_argument("--force", action="store_true", help="Re-extract even if mp3 already exists and is newer")
    parser.add_argument("--no-subfolders", action="store_true", help="Only process videos directly in the folder")
    args = parser.parse_args()

    videos = find_videos(args.folder, recursive=not args.no_subfolders)
    if not videos:
        print(f"No video files found in {args.folder}", file=sys.stderr)
        return

    for video in videos:
        mp3 = video.with_suffix(".mp3")
        name = video.relative_to(args.folder)
        if mp3.exists() and not args.force and mp3.stat().st_mtime >= video.stat().st_mtime:
            print(f"skip  {name.with_suffix('.mp3')} (up to date)")
            continue
        if not has_audio(video):
            print(f"skip  {name} (no audio track — b-roll)")
            continue
        print(f"audio {name} -> {mp3.name}")
        try:
            extract_one(video, mp3)
        except subprocess.CalledProcessError as e:
            print(f"  ffmpeg failed on {name}: {e.stderr.decode(errors='replace')[-500:]}", file=sys.stderr)


if __name__ == "__main__":
    main()
