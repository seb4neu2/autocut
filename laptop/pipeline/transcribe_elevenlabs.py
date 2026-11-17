#!/usr/bin/env python3
"""Stage 2b (optional, paid): transcribe each .mp3 via the ElevenLabs Speech-to-Text API.

Produces, per audio file:
  - name.elevenlabs.json   raw API response (word-level timestamps, speaker ids, audio-event tags)
  - name.elevenlabs.txt    human/LLM-readable transcript, grouped into speaker-labeled segments

When name.elevenlabs.json exists next to a video, later stages prefer it over the
free faster-whisper output (name.txt / name.words.json): stage 3 (selection) should
read name.elevenlabs.txt instead of name.txt when present, and build_draft.py (stage 4)
automatically prefers it for cut-point snapping.

Costs real money per run — skips files already transcribed unless --force is passed.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

API_URL = "https://api.elevenlabs.io/v1/speech-to-text"


def load_api_key() -> str:
    load_dotenv(Path(__file__).parent / ".env")
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise SystemExit("Set ELEVENLABS_API_KEY in pipeline/.env or the environment")
    return key


def transcribe_one(api_key: str, mp3: Path, model: str) -> dict:
    with open(mp3, "rb") as f:
        resp = requests.post(
            API_URL,
            headers={"xi-api-key": api_key},
            data={
                "model_id": model,
                "diarize": "true",
                "tag_audio_events": "true",
                "timestamps_granularity": "word",
            },
            files={"file": (mp3.name, f, "audio/mpeg")},
            timeout=600,
        )
    resp.raise_for_status()
    return resp.json()


def speech_regions(mp3: Path, merge_gap: float = 1.0, pad: float = 0.5) -> list[tuple[float, float]]:
    """Voice regions of an audio file (seconds), found with the Silero VAD that ships with faster-whisper."""
    from faster_whisper.audio import decode_audio
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    audio = decode_audio(str(mp3))
    opts = VadOptions(threshold=0.35, min_silence_duration_ms=800, speech_pad_ms=int(pad * 1000))
    regions: list[list[float]] = []
    for ts in get_speech_timestamps(audio, opts):
        s, e = ts["start"] / 16000, ts["end"] / 16000
        if regions and s - regions[-1][1] < merge_gap:
            regions[-1][1] = e
        else:
            regions.append([s, e])
    return [(s, e) for s, e in regions], audio


def transcribe_speech_only(api_key: str, mp3: Path, model: str, gap: float = 0.4) -> dict:
    """Send only the voice parts of mp3 (joined by short silences) and map the word times back.

    Cheaper (breathing, walking and wind aren't billed) and more accurate: long
    non-speech stretches are what break ElevenLabs' word alignment."""
    import subprocess
    import tempfile
    import wave

    import numpy as np

    regions, audio = speech_regions(mp3)
    if not regions:
        return {"words": [], "speech_only": True, "regions": []}
    silence = np.zeros(int(gap * 16000), dtype=np.float32)
    parts, spans, t = [], [], 0.0  # spans: (new_start, new_end, orig_start)
    for s, e in regions:
        chunk = audio[int(s * 16000):int(e * 16000)]
        spans.append((t, t + len(chunk) / 16000, s))
        parts += [chunk, silence]
        t += (len(chunk) + len(silence)) / 16000

    def to_orig(x: float) -> float:
        for ns, ne, os_ in spans:
            if x <= ne + gap / 2:
                return os_ + min(max(x - ns, 0.0), ne - ns)
        ns, ne, os_ = spans[-1]
        return os_ + (ne - ns)

    with tempfile.TemporaryDirectory() as tmp:
        wav, packed = Path(tmp) / "speech.wav", Path(tmp) / "speech.mp3"
        pcm = (np.clip(np.concatenate(parts), -1, 1) * 32767).astype(np.int16)
        with wave.open(str(wav), "wb") as f:
            f.setnchannels(1), f.setsampwidth(2), f.setframerate(16000), f.writeframes(pcm.tobytes())
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-q:a", "4", str(packed)], check=True)
        data = transcribe_one(api_key, packed, model)

    for w in data.get("words", []):
        w["start"], w["end"] = to_orig(w["start"]), to_orig(w["end"])
    data["speech_only"] = True
    data["regions"] = [[round(s, 2), round(e, 2)] for s, e in regions]
    data["billed_seconds"] = round(t, 1)
    return data


def to_segments(words: list[dict], gap_threshold: float = 1.2) -> list[dict]:
    """Group the flat word list into speaker-labeled segments, breaking on a
    speaker change or a pause longer than gap_threshold seconds."""
    segments: list[dict] = []
    cur: dict | None = None
    for w in words:
        speaker = w.get("speaker_id", "speaker_0")
        if cur is not None and (speaker != cur["speaker"] or w["start"] - cur["end"] > gap_threshold):
            segments.append(cur)
            cur = None
        if cur is None:
            cur = {"speaker": speaker, "start": w["start"], "end": w["end"], "text": w["text"]}
        else:
            cur["text"] += w["text"]
            cur["end"] = w["end"]
    if cur is not None:
        segments.append(cur)
    return segments


def fmt(t: float) -> str:
    m, s = divmod(t, 60)
    return f"{int(m):02d}:{s:06.3f}"


def write_txt(data: dict, txt_path: Path) -> None:
    segments = to_segments(data.get("words", []))
    lines = []
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        lines.append(f"[{fmt(seg['start'])} -> {fmt(seg['end'])}] {seg['speaker']}: {text}")
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Folder containing .mp3 files")
    parser.add_argument("--model", default="scribe_v2", help="ElevenLabs STT model_id")
    parser.add_argument("--force", action="store_true", help="Re-transcribe even if .elevenlabs.json already exists and is newer")
    parser.add_argument("--no-subfolders", action="store_true", help="Only process .mp3 files directly in the folder")
    args = parser.parse_args()

    api_key = load_api_key()
    mp3s = sorted(args.folder.glob("*.mp3") if args.no_subfolders else args.folder.rglob("*.mp3"))
    if not mp3s:
        print(f"No .mp3 files found in {args.folder}", file=sys.stderr)
        return

    for mp3 in mp3s:
        json_path = mp3.with_suffix(".elevenlabs.json")
        txt_path = mp3.with_suffix(".elevenlabs.txt")
        if json_path.exists() and not args.force and json_path.stat().st_mtime >= mp3.stat().st_mtime:
            print(f"skip  {json_path.name} (up to date)")
            continue
        print(f"transcribe (ElevenLabs) {mp3.name} -> {json_path.name}")
        try:
            data = transcribe_one(api_key, mp3, args.model)
        except requests.HTTPError as e:
            print(f"  ElevenLabs API failed on {mp3.name}: {e.response.status_code} {e.response.text[:500]}", file=sys.stderr)
            continue
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        write_txt(data, txt_path)


if __name__ == "__main__":
    main()
