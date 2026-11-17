#!/usr/bin/env python3
"""Stage 4a: check every dialogue cut of an edit plan by re-transcribing exactly what it plays.

Sends the audio of all not-yet-verified clips to ElevenLabs in one request (joined by
silences), then:
  - saves the heard words per cut (times relative to the cut) to assets/<name>/cutwords.json,
    which build_plan.py uses for captions and bleeps — accurate even where the source
    transcript's timings were broken
  - prints only the cuts whose audio doesn't match the plan's "text"

Local whisper is not used here on purpose: it hallucinates on breathing/grunting audio.
Cached per cut, so re-running after edits only pays for changed clips (~2 credits/10 s).
"""

import argparse
import difflib
import json
import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from faster_whisper.audio import decode_audio

import assets
from build_plan import clip_range, cut_key
from transcribe_elevenlabs import load_api_key, transcribe_one

GAP = 2.5


def norm(text: str) -> str:
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)|^[A-Z -]+:", " ", text)
    return " ".join(re.sub(r"[^\w' ]", " ", text.lower()).split())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("videos_dir", type=Path)
    parser.add_argument("--threshold", type=float, default=0.6, help="Similarity below which a cut is reported")
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    out_dir = assets.asset_dir(plan.get("assets", plan["name"]))
    cache_file = out_dir / "cutwords.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}

    words_cache: dict = {}
    cuts = []
    for n, item in enumerate(plan["timeline"], 1):
        if "clip" in item:
            s, e, _ = clip_range(item, args.videos_dir, words_cache)
            cuts.append((n, item, s, e, cut_key(item, s, e)))

    todo = [c for c in cuts if c[4] not in cache]
    if todo:
        audio_cache, parts, spans, t = {}, [], [], 0.0
        gap = np.zeros(int(GAP * 16000), dtype=np.float32)
        for n, item, s, e, key in todo:
            mp3 = (args.videos_dir / item["clip"]).with_suffix(".mp3")
            if mp3 not in audio_cache:
                audio_cache[mp3] = decode_audio(str(mp3))
            a = audio_cache[mp3][int(s * 16000):int(e * 16000)]
            spans.append((key, t, t + len(a) / 16000))
            parts += [a, gap]
            t += (len(a) + len(gap)) / 16000
        print(f"verifying {len(todo)} cuts ({t / 60:.1f} min of audio) with ElevenLabs...")
        with tempfile.TemporaryDirectory() as tmp:
            wav, mp3 = Path(tmp) / "cuts.wav", Path(tmp) / "cuts.mp3"
            pcm = (np.clip(np.concatenate(parts), -1, 1) * 32767).astype(np.int16)
            with wave.open(str(wav), "wb") as f:
                f.setnchannels(1), f.setsampwidth(2), f.setframerate(16000), f.writeframes(pcm.tobytes())
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-q:a", "4", str(mp3)], check=True)
            data = transcribe_one(load_api_key(), mp3, "scribe_v2")
        for key, a, b in spans:
            cache[key] = [{"text": w["text"], "type": w["type"], "start": round(w["start"] - a, 3),
                           "end": round(min(w["end"], b) - a, 3)}
                          for w in data["words"] if w["type"] != "spacing" and a - 0.2 <= w["start"] < b + 0.2]
        cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    bad = 0
    for n, item, s, e, key in cuts:
        heard = " ".join(w["text"] for w in cache[key] if w["type"] == "word")
        ratio = difflib.SequenceMatcher(None, norm(item.get("text", "")), norm(heard)).ratio()
        if ratio < args.threshold:
            bad += 1
            print(f"#{n:>3} {item['clip'][-12:]} {s:.2f}-{e:.2f}  ({ratio:.0%})\n"
                  f"      plan : {item.get('text', '')}\n      heard: {heard}")
    print(f"{len(cuts)} cuts checked, {bad} mismatches" + (" — all good" if not bad else ""))


if __name__ == "__main__":
    main()
