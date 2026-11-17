# Running Claude Code + AutoCut on Windows

Step-by-step to get Claude Code working on your Windows machine, then get this
AutoCut pipeline running there too (so the whole thing — transcribe, select,
build the CapCut draft, open CapCut — happens on one machine with no
Linux↔Windows path translation needed).

## 1. Install Node.js

Claude Code needs Node.js 18 or newer.

1. Go to https://nodejs.org and download the **LTS** installer for Windows.
2. Run it, accepting the defaults.
3. Verify in PowerShell:
   ```
   node --version
   ```

## 2. Install Claude Code

Open PowerShell and run:

```
npm install -g @anthropic-ai/claude-code
```

Verify it installed:

```
claude --version
```

> **Native Windows vs. WSL2:** Claude Code runs natively in PowerShell/cmd —
> no WSL required. If you'd rather have a more Linux-like environment (closer
> to how this pipeline was built and tested), you can instead install
> [WSL2](https://learn.microsoft.com/windows/wsl/install) (`wsl --install` in
> an admin PowerShell) and install Node + Claude Code inside that Ubuntu
> environment the same way. Either works; native Windows is simpler and is
> what the rest of these steps assume.

## 3. Log in

From any folder, run:

```
claude
```

The first run opens a browser window to log in with your Anthropic account
(the same one you use on Linux). After that, `claude` in any folder uses that
login.

## 4. Unzip AutoCut and open it

1. Unzip the `AutoCut.zip` you uploaded somewhere convenient, e.g.
   `C:\Users\<you>\AutoCut`.
2. In PowerShell:
   ```
   cd C:\Users\<you>\AutoCut
   claude
   ```
   You now have the same conversational stage-3 selection step (reading
   transcripts, writing `edl.json`) available directly on Windows.

## 5. Set up the Python pipeline on Windows

The zip does **not** include the `.venv` folder (it's Linux-only binaries and
won't run on Windows), so recreate it here:

1. Install Python 3.12 from https://python.org (check "Add python.exe to
   PATH" during install).
2. In the `AutoCut` folder:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r pipeline\requirements.txt
   ```
3. Install ffmpeg (needed for stage 1, audio extraction):
   ```
   winget install ffmpeg
   ```
   or download a build from https://ffmpeg.org and add it to your PATH.

## 6. Re-add the ElevenLabs API key

The zip also does **not** include `pipeline/.env` (it held your API key —
left out on purpose so the key isn't sitting in a file you upload to Google
Drive). Recreate it on Windows:

1. Create `pipeline\.env` with:
   ```
   ELEVENLABS_API_KEY=your_key_here
   ```

## 7. Adjust `config.yaml` for local Windows paths

Since everything now runs on the same Windows machine as CapCut, copy
`pipeline/config.example.yaml` to `pipeline/config.yaml` and point
`draft_output_dir` at a real local folder (or CapCut's actual drafts
directory, if you find its setting for that) — the `linux_prefix` /
`windows_prefix` mapping that exists for the cross-machine Linux→Windows
setup isn't needed anymore since there's only one machine now.

See `pipeline/README.md` for the full stage-by-stage pipeline usage once
setup is done.
