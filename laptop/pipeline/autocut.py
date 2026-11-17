#!/usr/bin/env python3
"""One command for everything before the creative pass:

  stage 1   extract_audio.py   audio from every video (subfolders included)
  stage 2   transcribe.py      local speech check -> ElevenLabs (voice parts only)
  stage 2c  overview.py        overview.md + storyboard_N.jpg for stage 3

Then ask Claude to read overview.md + the storyboards and build the edit plan.
"""

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def run(script: str, *args: str) -> None:
    print(f"\n=== {script} ===", flush=True)
    subprocess.run([sys.executable, str(HERE / script), *args], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--no-subfolders", action="store_true")
    parser.add_argument("--no-storyboard", action="store_true")
    args = parser.parse_args()

    common = [str(args.folder)] + (["--no-subfolders"] if args.no_subfolders else [])
    run("extract_audio.py", *common)
    run("transcribe.py", *common)
    run("overview.py", *common, *(["--no-storyboard"] if args.no_storyboard else []))
    print(f"\nReady for stage 3: {args.folder / 'overview.md'}")


if __name__ == "__main__":
    main()
