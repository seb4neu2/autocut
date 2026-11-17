#!/usr/bin/env python3
"""Stage 2 (default): local speech check, then ElevenLabs transcription for clips with speech.

For each .mp3, a quick local faster-whisper pass decides whether anything is actually
said. Its voice-activity filter drops non-speech audio before recognition, and it stops
as soon as it has found a few confident words, so drone shots / b-roll cost almost
nothing to check and talking clips aren't fully transcribed twice. Only clips that pass
are sent to ElevenLabs (paid) — and only their voice parts, with word times mapped back
to the original clip (about 60% cheaper, and long breathing/grunting stretches no longer
throw off the word alignment). --full-audio sends whole files instead.

Produces, per audio file:
  - name.speech.json       result of the local check (cached; b-roll clips get only this)
  - name.elevenlabs.json   raw ElevenLabs response        (clips with speech only)
  - name.elevenlabs.txt    human-readable transcript       (clips with speech only)
"""

import argparse
import json
import sys
from pathlib import Path

import requests
from faster_whisper import WhisperModel

from transcribe_elevenlabs import load_api_key, transcribe_one, transcribe_speech_only, write_txt

# A segment is ignored when whisper's own silence rule fires (likely no voice AND low
# confidence), or when confidence is so low it's a hallucination on noise. Tuned on real
# vlog footage: a single-signal rule dropped quiet real speech (no_speech_prob 0.62,
# logprob -0.56), while noise hallucinations came out around logprob -2.6.
NO_SPEECH_PROB_MAX = 0.6
AVG_LOGPROB_MIN = -1.0
HALLUCINATION_LOGPROB = -2.0


def is_noise(seg) -> bool:
    silent = seg.no_speech_prob > NO_SPEECH_PROB_MAX and seg.avg_logprob < AVG_LOGPROB_MIN
    return silent or seg.avg_logprob < HALLUCINATION_LOGPROB


def up_to_date(output: Path, source: Path) -> bool:
    return output.exists() and output.stat().st_mtime >= source.stat().st_mtime


def check_speech(model: WhisperModel, mp3: Path, min_words: int) -> dict:
    segments, info = model.transcribe(
        str(mp3), vad_filter=True, beam_size=1, condition_on_previous_text=False,
        temperature=0.0,  # no random-sampling retries: deterministic, and noise can't get "lucky"
    )
    words: list[str] = []
    for seg in segments:  # lazy generator: breaking early skips the rest of the audio
        if is_noise(seg):
            continue
        words.extend(seg.text.split())
        if len(words) >= min_words:
            break
    return {
        "has_speech": len(words) >= min_words,
        "sample": " ".join(words),
        "language": info.language if words else None,
        "duration": round(info.duration, 1),
        "speech_seconds": round(info.duration_after_vad, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Folder containing .mp3 files")
    parser.add_argument("--model", default="scribe_v2", help="ElevenLabs STT model_id")
    parser.add_argument("--check-model", default="small", help="faster-whisper model for the local speech check")
    parser.add_argument("--min-words", type=int, default=3,
                        help="Confident words the local check must find to count a clip as speech")
    parser.add_argument("--force", action="store_true",
                        help="Redo the speech check and re-send to ElevenLabs even if outputs are up to date")
    parser.add_argument("--no-subfolders", action="store_true", help="Only process .mp3 files directly in the folder")
    parser.add_argument("--full-audio", action="store_true",
                        help="Send the whole mp3 instead of only its voice parts (costlier; keeps long sound-event tags)")
    args = parser.parse_args()

    api_key = load_api_key()
    billed = 0.0
    mp3s = sorted(args.folder.glob("*.mp3") if args.no_subfolders else args.folder.rglob("*.mp3"))
    if not mp3s:
        print(f"No .mp3 files found in {args.folder}", file=sys.stderr)
        return

    model: WhisperModel | None = None
    sent = skipped_broll = 0

    for mp3 in mp3s:
        json_path = mp3.with_suffix(".elevenlabs.json")
        txt_path = mp3.with_suffix(".elevenlabs.txt")
        speech_path = mp3.with_suffix(".speech.json")
        name = mp3.relative_to(args.folder)

        if not args.force and up_to_date(json_path, mp3):
            print(f"skip  {name} (already transcribed)")
            continue

        if not args.force and up_to_date(speech_path, mp3):
            check = json.loads(speech_path.read_text(encoding="utf-8"))
        else:
            if model is None:
                model = WhisperModel(args.check_model, device="cpu", compute_type="int8")
            print(f"check {name} ...", end=" ", flush=True)
            check = check_speech(model, mp3, args.min_words)
            speech_path.write_text(json.dumps(check, ensure_ascii=False, indent=2), encoding="utf-8")
            print("speech" if check["has_speech"] else "no speech")

        if not check["has_speech"]:
            print(f"skip  {name} (no speech — b-roll, not sent to ElevenLabs)")
            skipped_broll += 1
            continue

        print(f"transcribe (ElevenLabs) {name} -> {json_path.name}")
        try:
            if args.full_audio:
                data = transcribe_one(api_key, mp3, args.model)
                billed += check["duration"]
            else:
                data = transcribe_speech_only(api_key, mp3, args.model)
                billed += data.get("billed_seconds", 0)
        except requests.HTTPError as e:
            print(f"  ElevenLabs API failed on {name}: {e.response.status_code} {e.response.text[:500]}", file=sys.stderr)
            continue
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        write_txt(data, txt_path)
        sent += 1

    print(f"done: {sent} sent to ElevenLabs ({billed / 60:.1f} min billed), {skipped_broll} skipped as b-roll")


if __name__ == "__main__":
    main()
