# AutoCut - project notes

Speech-driven rough cuts into CapCut drafts. Status in `status.md`, pipeline details in `pipeline\README.md`.
Shared machine and tool notes are in `C:\Work\CLAUDE.md`.

## Re-editing a video the user has already worked on
- The user edits drafts heavily by hand in CapCut (cuts, crops, volumes, music, captions, own narration takes) and does not list the changes. **A new version is made from the user's latest draft, not from the old plan.**
- How: read `draft_content.json` of the latest draft, apply the changes to a copy, and write it as a new draft folder holding only `draft_content.json` and pycapcut's `draft_meta_info.json` template. Never write into the user's draft. Example: `assets\Thailand_Shortcut_42_v2\tools\make_draft_v6.py`.
- First compare the draft with a fresh scratch build of its plan to see what the user changed, and adopt their choices as new defaults where they are general (caption style, colours).
- If something in the user's edit looks like a mistake, ask instead of fixing it silently.
- The user makes narration takes on the ElevenLabs website and drops them into `assets\<name>\` (`ElevenLabs_*.mp3`). Their two takes so far used different settings (speed 1.07, similarity 50, then speed 1.00, similarity 75), so which they prefer is open.

## Upright (portrait) clips (user, 2026-10-23)
- **Never leave out a clip because it is upright** (portrait, or flagged "sideways" / "upside_down" in the shot log). Look through it like any other clip; it may hold something valuable.
- The user often starts filming upright and **turns the camera to landscape partway through**. The phone keeps the orientation it started with, so from the turn on, the picture is sideways in the file. Check frames across the whole clip, not just the start (contact sheet, `tools\sheet.py`), and note where the turn happens.
- Use the parts that are worth it: the sideways part with a per-item `"rotate"` (90 or -90) in the plan, or a lossless corrected copy via the plan's `"media"` map (see `pipeline\README.md`, "Wrongly oriented clips"); a truly upright part as it is (black bars at the sides, as with the Vietnam hammock clip). If a clip is skipped, say why in the report, never only because of its orientation.

## Narration voice (ElevenLabs)
- **Voice:** Richard Basston - Deep, voice id `i6icHCFicH3kzHTat04x` (British, deep, middle aged, narrative). Use this one voice for all narration.
- **Model:** Eleven v4, model id `eleven_v4` (checked on the account 2026-10-12; max 10000 characters per request).
- **Tagging:** every narration line gets audio tags before generation. ElevenLabs' own "Enhance" button is web-only (no API in the docs, checked 2026-10-12), so Claude writes the tags, following the official guide: https://elevenlabs.io/docs/best-practices/prompting/eleven-v4 (decided by the user 2026-10-12). Rules from that guide:
  - Never change, add or remove words. Only add tags in square brackets, and optionally `...` for a pause, CAPITALS for emphasis on one word, `?` and `!`.
  - A tag goes directly before the words it shapes, or directly after them (`This is hard. [sighs]`).
  - Only voice tags: emotion and delivery (`[curious]`, `[excited]`, `[sarcastic]`, `[thoughtful]`, `[surprised]`, `[whispers]`), sounds the narrator makes (`[sighs]`, `[exhales]`, `[chuckles]`, `[laughs]`), pauses (`[short pause]`, `[long pause]`), or a free description (`[low, steady voice, restrained urgency]`). No stage directions and no sound effect or music tags (`[applause]`, `[music]`, `[grinning]`): sound effects come from the sfx track.
  - Match the voice. This is a deep, serious British narrator: dry, calm, wry tags suit it; playful ones (`[giggles]`, `[woo]`, `[sings]`) do not. Tags the voice was not trained on are less reliable.
  - Go light: about one tag per sentence at most, and many sentences need none. The tags should follow what happens in the picture at that moment.
  - Speed setting stays between 0.7 and 1.2 (default 1.0).
  - Strip tags from the text used for narration captions, and list the tagged lines for the user in the report so they can be corrected (a few lines cost almost nothing; ask first only for a large batch).
- Settings, taken from the take the user made on the ElevenLabs website on 2026-10-12: speed 1.07, stability 0.5, similarity 0.5. These are the defaults in `pipeline\assets.py` (`narration()`).
- **Time spans in narration are 42, not 40** (user, 2026-10-12): when the narrator names a time frame, say "forty two minutes", never "forty minutes". 42 is the channel's running number ("hello forty-two").
- In a plan: `"text"` is the caption wording, `"tagged"` the spoken wording with tags. Check each new file by ear or with a local whisper pass (tags must not be read aloud).

## Caption colours (user, 2026-10-12)
- **Narration captions:** main colour `#F4C70F` (CapCut RGB 0.957, 0.780, 0.059).
- **"Forty two" is always `#FF8000`** (CapCut RGB 1.0, 0.502, 0.0), only those words, the rest of the caption keeps its normal colour:
  - in narration captions, when the narrator says it;
  - in the dialogue captions (subtitles), every time the user or anyone else says it.
- Match every spelling the transcript may give: "forty two", "forty-two", "42".
- **In every language**: the user coloured "cuarenta y dos", "zweiundvierzig", "czterdzieści dwa" and "42" orange by hand in the Thailand v5 greeting, and merged the caption pieces so the whole number sits in one caption.
- **Dialogue captions are white with highlighted key words** (user, 2026-10-23, replaces the plain-white rule of Thailand v5): Poppins Bold size 8.1 at height y -0.618, like the narration captions. Specific words or short phrases that carry the moment (the punchline, the place, the surprise, a strong feeling) are `#F4C70F`, a little bigger (x1.15) and pop in, like Vietnam v1, which the user liked better than the all-white v2. Everything else stays white. In the code: the plan's `"emphasis"` word list; pick the words per video, not too many (a few per minute).
- In the code since 2026-10-12 (`pipeline\build_plan.py`: `forty_two_spans`, caption defaults). Limit: a number split over two caption pieces ("cuarenta" / "y dos") is not caught, so merge those pieces.

## Swearing (user, 2026-10-12)
- When the user swears, **split the clip at the swear word**: one cut right before the word and one right after it, so the word is its own small clip on the main track. Set the **volume of that small clip to 0**. The picture keeps running, nothing is removed from the timeline, and the clips before and after stay at normal volume.
- Why (Claude's reading): a separate muted clip is easy to see, adjust or undo in CapCut, unlike volume keyframes hidden inside a long clip.
- Use the verified word times from `verify_cuts.py` for the two cuts, with the same small padding as now (about 0.03 s before, 0.05 s after).
- The 1 kHz beep still plays over the muted clip (on the `bleep` track), and the caption still shows the censored word with stars (`f***`). Confirmed by the user 2026-10-12.
- In the code since 2026-10-12 (`pipeline\build_plan.py`, the `mutes` list): the clip is built as separate pieces, the swear piece with volume 0, plus the beep.

## Travel map (user, 2026-10-12)
- **Every travel video gets an animated route map** of the trip (from where to where), in the style of the first one: Phuket to Khao Sok National Park. Script to copy and adapt: `assets\Thailand_Shortcut_42_v2\tools\make_route_map.py` (real coastline from OpenStreetMap, real road route from OSRM, camera pulls back while the route draws, pin drops on the destination; data download is under 1 MB).
- **Placement: picture-in-picture in the top left corner**, on an overlay track above the main video, at the moment the trip is mentioned. Values the user set by hand in `Thailand_Shortcut_42_v5` (4K canvas): scale 0.4265, transform x -0.574, y 0.533. That leaves a small even margin to the left and top edge.
- **Mask:** a rectangle mask exactly the size of the map clip (width 1.0, height 1.0, centred, no feather), with **round corners 25** (CapCut stores it as `roundCorner: 0.25`). In pycapcut: `VideoSegment.add_mask` with the rectangle type. Nothing of the map may be cut off except the corners.
- The user's own test had the mask slightly smaller than the clip (0.969 x 0.988); the rule is the exact size.
- **The mask is a required step, never skip it** (user, 2026-10-23: Vietnam v3's map came out without it). `build_plan.py` adds it to every overlay video with "map" in its file name, even when the plan has no `"round"`. pycapcut's own `add_mask` alone does not work in CapCut 9.2: it writes an old resource id under `materials.masks`, which CapCut drops. `rect_mask()` and `move_masks()` write CapCut's own rectangle (resource id 7374021450748924432) into `materials.common_mask`. Check in the final draft JSON that the map segment has a `common_mask` entry with `roundCorner: 0.25`.
- **Labels are baked into the map clip** (use the `--labels` render). This is the agreed exception to the text rule below: the map is a moving animation and the labels have to move with it (user, 2026-10-12).
- **Where the trip started:** look in the Google Timeline export `C:\Work\Cleaning\Timeline.json` first (user, 2026-10-23); its visits and activities give start, end and times. Vietnam v3 script to copy: `assets\Vietnam_NoHotel_Waterfall\tools\make_route_map.py` (inland version: rivers, lakes and roads instead of coastline). Overpass needs a user agent (`curl -A ...`), or it answers 406.
- **Ask the user first when a location is not known**: start point, destination, or any place name that goes on the map. Do not guess and bake it in, because baked text cannot be corrected in CapCut. (Phuket Town was assumed as the start in the first one.)

## Info cards and end screen (user, 2026-10-23)
- **Info card wording may be livelier than the user's brief.** The user gives the facts; Claude may rewrite them to be more entertaining (jokes, a punchline row), keeping the facts. The Vietnam v2 cards (peeing, Pho Bo) were too plain.
- **A picture that belongs to an info card goes below the card**, left-aligned with it, not beside it (the user moved the Pho Bo picture under its card in Vietnam v2 for better spacing).
- **No "next video" / "subscribe" slots on the end screen.** The end screen is the title line ("For real, for real" in Vietnam) with "Thanks for watching / See you in the next one" over the last shot, no darkened background with frames.

## Sound effects next to narration (user, 2026-10-22)
- **A sound effect must not play over the narrator's first words.** When a sting (or similar) belongs to a narration line, it starts about **0.65 s before** the line and at a **lower volume, about 0.2** (the user changed the Vietnam v2 stings from 0.1 s before at volume 0.6 to 0.65 s before at 0.20 and 0.24).
- This is for stings only. The record scratch on a freeze frame stays on the cut, and the level-up chime at "Final score" stays with the narrator at volume 0.5 (the user kept both, 2026-10-23).
- In the code (`build_plan.py`, `SFX_LEAD`, `SFX_UNDER_NARR`): a sound marked `"lead": true` in the plan's sfx library that starts within 0.5 s of its item's narration start is moved ahead and lowered.

## Text and graphics in drafts
- **Use rendered graphics (PNG) only when it cannot be avoided.** All splash screens, title cards, end cards, stickers, HUD panels and labels must be easy to change or remove inside CapCut.
- All text is a native CapCut text segment (`cc.TextSegment`), never baked into an image. Only exception: the labels inside the animated travel map (see "Travel map").
- If a design needs a panel, card or shape, render only the background as a PNG on an overlay track and place the text on top as CapCut text. Prefer CapCut's own text background (`cc.TextBackground`) when a plain box is enough.
- `pipeline\graphics.py` works this way since 2026-10-12: each overlay returns a text-free background image (or none) plus text items; `build_plan.py` places them as CapCut text. Title card and sticker need no image.
- Text size in pixels is an estimate (`graphics.px_per_size`, about 20 px per size unit on a 4K canvas), not yet confirmed in CapCut. Centred text is safe; text lined up against a panel edge (HUD) depends on it.
- CapCut's overlay fonts (Anton, Bebas Neue, Poppins Bold) have no baht sign: write "BAHT".
- **Cards must not overlap the chapter label** (user, 2026-10-22): when an info card or HUD panel is on screen together with a chapter label (top left, "09 · THE PARTY"), the card goes lower so the two do not overlap. In the code since 2026-10-22 (`build_plan.py`, `CHAPTER_DROP`): a top-left card that starts while its item's chapter label is up moves down by 0.28 half-heights. Also check other top-left overlays (map, pictures) against the label by hand.
- **Preview cards on the final build** before reporting (frame + background PNG + text at its position). Vietnam v2's info-card text sat off its panel because an old cached background was reused after a size change (fixed 2026-10-22: backgrounds are named by their pixels).
- Thumbnails are separate image files, not part of the draft, so they stay rendered.

## Thumbnails: the koel direction (user, 2026-10-24)
- The user called `assets\Vietnam_NoHotel_Waterfall\youtube\shorts\short_koel_ai_03.jpg` **"awesome": go in this direction in the future.**
- What it is, so it can be repeated (script: `assets\Vietnam_NoHotel_Waterfall\tools\make_short_thumbnails.py`):
  1. **Local base first** (free): two real pictures stacked in 9:16, a slanted black and yellow divider, a big face close-up with a clear emotion on top (sleepy, annoyed), the "subject" of the story on the bottom (the bird), headline in Anton, white lines plus one gold punchline (`"FOR REAL"`).
  2. **Nothing covers the subject**: the headline sits in the upper middle and the subject's face (the bird's red eye, open beak) is fully clear below it. When a try overlapped, the fix was in the local layout (`text_dy`, crop focus), not in the prompt.
  3. **Then Gemini 3 Pro Image** (OpenRouter, about $0.14) gets the local base with the prompt in that script: keep the faces and the exact words, make it more vivid and dramatic. It added a golden-hour sky, warm orange light against blue, mist on the river, crisp detail, and kept the layout.
- Do the same for long-video thumbnails where it fits: real faces and layout from the footage, AI only to polish. Check the AI version for drifted faces, covered letters and colours far from the real place (the pee thumbnail's turquoise falls).

## Length of Shorts (user, 2026-10-23)
- **Every Short is under 1 minute** (under 60 s, end card included), even though YouTube allows up to 3 minutes. Cut whole beats to get there, do not speed up the footage.

## Text splashes in short videos (user, 2026-10-12)
- **In short videos, text splashes use font size 25** (CapCut text size).
- In the code since 2026-10-23: `graphics.label` (the Shorts headline) defaults to size 25. Keep each line short (about 10 letters), size 25 is big on a 1080 px wide canvas.

## Card colours (user, 2026-10-12)
- Brand yellow is `#F4C70F` (RGB 244, 199, 15; CapCut RGB 0.957, 0.780, 0.059). It is the same yellow as the narration captions.
- **Background graphics (HUD panel, map card and similar): the outer rim is `#F4C70F`.**
- **The title of a card is `#F4C70F`** too.
- **Text inside a card stays white.**
- **A highlighted value or word inside a card is `#F4C70F`.**
- In the code since 2026-10-12 (`pipeline\graphics.py`: `YELLOW`, `YELLOW_F`).

## Length and zoom (user, 2026-10-12)
- **Videos should be at least 8 minutes long**, if the footage allows it without padding. If it does not reach 8 minutes, say so and say what is missing, do not stretch it with filler.
- **Use zoom sparingly.** No zoom by default; add one only where it is really necessary and there is a concrete reason (for example a detail that is too small to see), and be ready to name that reason.
- In the code since 2026-10-12: no zoom unless a plan item sets `"zoom"`. In Thailand v6 only the two punch-ins on "Never again" and the user's own crops are left.
