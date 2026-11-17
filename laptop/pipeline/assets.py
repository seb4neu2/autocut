"""ElevenLabs-generated assets for an edit plan: narration, sound effects, music.

Every asset is cached under assets/<plan name>/ by a hash of what produced it, so
rebuilding a plan only pays for lines/prompts that actually changed.

File names say what the file is, then end in that hash:
  music_<type-and-mood>_<length>s_<hash>.mp3     e.g. music_lofi-hiphop-deep-bass-chill-day_135s_ab12...
  sfx_<what-sound>_<hash>.mp3                    e.g. sfx_vinyl-record-scratch-stop_3f09...
  narration_<voice>_<first-words>_<hash>.mp3     e.g. narration_richard-basston_this-is-sebastian-forty_9c1e...
The cache looks files up by hash, so renaming the descriptive part never re-bills.
"""

import base64
import hashlib
import json
import re
import subprocess
from pathlib import Path

import requests

from transcribe_elevenlabs import load_api_key

API = "https://api.elevenlabs.io"
ASSETS_ROOT = Path(__file__).parent.parent / "assets"
VOICE_NAMES = {"JBFqnCBsd6RMkjVDRZzb": "george", "i6icHCFicH3kzHTat04x": "richard-basston"}


def _key(*parts) -> str:
    return hashlib.sha1(json.dumps(parts, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


def slug(text: str, words: int = 5) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", text.lower())[:words]) or "untitled"


def asset_dir(plan_name: str) -> Path:
    d = ASSETS_ROOT / plan_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cached(d: Path, kind: str, k: str, ext: str = ".mp3") -> Path | None:
    hits = sorted(d.glob(f"{kind}_*{k}{ext}"))
    return hits[0] if hits else None


def audio_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "0", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


def narration(plan_name: str, text: str, voice_id: str, *, tagged: str | None = None, file: str | None = None,
              model: str = "eleven_v4", stability: float = 0.5, similarity: float = 0.5,
              speed: float = 1.07) -> tuple[Path, list[dict]]:
    """TTS for one narration line. Returns (mp3, sentence timings [{text, start, end}]).

    `text` is what the captions show; `tagged` is the same words with audio tags like [deadpan]
    added and is what gets spoken. `file` uses an existing recording from the asset folder (for
    example a take made on the ElevenLabs website); it needs a .json next to it holding
    {"sentences": [{text, start, end}]}."""
    d = asset_dir(plan_name)
    if file:
        mp3 = d / file
        return mp3, json.loads(mp3.with_suffix(".json").read_text(encoding="utf-8"))["sentences"]
    spoken = tagged or text
    k = _key("tts", spoken, voice_id, model, stability, similarity, speed)
    mp3 = _cached(d, "narration", k)
    if mp3 is None:
        r = requests.post(
            f"{API}/v1/text-to-speech/{voice_id}/with-timestamps",
            headers={"xi-api-key": load_api_key()},
            json={"text": spoken, "model_id": model,
                  "voice_settings": {"stability": stability, "similarity_boost": similarity, "speed": speed}},
            timeout=300,
        )
        if not r.ok:
            raise SystemExit(f"ElevenLabs narration failed ({r.status_code}): {r.text[:500]}")
        data = r.json()
        mp3 = d / f"narration_{VOICE_NAMES.get(voice_id, voice_id[:6])}_{slug(text, 4)}_{k}.mp3"
        mp3.write_bytes(base64.b64decode(data["audio_base64"]))
        mp3.with_suffix(".json").write_text(json.dumps(data.get("alignment") or {}, ensure_ascii=False),
                                            encoding="utf-8")
    align = json.loads(mp3.with_suffix(".json").read_text(encoding="utf-8"))
    return mp3, _sentences(align)


def _sentences(align: dict) -> list[dict]:
    """Split a character alignment into sentence-ish caption chunks with times.
    Audio tags ([deadpan], [short pause], ...) are spoken directions and are left out."""
    chars = align.get("characters", [])
    starts, ends = align.get("character_start_times_seconds", []), align.get("character_end_times_seconds", [])
    out, cur, t0, depth = [], "", None, 0
    for i, (c, s, e) in enumerate(zip(chars, starts, ends)):
        if c == "[":
            depth += 1
        if depth:
            depth -= c == "]"
            continue
        if t0 is None and c.strip():
            t0 = s
        cur += c
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        initial = c == "." and i >= 1 and chars[i - 1].isupper() and (i < 2 or not chars[i - 2].isalpha())
        if (c in ".?!…" and nxt != "." and not (initial and nxt.isupper())) or (c == "," and len(cur) > 28):
            if cur.strip() and t0 is not None:
                out.append({"text": " ".join(cur.split()), "start": t0, "end": e})
            cur, t0 = "", None
    if cur.strip() and t0 is not None:
        out.append({"text": " ".join(cur.split()), "start": t0, "end": ends[-1]})
    return out


def loudness(path: Path) -> float:
    """Integrated loudness of an audio file in LUFS."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


def volume_for(path: Path, target_lufs: float) -> float:
    """Clip volume (at most 2.0, i.e. +6 dB) that plays `path` at the target loudness."""
    return round(min(2.0, 10 ** ((target_lufs - loudness(path)) / 20)), 3)


def sfx(plan_name: str, prompt: str, duration: float | None = None, influence: float = 0.4,
        name: str | None = None) -> Path:
    """Sound effect from a text prompt; `name` says what the sound is (defaults to the prompt)."""
    d = asset_dir(plan_name)
    k = _key("sfx", prompt, duration, influence)
    mp3 = _cached(d, "sfx", k)
    if mp3 is None:
        body = {"text": prompt, "prompt_influence": influence}
        if duration:
            body["duration_seconds"] = duration
        r = requests.post(f"{API}/v1/sound-generation", headers={"xi-api-key": load_api_key()}, json=body, timeout=300)
        r.raise_for_status()
        mp3 = d / f"sfx_{slug(name or prompt, 5)}_{k}.mp3"
        mp3.write_bytes(r.content)
    return mp3


def music(plan_name: str, prompt: str, seconds: float, name: str | None = None) -> Path:
    """Instrumental music of (at least) the given length, rounded up to 5 s to keep the cache stable.
    `name` should say the type and mood, e.g. "lofi hiphop deep bass chill day"."""
    length = max(10, min(300, int(-(-seconds // 5) * 5)))
    d = asset_dir(plan_name)
    k = _key("music", prompt, length)
    mp3 = _cached(d, "music", k)
    if mp3 is None:
        body = {"prompt": prompt, "music_length_ms": length * 1000, "force_instrumental": True}
        r = requests.post(f"{API}/v1/music", headers={"xi-api-key": load_api_key()}, json=body, timeout=600)
        if r.status_code in (400, 422):  # older API without force_instrumental
            body.pop("force_instrumental")
            r = requests.post(f"{API}/v1/music", headers={"xi-api-key": load_api_key()}, json=body, timeout=600)
        r.raise_for_status()
        mp3 = d / f"music_{slug(name or prompt, 7)}_{length}s_{k}.mp3"
        mp3.write_bytes(r.content)
    return mp3


def beep(plan_name: str) -> Path:
    """Classic 1 kHz TV censor beep (generated locally, free)."""
    wav = asset_dir(plan_name) / "sfx_censor-beep-1khz.wav"
    if not wav.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=3",
                        "-af", "volume=0.5", str(wav)], check=True)
    return wav
