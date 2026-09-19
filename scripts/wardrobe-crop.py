#!/usr/bin/env python3
"""Task 6 / Task T4: face crops for wardrobe i2i variants + reference portraits.

Usage: python3 wardrobe-crop.py <job> [--boxes boxes.json]
  job = yoona | sohee | jiyeon | sohee-morning | jiwon

--boxes: optional JSON file {"vN": [x, y, w, h], "ref": [x, y, w, h]} giving face
boxes in pixels that override Haar detection (VLM-guided re-cropping, per 6-a).

Reference portraits:
  yoona:  epub/OEBPS/images/char-limyoonah.jpg
  sohee:  epub/OEBPS/images/char-hansohee.jpg
  jiyeon: epub/OEBPS/images/char-parkjiyeon.jpg   (T4, ch110-113)
  sohee-morning: same char-hansohee.jpg portrait (T4 morning scene)
  jiwon:  epub/OEBPS/images/char-kimjiwon.jpg    (T4, ch110-113)

Variants v1..v18 (864x1152; rounds of 6) in scripts/wardrobe-<job>/ -> faces/<id>.jpg at 768x768.
"""
import json
import os
import sys
from pathlib import Path
import cv2
import numpy
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EPUB_IMAGES = ROOT / "epub" / "OEBPS" / "images"

JOBS = {
    "yoona": {
        "out_dir": str(ROOT / "scripts" / "wardrobe-yoona"),
        "ref_img": str(EPUB_IMAGES / "char-limyoonah.jpg"),
    },
    "sohee": {
        "out_dir": str(ROOT / "scripts" / "wardrobe-sohee"),
        "ref_img": str(EPUB_IMAGES / "char-hansohee.jpg"),
    },
    "jiyeon": {
        "out_dir": str(ROOT / "scripts" / "wardrobe-jiyeon"),
        "ref_img": str(EPUB_IMAGES / "char-parkjiyeon.jpg"),
    },
    "sohee-morning": {
        "out_dir": str(ROOT / "scripts" / "wardrobe-sohee-morning"),
        "ref_img": str(EPUB_IMAGES / "char-hansohee.jpg"),
    },
    "jiwon": {
        "out_dir": str(ROOT / "scripts" / "wardrobe-jiwon"),
        "ref_img": str(EPUB_IMAGES / "char-kimjiwon.jpg"),
    },
}
OUT_SIZE = (768, 768)
VARIANTS = [f"v{i}" for i in range(1, 19)]  # up to 3 rounds of 6

CASCADES = [cv2.CascadeClassifier(cv2.data.haarcascades + f)
            for f in ("haarcascade_frontalface_default.xml",
                      "haarcascade_frontalface_alt2.xml")]


def crop_resize(img, box, out_path):
    x, y, w, h = box
    left, top = max(0, x), max(0, y)
    right = min(img.width, x + w)
    bottom = min(img.height, y + h)
    face = img.crop((left, top, right, bottom)).resize(OUT_SIZE, Image.LANCZOS)
    face.save(out_path, "JPEG", quality=92)
    return face.size


def detect_face(img):
    cv_img = cv2.cvtColor(numpy.array(img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    best = None
    for casc in CASCADES:
        faces = casc.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=5,
                                      minSize=(40, 40))
        for (x, y, w, h) in faces:
            if best is None or w * h > best[2] * best[3]:
                best = (int(x), int(y), int(w), int(h))
    return best


def margin_box(box, img_w, img_h):
    x, y, w, h = box
    mx = int(0.55 * w)
    mt = int(0.75 * h)
    mb = int(0.45 * h)
    x0 = max(0, x - mx)
    y0 = max(0, y - mt)
    x1 = min(img_w, x + w + mx)
    y1 = min(img_h, y + h + mb)
    bw, bh = x1 - x0, y1 - y0
    side = max(bw, bh)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    x0 = max(0, cx - side // 2)
    y0 = max(0, cy - side // 2)
    x1 = min(img_w, x0 + side)
    y1 = min(img_h, y0 + side)
    return (x0, y0, x1 - x0, y1 - y0)


def main():
    argv = sys.argv[1:]
    job = argv[0] if argv else ""
    if job not in JOBS:
        print("usage: wardrobe-crop.py <yoona|sohee|jiyeon|sohee-morning|jiwon> [--boxes boxes.json]")
        sys.exit(1)
    boxes = {}
    if "--boxes" in argv:
        bpath = argv[argv.index("--boxes") + 1]
        with open(bpath) as fh:
            boxes = {k: tuple(v) for k, v in json.load(fh).items()}
        print(f"loaded VLM-guided box overrides: {sorted(boxes.keys())}")
    cfg = JOBS[job]
    out_dir = cfg["out_dir"]
    face_dir = os.path.join(out_dir, "faces")
    os.makedirs(face_dir, exist_ok=True)

    # Reference portrait — Haar-detected (all are clear single-face portraits)
    ref = Image.open(cfg["ref_img"]).convert("RGB")
    if "ref" in boxes:
        box = margin_box(boxes["ref"], ref.width, ref.height)
        note = f"VLM-guided box {boxes['ref']} -> margin box {box}"
    else:
        det = detect_face(ref)
        if det:
            box = margin_box(det, ref.width, ref.height)
            note = f"detected face {det} -> margin box {box}"
        else:
            # fallback: upper-center heuristic
            side = int(0.55 * ref.width)
            cx, cy = ref.width // 2, int(0.30 * ref.height)
            box = (max(0, cx - side // 2), max(0, cy - side // 2), side, side)
            note = f"NO face detected, fallback upper-center box {box}"
    crop_resize(ref, box, os.path.join(face_dir, "ref.jpg"))
    print(f"ref.jpg: portrait {ref.size} {note} -> 768x768")

    for vid in VARIANTS:
        src = os.path.join(out_dir, f"{vid}.jpg")
        if not os.path.exists(src):
            continue
        img = Image.open(src).convert("RGB")
        if vid in boxes:
            box = margin_box(boxes[vid], img.width, img.height)
            note = f"VLM-guided box {boxes[vid]} -> margin box {box}"
        else:
            det = detect_face(img)
            if det:
                box = margin_box(det, img.width, img.height)
                note = f"detected face {det} -> margin box {box}"
            else:
                w = img.width
                h = img.height
                side = int(0.30 * w)
                cx = w // 2
                cy = int(0.16 * h)
                box = (cx - side // 2, max(0, cy - side // 2), side, side)
                note = f"NO face detected, fallback upper-center box {box}"
        out = os.path.join(face_dir, f"{vid}.jpg")
        crop_resize(img, box, out)
        print(f"{vid}.jpg: {img.size} {note} -> 768x768")


if __name__ == "__main__":
    main()
