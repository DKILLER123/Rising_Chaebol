#!/usr/bin/env python3
"""Build the Peninsula EPUB from the editable ``epub/`` tree.

Only ``mimetype``, ``META-INF/`` and ``OEBPS/`` are packaged. The verbatim raw archive and audit
reports stay outside the deliverable. ``mimetype`` is always the first, stored ZIP entry.
"""
from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TREE = ROOT / "epub"
OUT = ROOT / "public" / "Peninsula_Rising_Chaebol.epub"


def entries() -> list[str]:
    required = [TREE / "mimetype", TREE / "META-INF" / "container.xml", TREE / "OEBPS" / "content.opf"]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("build_epub: missing required source files: " + ", ".join(missing))
    payload = []
    for prefix in ("META-INF", "OEBPS"):
        base = TREE / prefix
        payload.extend(p.relative_to(TREE).as_posix() for p in base.rglob("*") if p.is_file())
    return ["mimetype"] + sorted(payload)


def main() -> int:
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__.strip())
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rels = entries()
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        zi = zipfile.ZipInfo("mimetype")
        zi.compress_type = zipfile.ZIP_STORED
        archive.writestr(zi, b"application/epub+zip")
        for rel in rels[1:]:
            archive.write(TREE / rel, rel, compress_type=zipfile.ZIP_DEFLATED)

    data = OUT.read_bytes()
    with zipfile.ZipFile(OUT) as archive:
        infos = archive.infolist()
        first_stored = (
            bool(infos)
            and infos[0].filename == "mimetype"
            and infos[0].compress_type == zipfile.ZIP_STORED
            and archive.read("mimetype") == b"application/epub+zip"
        )
        bad = archive.testzip()
    digest = hashlib.sha256(data).hexdigest()
    print(f"built {OUT.relative_to(ROOT)}")
    print(f"entries: {len(infos)} · size: {len(data):,} B · sha256: {digest}")
    print(f"mimetype first/STORED: {first_stored} · testzip: {bad}")
    if not first_stored or bad:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
