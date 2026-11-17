#!/usr/bin/env python3
"""Precise single-word cuts for word-mix Shorts.

ElevenLabs word times in *.elevenlabs.json are only roughly right (often 0.1-0.3 s off), so a
cut made from them alone can catch part of the next word, or the same word twice when it was
repeated ("very, very", "yes, yes"). For one take (clip + rough time from the JSON) this:
  1. lets local whisper listen to about 3 s around it with word timestamps,
  2. finds the target word there, plus where the words before and after it end and start,
  3. cuts around the stretch where the voice really sounds, never past a neighbouring word,
  4. limits the cut to at most 0.12 s before and 0.18 s after the transcribed word (breaths).
Whisper is not asked to judge a lone word (it invents words like "Thank you" on short cuts);
check whole built sentences instead (sentence_check in the plan scripts).
Results are cached in wordmix/precise.json, so plans can be rewritten without waiting.

  from wordmix_precise import refine
  start, end, info = refine("42700_DJI_20240318_0091.MP4", 37.58, "i")
"""

import json
import re
from pathlib import Path

import numpy as np

FOLDER = Path(r"D:\Backup\VlogX")
CACHE = Path(__file__).resolve().parent.parent / "wordmix" / "precise.json"
SR = 16000
WINDOW = 1.5        # seconds of context on each side of the rough time
_model = None
_audio: dict = {}
_cache: dict | None = None


def norm(w: str) -> str:
    return re.sub(r"[^\w']", "", w.lower()).replace("fortytwo", "forty-two")


def _load(clip: str) -> np.ndarray:
    if clip not in _audio:
        from faster_whisper.audio import decode_audio
        _audio[clip] = decode_audio(str(FOLDER / Path(clip).with_suffix(".mp3")), sampling_rate=SR)
    return _audio[clip]


def _whisper():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
    return _model


def _env(x: np.ndarray) -> np.ndarray:
    hop = int(0.005 * SR)   # 5 ms frames
    n = len(x) // hop
    return np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-10)


def refine(clip: str, src: float, word: str, context: str = "") -> tuple[float, float, dict]:
    global _cache
    if _cache is None:
        _cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    key = f"{clip}|{src:.2f}|{norm(word)}"
    if key in _cache:
        c = _cache[key]
        return c["start"], c["end"], c
    audio = _load(clip)
    # the word in the ElevenLabs transcript, with its neighbours
    el = [w for w in json.loads((FOLDER / Path(clip).with_suffix(".elevenlabs.json")).read_text(encoding="utf-8"))["words"]
          if w["type"] == "word"]
    k = min(range(len(el)), key=lambda j: abs(el[j]["start"] - src))
    es, ee = el[k]["start"], el[k]["end"]
    el_prev = el[k - 1]["end"] if k else es - 1.0
    el_next = el[k + 1]["start"] if k + 1 < len(el) else ee + 1.0

    w0 = max(src - WINDOW, 0.0)
    win = audio[int(w0 * SR):int((src + WINDOW) * SR)]
    segs, _ = _whisper().transcribe(win, language="en", beam_size=5, word_timestamps=True, vad_filter=False,
                                    condition_on_previous_text=False, initial_prompt=context or None)
    words = [(norm(w.word), w0 + w.start, w0 + w.end) for s in segs for w in s.words]
    target = norm(word)
    hits = [i for i, w in enumerate(words) if w[0] == target or w[0].rstrip("s") == target.rstrip("s")]
    info = {"clip": clip, "src": src, "word": word, "window": " ".join(w[0] for w in words),
            "elevenlabs": (es, ee), "found": bool(hits)}
    centre = (es + ee) / 2
    lo, hi = el_prev, el_next
    if hits:
        i = min(hits, key=lambda j: abs((words[j][1] + words[j][2]) / 2 - centre))
        if i > 0:
            lo = max(lo, words[i - 1][2])
        if i + 1 < len(words):
            hi = min(hi, words[i + 1][1])
    # never let a neighbour's limit cut into the word itself (both transcripts can be off)
    lo = min(max(lo, centre - 0.6), centre - 0.06)
    hi = max(min(hi, centre + 0.6), centre + 0.06)

    # where the voice actually sounds between those limits: active stretches of the loudness curve
    a0 = max(lo - 0.05, 0.0)
    seg = audio[int(a0 * SR):int((hi + 0.05) * SR)]
    env = _env(seg)
    t = lambda n: a0 + n * 0.005
    f = lambda x: int(round((x - a0) / 0.005))
    peak = float(env[max(f(lo), 0):f(hi)].max())
    active = env >= peak * 0.1
    runs, n = [], 0
    while n < len(active):
        if active[n]:
            m = n
            while m + 1 < len(active) and active[m + 1]:
                m += 1
            runs.append([n, m])
            n = m + 1
        else:
            n += 1
    runs = [r for r in runs if t(r[1]) > lo and t(r[0]) < hi]
    merged = []
    for r in runs:   # join stretches split by short dips inside one word (under 60 ms)
        if merged and r[0] - merged[-1][1] <= 12:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    # the stretch around the word's centre, plus any part of it still inside the transcribed word
    core = [r for r in merged if t(r[1]) >= es - 0.03 and t(r[0]) <= ee + 0.03] or         [min(merged, key=lambda r: abs((t(r[0]) + t(r[1])) / 2 - centre))]
    # a breath or room noise joined to the word must not stretch the cut far past the transcribed word
    start = max(t(core[0][0]) - 0.02, lo, es - 0.12)
    end = min(t(core[-1][1]) + 0.04, hi, ee + 0.18)
    start, end = round(start, 3), round(end, 3)

    info.update(start=start, end=end, limits=(round(lo, 3), round(hi, 3)),
                level_db=round(20 * np.log10(peak + 1e-9), 1))
    _cache[key] = info
    _save()
    return start, end, info


def _save() -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(_cache, ensure_ascii=False, indent=1), encoding="utf-8")
