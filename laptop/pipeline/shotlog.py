#!/usr/bin/env python3
"""Stage 2d (optional): a vision model describes what is visible, every few seconds of every clip.

The storyboards show 6 frames per talking clip, so most silent footage is never looked at.
This samples a small frame every --every seconds, sends --group consecutive frames per request
to a vision model and writes one line per stretch: shot type, what happens, how usable it is
as b-roll, and problems (dark, blurry, sideways, ...).

Works with any OpenAI-compatible endpoint, so the same run can be compared between
  - OpenRouter (paid, default):  OPENROUTER_API_KEY in pipeline/.env
  - a local llama-server (free): --api-base http://127.0.0.1:8080/v1

Produces:
  - name.shots.json   next to each video (cached; rerun only redoes changed videos)
  - shotlog.md        in the folder: every clip in filming order, stretches with speech marked
"""

import argparse
import base64
import json
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from dotenv import load_dotenv

from extract_audio import find_videos
from overview import clip_id, probe

OPENROUTER = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "qwen/qwen3-vl-8b-instruct"
FRAME_W = 768

PROMPT = """These {n} frames are consecutive stills from one vlog clip, {every:g} seconds apart, in order.
Answer with one JSON object and nothing else:
{{"shot": "<wide | medium | close | selfie | pov | aerial>",
 "what": "<max 22 words: what is visible and what changes across the frames; concrete nouns, no guessing>",
 "broll": <0-3: 0 unusable, 1 filler, 2 good cutaway, 3 striking image>,
 "flags": [<any of: "dark", "overexposed", "blurry", "shaky", "sideways", "upside_down", "lens_dirty", "static", "face_visible", "other_people", "text_on_screen">]}}"""


def fmt_t(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


def extract_frames(video: Path, every: float, out_dir: Path) -> list[Path]:
    # Decode only keyframes, on the GPU: 4K60 HEVC from the DJI has one every 0.5 s, so nothing
    # is lost at --every 2 and a 59 s clip takes 2 s instead of 85 s. Falls back to a full
    # software decode when the fast way yields nothing (no GPU decoder, sparse keyframes).
    tail = ["-i", str(video), "-vf", f"fps=1/{every},scale={FRAME_W}:-2", "-q:v", "5", str(out_dir / "%05d.jpg")]
    fast = subprocess.run(["ffmpeg", "-v", "error", "-y", "-hwaccel", "d3d11va", "-skip_frame", "nokey", *tail])
    expected = probe(video)["duration"] / every
    if fast.returncode != 0 or len(list(out_dir.glob("*.jpg"))) < expected * 0.8:
        subprocess.run(["ffmpeg", "-v", "error", "-y", *tail], check=True)
    return sorted(out_dir.glob("*.jpg"))


def kept_frames(video: Path, every: float, frames_dir: Path) -> list[Path]:
    """Frames kept for looking at, named <clip>_<mm>m<ss>s.jpg; extracted once."""
    if not any(frames_dir.glob("*.jpg")):
        frames_dir.mkdir(parents=True, exist_ok=True)
        for i, f in enumerate(extract_frames(video, every, frames_dir)):
            t = i * every
            f.rename(frames_dir / f"{clip_id(video.stem)}_{int(t // 60):02d}m{int(t % 60):02d}s.jpg")
    return sorted(frames_dir.glob("*.jpg"))


def parse_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    try:
        return json.loads(text[start:end + 1])
    except ValueError:
        return {"shot": "?", "what": text.strip()[:200], "broll": 0, "flags": ["unparsed"]}


def describe(session: requests.Session, api_base: str, model: str, frames: list[Path], every: float) -> tuple[dict, dict]:
    content = [{"type": "text", "text": PROMPT.format(n=len(frames), every=every)}]
    for f in frames:
        b64 = base64.b64encode(f.read_bytes()).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    body = {"model": model, "messages": [{"role": "user", "content": content}], "temperature": 0, "max_tokens": 200}
    for attempt in range(4):
        resp = session.post(f"{api_base}/chat/completions", json=body, timeout=300)
        if resp.status_code in (429, 500, 502, 503) and attempt < 3:
            time.sleep(5 * (attempt + 1))
            continue
        resp.raise_for_status()
        data = resp.json()
        return parse_json(data["choices"][0]["message"]["content"] or ""), data.get("usage", {})
    raise RuntimeError("unreachable")


def speech_seconds(video: Path, start: float, end: float) -> float:
    path = video.with_suffix(".elevenlabs.json")
    if not path.exists():
        return 0.0
    words = json.loads(path.read_text(encoding="utf-8")).get("words", [])
    return sum(max(0.0, min(w["end"], end) - max(w["start"], start)) for w in words if w.get("type") == "word")


def log_video(session, args, video: Path, usage: dict, frames_dir: Path | None = None) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        frames = kept_frames(video, args.every, frames_dir) if frames_dir else extract_frames(video, args.every, Path(tmp))
        groups = [frames[i:i + args.group] for i in range(0, len(frames), args.group)]
        if args.limit:
            groups = groups[:args.limit]
        with ThreadPoolExecutor(args.parallel) as pool:
            results = list(pool.map(lambda g: describe(session, args.api_base, args.model, g, args.every), groups))
    duration = probe(video)["duration"]
    shots = []
    for i, (shot, used) in enumerate(results):
        start = i * args.group * args.every
        end = min(duration, start + args.group * args.every)
        shots.append({"start": start, "end": end, **shot})
        for k in ("prompt_tokens", "completion_tokens", "cost"):
            usage[k] = usage.get(k, 0) + (used.get(k) or 0)
    return {"model": args.model, "every": args.every, "group": args.group, "partial": bool(args.limit), "shots": shots}


def write_markdown(folder: Path, videos: list[Path]) -> Path:
    lines = [f"# Shot log: {folder.name}", "",
             "One line per stretch: time | shot | b-roll score 0-3 | what is visible | flags. 🗣 = speech in that stretch.", ""]
    for video in videos:
        path = video.with_suffix(".shots.json")
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        lines.append(f"## {clip_id(video.stem)}  {video.relative_to(folder).as_posix()}")
        for s in data["shots"]:
            talk = " 🗣" if speech_seconds(video, s["start"], s["end"]) > 0.5 else ""
            flags = " [" + ", ".join(s.get("flags") or []) + "]" if s.get("flags") else ""
            lines.append(f'- {fmt_t(s["start"])}–{fmt_t(s["end"])}{talk} | {s.get("shot", "?")} | b{s.get("broll", 0)} | {s.get("what", "")}{flags}')
        lines.append("")
    out = folder / "shotlog.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--every", type=float, default=2.0, help="seconds between sampled frames (default 2)")
    ap.add_argument("--group", type=int, default=3, help="frames per request = one log line (default 3)")
    ap.add_argument("--api-base", default=OPENROUTER, help="OpenAI-compatible endpoint (default OpenRouter)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--parallel", type=int, default=4, help="requests at once (use 1 for a local server)")
    ap.add_argument("--only", help="only videos whose name contains this text")
    ap.add_argument("--limit", type=int, help="only the first N requests per video (to measure cost and speed)")
    ap.add_argument("--keep-frames", type=Path, metavar="DIR", help="keep the sampled frames in DIR/<video name>/")
    ap.add_argument("--frames-only", action="store_true", help="with --keep-frames: only extract frames, no model calls")
    ap.add_argument("--no-subfolders", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    session = requests.Session()
    if "openrouter.ai" in args.api_base and not args.frames_only:
        load_dotenv(Path(__file__).parent / ".env")
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise SystemExit("Set OPENROUTER_API_KEY in pipeline/.env, or pass --api-base for a local server")
        session.headers["Authorization"] = f"Bearer {key}"
        session.params = {}

    videos = find_videos(args.folder, recursive=not args.no_subfolders)
    usage: dict = {}
    t0 = time.time()
    for video in videos:
        if args.only and args.only not in video.name:
            continue
        frames_dir = args.keep_frames / video.stem if args.keep_frames else None
        if args.frames_only:
            if frames_dir:
                print(f"{video.name}: {len(kept_frames(video, args.every, frames_dir))} frames", flush=True)
            continue
        out = video.with_suffix(".shots.json")
        if out.exists() and not args.force and out.stat().st_mtime >= video.stat().st_mtime \
                and not json.loads(out.read_text(encoding="utf-8")).get("partial"):
            continue
        t1 = time.time()
        data = log_video(session, args, video, usage, frames_dir)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{video.name}: {len(data['shots'])} stretches in {time.time() - t1:.0f} s", flush=True)

    md = write_markdown(args.folder, videos)
    cost = f", cost ${usage['cost']:.4f}" if usage.get("cost") else ""
    print(f"{md}  ({time.time() - t0:.0f} s, {usage.get('prompt_tokens', 0)} tokens in, "
          f"{usage.get('completion_tokens', 0)} out{cost})")


if __name__ == "__main__":
    main()
