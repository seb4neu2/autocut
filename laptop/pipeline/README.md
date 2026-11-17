# Speech-driven auto rough-cut pipeline

Turns a folder of raw footage into a CapCut draft, assembled purely from what
was said. Every stage includes subfolders of the given folder by default
(pass `--no-subfolders` to stages 1–2 to process only the top level); output
files are always written next to their source video. See `/home/niu/.claude/plans/twinkling-wobbling-sprout.md` for the
full design rationale.

## Setup (one-time)

Windows (current setup — pipeline and CapCut on the same machine):
```
cd C:\Work\AutoCut
.venv\Scripts\activate           # python 3.12 venv, already created
```
`pipeline\config.yaml` already writes drafts straight into CapCut's drafts
folder with no path mapping. Put `ELEVENLABS_API_KEY=...` in `pipeline\.env`
if you want stage 2b.

Linux (original setup): `source .venv/bin/activate`, copy
`config.example.yaml` to `config.yaml`, and fill in `path_mappings` so draft
paths get rewritten to the Windows drive letters CapCut sees.

## Quick start (the whole thing)

```
python pipeline/autocut.py D:\footage\folder        # stages 1, 2, 2c in one go
```
Then ask Claude: *"Read overview.md and the storyboards in D:\footage\folder,
propose 3 directions."* → pick one → *"Build the plan."* Claude writes
`plan.json` in the folder and runs:
```
python pipeline/verify_cuts.py <folder>\plan.json <folder>   # check every cut, exact word times
python pipeline/build_plan.py  <folder>\plan.json <folder>   # full produced draft into CapCut
```

## Stage 1 — extract audio

```
python pipeline/extract_audio.py /path/to/video/folder
```
Writes `name.mp3` next to each video. Skips files already up to date; pass
`--force` to redo. Videos with no audio track at all (typical for drone
footage) are skipped as b-roll.

## Stage 2 — transcribe (default: local speech check → ElevenLabs)

```
python pipeline/transcribe.py /path/to/video/folder
```
For each mp3, a quick local faster-whisper check (model `small`) decides
whether anything is actually said. Only clips with speech are sent to
ElevenLabs (paid); drone shots / b-roll are never uploaded — and only the
voice parts of those clips (joined by short silences, word times mapped back),
which is ~60–80% cheaper and fixes the broken word timings ElevenLabs produces
next to long breathing/grunting stretches. `--full-audio` sends whole files. The check takes a
few seconds per clip: whisper's voice-activity filter drops non-speech audio,
and the check stops once it finds `--min-words` (default 3) confident words.

Writes next to each mp3:
- `name.speech.json` — the check's result (`has_speech`, a sample of the words
  heard, detected language). Cached, so reruns don't recheck.
- `name.elevenlabs.json` / `name.elevenlabs.txt` — only for clips with speech:
  raw API response (word-level timestamps, speaker ids, audio-event tags) and
  a human-readable, speaker-labeled transcript.

Requires `ELEVENLABS_API_KEY` in `pipeline/.env` (or the environment). Skips
clips already transcribed; `--force` redoes the check and re-sends. If a clip
with speech gets marked as b-roll (e.g. one quick word), lower `--min-words`,
or delete its `name.speech.json` and rerun.

Alternatives:
- `python pipeline/transcribe_local.py <folder>` — fully local and free
  (`large-v3-turbo`), writes `name.txt` + `name.words.json`.
- `python pipeline/transcribe_elevenlabs.py <folder>` — sends every mp3 to
  ElevenLabs with no speech check.

When `name.elevenlabs.json` exists for a video, it takes priority over the
free whisper output: read `name.elevenlabs.txt` instead of `name.txt` during
stage 3 selection, and `build_draft.py` automatically snaps cuts using its
word timestamps instead of whisper's.

## Stage 2c — overview for stage 3

```
python pipeline/overview.py /path/to/video/folder
```
Writes `overview.md` (every clip in filming order with phrase-level lines and
exact start/end times; `⚠` marks unreliable word timings) and
`storyboard_N.jpg` frame sheets (6 frames per talking clip, more for b-roll).
Stage 3 reads only these — no follow-up lookups, far fewer tokens.

## Stage 2d — shot log (optional, sees the silent footage)

```
python pipeline/shotlog.py /path/to/video/folder                                    # OpenRouter (paid, minutes)
python pipeline/shotlog.py /path/to/video/folder --api-base http://127.0.0.1:8089/v1 --model local --parallel 1   # local llama-server (free, slow)
```
A vision model (Qwen3-VL 8B) looks at a frame every 2 s, three frames per request, and
writes `name.shots.json` per video plus `shotlog.md`: one line per 6 s with shot type,
what is visible, a b-roll score 0–3 and flags (dark, blurry, sideways, ...). Stretches with
speech are marked 🗣. OpenRouter needs `OPENROUTER_API_KEY` in `pipeline/.env`; `--limit 4`
measures cost and speed on a few requests first. Local on the Arc 140V: about 34 s per line.

Frames are taken the fast way: the graphics chip decodes only the keyframes
(`-hwaccel d3d11va -skip_frame nokey`; DJI 4K60 has one every 0.5 s), about 2 s for a
1-minute 4K clip instead of 85 s, with an automatic fallback to a full software decode.
`--keep-frames assets\<name>\frames` keeps the frames (named `<clip>_<mm>m<ss>s.jpg`) so
lines in `shotlog.md` can be checked against the pictures; `--frames-only` skips the model.
Measured on Thailand (43 min of footage): 433 lines for $0.10. The descriptions are
reliable enough to find footage; the b-roll scores and flags are not, so confirm picks on
the frames. Run this before stage 3, so silent footage is planned in from the start.

## Stage 3 — select & order (the only step that costs tokens)

There's no script for this — it's done by asking Claude Code directly, since
that's already the "agent" in this workflow. Use whichever transcript is
better per video: `name.elevenlabs.txt` if it exists, else `name.txt`. Clips
whose `name.speech.json` says `"has_speech": false` (or with no mp3 at all)
are b-roll — no dialogue to cut, but available for cutaways in CapCut.

- **Directed**: "Read the transcripts in `<folder>` and build an edl.json that
  tells this story: `<your direction>`."
- **Auto-discover**: "Read the transcripts in `<folder>` and propose 3 possible
  directions this footage could go, each with a short pitch and a couple of
  example quotes." Then, once you pick one: "Build edl.json for direction 2."

Either way, the output is `edl.json` in the same folder: an ordered list of
```json
{"clip": 1, "source": "video3.mp4", "start": 12.4, "end": 15.1, "text": "..."}
```
Segments can come from any video in the folder or its subfolders, in any
order — whatever makes the chosen narrative coherent. `source` is the path
relative to the folder, e.g. `"Filmik vlog weed/PXL_20240318_090102277.mp4"`.

## Stage 4 — build the CapCut draft

```
python pipeline/build_draft.py /path/to/video/folder/edl.json /path/to/video/folder --draft-name my_video
```
Writes a CapCut draft folder under `draft_output_dir` (see config.yaml) with
every EDL entry trimmed and placed on the timeline in order — no re-encoding,
no cutting of the original files. Canvas size and fps come from the first
source video unless `video_width`/`video_height` are set in config.yaml.

It refuses to overwrite an existing draft with the same name (that folder may
be a real CapCut project you've already edited). Pass `--replace` to overwrite
deliberately.

## Stage 4 v2 — produced edit from a plan (`build_plan.py`)

`build_draft.py` lays clips on one track. `build_plan.py` builds the full thing
from a `plan.json` (example: `D:\Backup\VlogX\plan_v2.json`, and
`plan_short.json` for a vertical Short):

- **Main track**: dialogue clips with automatic punch-in zooms on jump cuts
  (`"zoom": "auto" | "punch" | "push" | 1.2`), b-roll with speed (`"broll"`,
  `"speed": 2.5` for montages), black-and-white freeze frames (`"freeze"`),
  placeholders, CapCut transitions (`"transition": "叠化"` dissolve,
  `"闪白"` white flash, ... any `pycapcut.TransitionType` name).
- **Wrongly oriented clips**: phone clips filmed with the rotation lock on come out
  sideways, cameras handed to someone else upside down. Fix the rotation flag losslessly
  (`ffmpeg -display_rotation 0|180 -i in.mp4 -map 0:v:0 -map 0:a:0 -c copy assets/<name>/upright/in.mp4`)
  and list the copy in the plan: `"media": {"in.mp4": "C:\\...\\upright\\in.mp4"}` — the
  draft shows the copy, transcripts and cut verification keep using the original.
  `"rotate": 180` on a single item turns just that cut.
- **Captions**: word-timed, 1–3 words, emphasis words in yellow with a pop-in,
  swearing shown as `f***`. `"captions": [{"from", "to", "text"}]` overrides a
  range (translations, fixes). Narration captions in a second, italic style.
- **Censor bleeps**: every swear word is dipped out of the clip's audio and a
  1 kHz beep plays over it (list in `PROFANITY`).
- **Narration** (`"narration": {"text": ...}`): ElevenLabs TTS, voice Richard Basston - Deep
  on Eleven v4 (`"narrator_voice"`, `"narrator_settings": {"model", "stability", "similarity",
  "speed"}` in the plan). `"tagged"` is the same line with audio tags (`[deadpan] Spoiler: ...`)
  and is what gets spoken; captions show `"text"`. `"file"` uses an existing recording from the
  asset folder instead (it needs a `.json` with `{"sentences": [{text, start, end}]}`).
  `"highlight": {"Forty two": [1, 0.5, 0]}` colours a phrase in the caption. `"narration_lufs"`
  in the plan plays every line at the same loudness. A freeze frame with narration stretches
  to fit the line.
- **Sound effects** (`"sfx"` library + `"sfx": [{"id", "at"}]` per item):
  generated by ElevenLabs from a text prompt.
- **Music** (`"music"` cues + `"music": "<cue>" | "stop"` on the item where a
  cue starts): ElevenLabs Music, generated to the exact section length,
  crossfaded between cues, ducked under speech (`dialog`) and up in b-roll
  (`open`).
- **Overlays** (`"overlay": [{"gfx": {...}, "at", "duration"}]`): title cards, game-style
  HUD panels, a route map, stickers and end cards. All wording is native CapCut text, so it
  can be changed or deleted in CapCut. graphics.py only draws what text cannot be: the HUD
  panel, the map card with its route, the end-card slots (text-free PNGs,
  `gfx_<type>-background_*.png`). Title card and sticker use no image at all. Text size in
  pixels is an estimate (`graphics.px_per_size`); correct that one number if text sits too
  big or too small on its panels.
- **Info cards** (`{"type": "info", "title", "lines", "highlight", "image"}`): panel top left with a yellow
  rim, text as CapCut text; `"image"` (a file in the asset folder, e.g. an AI picture) sits in the corner
  beside the panel, or alone without title and lines.
- **Other people's lines**: `"side_captions": [{"from", "to", "text"}]` puts them (e.g. translated
  Vietnamese) on the left side; `"auto_captions": false` with `"captions"` gives every caption of a clip by
  hand. `"y"` shifts a clip's picture up or down (like `"x"`). In a vertical draft side captions sit
  centred above the picture instead.
- **Wide shots in a vertical draft**: `"fit": true` on a clip or freeze shows the whole picture across the
  width, with CapCut's own background blur behind it (one click to change in CapCut). For group shots
  that a vertical crop would cut apart.
- **Chapters**: `"section": "The Plan"` puts an editable label on screen and
  writes `assets/<name>/chapters.txt` for the YouTube description.
- **Word mix**: `"snap": false` cuts a clip at exactly its `start`/`end` (single words already
  trimmed), `"over": {"broll", "start", "x", "rotate"}` plays the clip's voice over another shot,
  `"line"` with `"line_items": n` puts one caption over n items (a sentence built from single words).
- **Vertical** (`"canvas": "vertical"`): 1080x1920; footage is scaled to fill
  and auto-reframed on the speaker's face (OpenCV YuNet, `models/`).

All generated assets are cached in `assets/<name>/` by content hash — rebuilding
after an edit only pays for what changed. `"assets": "<other plan name>"` shares
a cache (a Short reusing the main video's sound effects and verified cuts).
`--no-music` skips music for quick iterations.

`verify_cuts.py` should run before each build: it re-transcribes exactly what
each cut plays (only new/changed cuts, one ElevenLabs request), prints cuts that
don't match their `"text"`, and stores the exact word times the captions and
bleeps use.

## Getting it into CapCut

On Windows the draft is written straight into CapCut's drafts folder: open
(or restart) CapCut and it's in the project list. The rough cut is already on
the timeline; add transitions and tighten pacing there. On the Linux setup,
copy the draft folder into CapCut's drafts directory on Windows first.

## Testing before running on real footage

Drop a couple of short throwaway clips with real speech into `/home/niu/Work/AutoCut/sample/`
and run all four stages against that folder first — including actually
opening the resulting draft in CapCut on Windows to confirm `pycapcut`'s
draft format is compatible with your installed CapCut version. Only point the
pipeline at the real `Data` partition footage once that checks out.
