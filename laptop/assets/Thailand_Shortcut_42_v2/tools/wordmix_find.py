#!/usr/bin/env python3
"""Find clean single-word cuts for the word-mix Shorts (sentences made from single words).

For every wanted word, lists each place it is said in the footage transcripts, then for each one:
  1. tightens the cut on the audio itself (quiet points next to the ElevenLabs word times),
  2. plays that exact cut to local whisper (free) padded with silence, and records what it hears.
Writes wordmix/candidates.json: word -> candidates sorted best first
(heard correctly, room to the neighbouring words, clear loudness).

  python wordmix_find.py boat thousand baht ...      (or no words: the default list below)
  python wordmix_find.py --fast because stupid ...    only trims, no whisper check (seconds, not minutes)
"""

import glob
import json
import re
import sys
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

FOLDER = Path(r"D:\Backup\VlogX")
OUT = Path(__file__).resolve().parent.parent / "wordmix" / "candidates.json"
SR = 16000
MAX_TAKES = 6   # checking every "I" and "the" takes far too long; six takes are enough to choose from
WORDS = """i took the boat two thousand baht nobody will know dogs hello am dog best way follow me he's tired
sweaty ridiculous beautiful place no water trash everywhere dangerous i'm five stars go again need have wine is
very good don't drink zero""".split()


def norm(w: str) -> str:
    return re.sub(r"[^\w']", "", w.lower())


def rms(x: np.ndarray) -> np.ndarray:
    hop = int(0.01 * SR)
    n = len(x) // hop
    return np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-10)


def tighten(audio: np.ndarray, s: float, e: float, lo: float, hi: float) -> tuple[float, float, float]:
    """Move s/e to the quietest 10 ms frame nearby, never past the neighbouring words (lo/hi)."""
    a0 = max(int((lo) * SR), 0)
    seg = audio[a0:int(hi * SR)]
    env = rms(seg)
    t = lambda i: lo + i * 0.01
    idx = lambda x: int(round((x - lo) / 0.01))
    peak = float(env[max(idx(s), 0):max(idx(e), idx(s) + 1)].max()) if len(env) else 0.0
    floor = peak * 0.08

    def search(x, back):
        i = min(max(idx(x), 0), len(env) - 1)
        rng = range(i, max(i - 25, 0), -1) if back else range(i, min(i + 25, len(env) - 1))
        for j in rng:          # first frame that is quiet enough, walking outwards
            if env[j] <= floor:
                return t(j)
        cand = list(rng)
        return t(min(cand, key=lambda j: env[j])) if cand else x
    return round(search(s, True), 3), round(search(e, False), 3), peak


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if a != "--fast"]
    fast = "--fast" in sys.argv
    wanted = [norm(w) for w in (args or WORDS)]
    model = None if fast else WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
    result = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    audio_cache, seen = {}, {}
    for f in sorted(glob.glob(str(FOLDER / "*.elevenlabs.json"))):
        words = [w for w in json.load(open(f, encoding="utf-8"))["words"] if w["type"] == "word"]
        clip = Path(f).name.replace(".elevenlabs.json", ".MP4")
        for i, w in enumerate(words):
            if norm(w["text"]) not in wanted or seen.get(norm(w["text"]), 0) >= MAX_TAKES:
                continue
            seen[norm(w["text"])] = seen.get(norm(w["text"]), 0) + 1
            if clip not in audio_cache:
                audio_cache[clip] = decode_audio(str(FOLDER / clip.replace(".MP4", ".mp3")), sampling_rate=SR)
            audio = audio_cache[clip]
            prev_end = words[i - 1]["end"] if i else 0.0
            next_start = words[i + 1]["start"] if i + 1 < len(words) else len(audio) / SR
            lo = max(prev_end - 0.02, w["start"] - 0.4)
            hi = min(next_start + 0.02, w["end"] + 0.4)
            s, e, peak = tighten(audio, w["start"], w["end"], lo, hi)
            if e - s < 0.08:
                continue
            cut = audio[int(s * SR):int(e * SR)]
            fade = min(int(0.008 * SR), len(cut) // 4)
            cut = cut.copy()
            cut[:fade] *= np.linspace(0, 1, fade)
            cut[-fade:] *= np.linspace(1, 0, fade)
            pad = np.zeros(int(0.6 * SR), dtype=np.float32)
            if model:
                segs, _ = model.transcribe(np.concatenate([pad, cut, pad]), language="en", beam_size=1,
                                           vad_filter=False, condition_on_previous_text=False)
                heard = " ".join(sg.text.strip() for sg in segs).strip()
            else:
                heard = ""
            ok = norm(heard.split()[0]) == norm(w["text"]) if len(heard.split()) == 1 else False
            ctx = " ".join(x["text"] for x in words[max(i - 3, 0):i + 4])
            result.setdefault(norm(w["text"]), [])
            result[norm(w["text"])] = [c for c in result[norm(w["text"])]
                                       if not (c["clip"] == clip and abs(c["src"] - w["start"]) < 0.01)]
            result[norm(w["text"])].append({
                "clip": clip, "src": w["start"], "start": s, "end": e, "speaker": w.get("speaker_id"),
                "heard": heard, "ok": ok, "gap_before": round(w["start"] - prev_end, 2),
                "gap_after": round(next_start - w["end"], 2), "level_db": round(20 * np.log10(peak + 1e-9), 1),
                "context": ctx})
            print(f"{norm(w['text']):>12} {clip[:5]} {s:8.2f}-{e:7.2f} {'OK ' if ok else '-- '} heard={heard!r:24} | {ctx}", flush=True)
    for k, v in result.items():
        v.sort(key=lambda c: (not c.get("ok"), -min(c["gap_before"], c["gap_after"], 0.3), -c["level_db"]))
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written", OUT)


if __name__ == "__main__":
    main()
