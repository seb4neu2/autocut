"""Auto-reframe for vertical (Shorts) drafts: find where the face is in a clip.

Uses OpenCV's YuNet face detector (models/face_detection_yunet_2023mar.onnx) on a few
frames of the cut and returns the face's horizontal centre (0 = left edge, 1 = right),
so build_plan.py can shift the 9:16 crop to keep the speaker in frame.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from statistics import median

import cv2

MODEL = Path(__file__).parent.parent / "models" / "face_detection_yunet_2023mar.onnx"
_detector = None


def _detect(img) -> list[tuple[float, float]]:
    global _detector
    h, w = img.shape[:2]
    if _detector is None:
        _detector = cv2.FaceDetectorYN.create(str(MODEL), "", (w, h), score_threshold=0.75)
    _detector.setInputSize((w, h))
    _, faces = _detector.detect(img)
    if faces is None:
        return []
    return [((f[0] + f[2] / 2) / w, f[2] * f[3]) for f in faces]  # (centre x, area)


def face_x(video: Path, start: float, end: float, cache_file: Path, samples: int = 3) -> float | None:
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    key = f"{video.name}|{start:.2f}|{end:.2f}"
    if key in cache:
        return cache[key]
    xs = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(samples):
            t = start + (end - start) * (i + 0.5) / samples
            png = Path(tmp) / f"{i}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                            "-vf", "scale=960:-2", str(png)], check=False)
            img = cv2.imread(str(png)) if png.exists() else None
            if img is None:
                continue
            faces = _detect(img)
            if faces:
                xs.append(max(faces, key=lambda f: f[1])[0])  # largest face = the speaker
    result = round(float(median(xs)), 3) if xs else None
    cache[key] = result
    cache_file.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return result
