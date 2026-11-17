"""Which way is up? Sample stored (un-rotated) frames of each clip and find the rotation that shows upright faces."""
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2

MODEL = Path(r"C:\Work\AutoCut\models\face_detection_yunet_2023mar.onnx")
ROT = {0: None, 90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
STEP = 3


def best_face(det, img):
    h, w = img.shape[:2]
    det.setInputSize((w, h))
    _, faces = det.detect(img)
    return 0.0 if faces is None else float(max(f[14] for f in faces))


def main():
    folder = Path(sys.argv[1])
    det = cv2.FaceDetectorYN.create(str(MODEL), "", (640, 360), score_threshold=0.6)
    for name in sys.argv[2:]:
        video = next(folder.glob(f"*{name}*.mp4"))
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["ffmpeg", "-v", "error", "-noautorotate", "-skip_frame", "nokey", "-i", str(video),
                            "-vf", f"fps=1/{STEP},scale=640:-2", str(Path(tmp) / "%04d.jpg")], check=False)
            line = []
            for jpg in sorted(Path(tmp).glob("*.jpg")):
                img = cv2.imread(str(jpg))
                scores = {r: best_face(det, img if c is None else cv2.rotate(img, c)) for r, c in ROT.items()}
                r, s = max(scores.items(), key=lambda kv: kv[1])
                t = (int(jpg.stem) - 1) * STEP
                line.append(f"{t}:{r if s > 0 else '-'}")
        print(f"{video.name}\n  " + " ".join(line), flush=True)


main()
