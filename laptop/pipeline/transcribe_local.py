#!/usr/bin/env python3
"""Stage 2 (alternative, free): transcribe each .mp3 in a folder fully locally with faster-whisper.

The default stage 2 is transcribe.py (local speech check + ElevenLabs); use this
instead when you don't want to pay for ElevenLabs.

Produces, per audio file:
  - name.txt         human-readable, segment-level timestamps (what the LLM/you read)
  - name.words.json  per-word timestamps sidecar (used only for precise cut snapping)
"""

import argparse
import json
import sys
from pathlib import Path

from faster_whisper import WhisperModel


def fmt(t: float) -> str:
    m, s = divmod(t, 60)
    return f"{int(m):02d}:{s:06.3f}"


def transcribe_one(model: WhisperModel, mp3: Path, txt: Path, words_json: Path) -> None:
    segments, _info = model.transcribe(str(mp3), word_timestamps=True, vad_filter=True)

    lines = []
    words = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        lines.append(f"[{fmt(seg.start)} -> {fmt(seg.end)}] {text}")
        for w in (seg.words or []):
            words.append({"word": w.word.strip(), "start": w.start, "end": w.end})

    txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    words_json.write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Folder containing .mp3 files")
    parser.add_argument("--model", default="large-v3-turbo", help="faster-whisper model size/name")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--force", action="store_true", help="Re-transcribe even if .txt already exists and is newer")
    parser.add_argument("--no-subfolders", action="store_true", help="Only process .mp3 files directly in the folder")
    args = parser.parse_args()

    mp3s = sorted(args.folder.glob("*.mp3") if args.no_subfolders else args.folder.rglob("*.mp3"))
    if not mp3s:
        print(f"No .mp3 files found in {args.folder}", file=sys.stderr)
        return

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    for mp3 in mp3s:
        txt = mp3.with_suffix(".txt")
        words_json = mp3.with_suffix(".words.json")
        if txt.exists() and not args.force and txt.stat().st_mtime >= mp3.stat().st_mtime:
            print(f"skip  {txt.name} (up to date)")
            continue
        print(f"transcribe {mp3.name} -> {txt.name}")
        transcribe_one(model, mp3, txt, words_json)


if __name__ == "__main__":
    main()
