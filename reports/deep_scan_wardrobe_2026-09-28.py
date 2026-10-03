#!/usr/bin/env python3
"""Deep asset/reference scan for every installed wardrobe block.

This is intentionally structural rather than a face-recognition claim: visual identity
must still be reviewed against the canonical character portraits. The report records the
reference pairing, manifest/resource coverage, public mirror parity, and image dimensions.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "epub/OEBPS/text"
IMAGES = ROOT / "epub/OEBPS/images"
PUBLIC = ROOT / "public/book"
OPF = ROOT / "epub/OEBPS/content.opf"

WARDROBE_TO_CHARACTER = {
    "wd-eunjung-dorm.jpg": "char-hameunjung.jpg",
    "wd-eunjung-incognito.jpg": "char-hameunjung.jpg",
    "wd-eunjung-ongi-dinner.jpg": "char-hameunjung.jpg",
    "wd-eunjung-rehearsal.jpg": "char-hameunjung.jpg",
    "wd-hara-campus.jpg": "char-goohara.jpg",
    "wd-hyomin-rehearsal.jpg": "char-hyomin.jpg",
    "wd-hyomin-travel.jpg": "char-hyomin.jpg",
    "wd-jiwon-loungewear.jpg": "char-kimjiwon.jpg",
    "wd-jiyeon-athleisure.jpg": "char-parkjiyeon.jpg",
    "wd-jiyeon-navy-casual.jpg": "char-songjiyeon.png",
    "wd-jiyeon-training.jpg": "char-songjiyeon.png",
    "wd-jiyeon-sleepover.jpg": "char-parkjiyeon.jpg",
    "wd-sohee-civilian.jpg": "char-hansohee.jpg",
    "wd-sohee-morning.jpg": "char-hansohee.jpg",
    "wd-sohee-new-home.jpg": "char-hansohee.jpg",
    "wd-sulli-airport.jpg": "char-sulli.jpg",
    "wd-sulli-exchange.jpg": "char-sulli.jpg",
    "wd-sulli-hospital-watch.jpg": "char-sulli.jpg",
    "wd-songjiyeon-exchange.jpg": "char-songjiyeon.png",
    "wd-yoona-disguise.jpg": "char-limyoonah.jpg",
}

# The exact uploaded Hyomin attachment was unavailable to workspace tools. The canonical
# packaged portrait is therefore the honest comparison reference for the generated plates.
VISUAL_REVIEW = {
    "wd-sohee-new-home.jpg": "retained-user-confirmed-match",
    "wd-eunjung-dorm.jpg": "visually-reviewed-against-canonical-portrait-2026-10-03",
    "wd-eunjung-incognito.jpg": "visually-reviewed-against-canonical-portrait-2026-10-03",
    "wd-eunjung-ongi-dinner.jpg": "visually-reviewed-against-canonical-portrait-2026-10-03",
    "wd-eunjung-rehearsal.jpg": "visually-reviewed-against-canonical-portrait-2026-10-03",
    "wd-hara-campus.jpg": "regenerated-from-canonical-portrait-2026-09-28",
    "wd-hyomin-rehearsal.jpg": "regenerated-from-canonical-portrait-2026-09-28",
    "wd-hyomin-travel.jpg": "regenerated-from-canonical-portrait-2026-09-28",
    "wd-jiwon-loungewear.jpg": "regenerated-from-canonical-portrait-2026-09-28",
    "wd-jiyeon-athleisure.jpg": "regenerated-from-canonical-portrait-2026-09-28",
    "wd-jiyeon-navy-casual.jpg": "visually-reviewed-against-canonical-portrait-2026-10-03",
    "wd-jiyeon-sleepover.jpg": "regenerated-from-canonical-portrait-2026-09-28",
    "wd-jiyeon-training.jpg": "visually-reviewed-against-canonical-portrait-2026-10-03",
    "wd-sohee-civilian.jpg": "regenerated-from-canonical-portrait-2026-09-28",
    "wd-sohee-morning.jpg": "regenerated-from-canonical-portrait-2026-09-28",
    "wd-sulli-airport.jpg": "visually-reviewed-against-canonical-portrait-2026-10-03",
    "wd-sulli-exchange.jpg": "visually-reviewed-against-canonical-portrait-2026-10-03",
    "wd-sulli-hospital-watch.jpg": "visually-reviewed-against-canonical-portrait-2026-10-03",
    "wd-songjiyeon-exchange.jpg": "visually-reviewed-against-canonical-portrait-2026-10-03",
    "wd-yoona-disguise.jpg": "regenerated-from-canonical-portrait-2026-09-28",
}


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def dimensions(path: Path) -> dict[str, object]:
    try:
        out = subprocess.check_output(
            ["identify", "-format", "%wx%h %m", str(path)], text=True, stderr=subprocess.STDOUT
        ).strip()
        size, fmt = out.split(maxsplit=1)
        width, height = (int(x) for x in size.split("x", 1))
        return {"width": width, "height": height, "format": fmt}
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"error": str(exc)}


def main() -> int:
    opf_text = OPF.read_text(encoding="utf-8")
    manifest = set(re.findall(r'href="images/([^"]+)"', opf_text))
    wardrobe_files = sorted(IMAGES.glob("wd-*.jpg"))
    refs: dict[str, list[str]] = {path.name: [] for path in wardrobe_files}
    errors: list[str] = []
    blocks = []

    for chapter in sorted(TEXT.glob("chapter*.xhtml"), key=lambda p: int(re.search(r"(\d+)", p.name).group(1))):
        root = ET.parse(chapter).getroot()
        for block in root.findall('.//{http://www.w3.org/1999/xhtml}div[@class="wardrobe-block"]'):
            image = block.find('.//{http://www.w3.org/1999/xhtml}img[@class="wd-photo"]')
            if image is None or not image.get("src"):
                errors.append(f"{chapter.name}: wardrobe-block has no wd-photo")
                continue
            src = image.get("src")
            filename = Path(src).name
            refs.setdefault(filename, []).append(chapter.name)
            path = IMAGES / filename
            blocks.append({"chapter": chapter.name, "image": filename, "src": src})
            if not path.exists():
                errors.append(f"{chapter.name}: missing image {filename}")
            if filename not in manifest:
                errors.append(f"{chapter.name}: image not in OPF manifest {filename}")
            if filename not in WARDROBE_TO_CHARACTER:
                errors.append(f"{chapter.name}: no character mapping for {filename}")

    for filename, character in WARDROBE_TO_CHARACTER.items():
        image = IMAGES / filename
        portrait = IMAGES / character
        mirror = PUBLIC / filename
        if not image.exists():
            errors.append(f"missing wardrobe asset: {filename}")
            continue
        if not portrait.exists():
            errors.append(f"missing character reference: {character} for {filename}")
        if not mirror.exists():
            errors.append(f"missing public mirror: {filename}")
        elif md5(image) != md5(mirror):
            errors.append(f"public mirror differs: {filename}")
        if filename not in manifest:
            errors.append(f"wardrobe image not in OPF manifest: {filename}")
        if not refs.get(filename):
            errors.append(f"wardrobe image is not referenced: {filename}")

    # There should be no unmanifested package image. cover-bg.png was an unused duplicate
    # and is intentionally absent from the editable package after this correction.
    package_images = sorted(path.name for path in IMAGES.iterdir() if path.is_file())
    unmanifested = sorted(set(package_images) - manifest)
    if unmanifested:
        errors.extend(f"unmanifested image: {name}" for name in unmanifested)

    assets = []
    for filename in sorted(WARDROBE_TO_CHARACTER):
        image = IMAGES / filename
        portrait = IMAGES / WARDROBE_TO_CHARACTER[filename]
        assets.append(
            {
                "wardrobe": filename,
                "character_reference": WARDROBE_TO_CHARACTER[filename],
                "referenced_by": sorted(refs.get(filename, [])),
                "manifested": filename in manifest,
                "public_mirror_md5": md5(PUBLIC / filename) if (PUBLIC / filename).exists() else None,
                "epub_md5": md5(image) if image.exists() else None,
                "same_as_public_mirror": (image.exists() and (PUBLIC / filename).exists() and md5(image) == md5(PUBLIC / filename)),
                "wardrobe_dimensions": dimensions(image) if image.exists() else None,
                "portrait_dimensions": dimensions(portrait) if portrait.exists() else None,
                "visual_review": VISUAL_REVIEW.get(filename, "not-recorded"),
            }
        )

    status = "PASS" if not errors and not any("pending" in x for x in VISUAL_REVIEW.values()) else "REVIEW"
    report = {
        "scope": "all EPUB wardrobe blocks and image references",
        "status": status,
        "errors": errors,
        "wardrobe_block_count": len(blocks),
        "wardrobe_asset_count": len(assets),
        "unmanifested_package_images": unmanifested,
        "blocks": blocks,
        "assets": assets,
        "visual_identity_note": "Automated checks verify source pairing, existence, dimensions, manifest wiring, and byte mirrors; identity judgments require visual review against the canonical portraits. Exact uploaded Hyomin attachment was unavailable to workspace tools; char-hyomin.jpg is the documented fallback reference.",
    }
    out = ROOT / "reports/deep_scan_wardrobe_2026-09-28.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
