#!/usr/bin/env python3
"""Validate the extracted Peninsula styles and fonts as the current source of truth.

The old starter version copied styles from another book's root files. This edition already owns
its canonical sheets at ``epub/OEBPS/styles/``; setup must verify them, not silently replace them.
The command is idempotent and read-only unless ``--copy-from DIR`` is explicitly supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEST = ROOT / "epub" / "OEBPS" / "styles"
SHEETS = ("stylesheet.css", "fonts.css")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copy-from", type=Path,
                        help="copy same-named sheets from this directory before validating")
    args = parser.parse_args()
    if args.copy_from:
        source = args.copy_from if args.copy_from.is_absolute() else ROOT / args.copy_from
        for name in SHEETS:
            src = source / name
            if not src.is_file():
                parser.error(f"--copy-from is missing {src}")
            DEST.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, DEST / name)
            print(f"  copied {name} from {source}")

    errors: list[str] = []
    report: dict[str, object] = {"directory": str(DEST.relative_to(ROOT)), "sheets": {}}
    for name in SHEETS:
        path = DEST / name
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT)}")
            continue
        data = path.read_bytes()
        text = data.decode("utf-8")
        report["sheets"][name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                                  "lines": text.count("\n") + 1}
        if not text.strip():
            errors.append(f"empty {name}")
    fonts = DEST / "fonts.css"
    if fonts.is_file():
        declared = re.findall(r"url\(\s*\.\./fonts/([^)'\"\s]+)", fonts.read_text(encoding="utf-8"))
        dangling = sorted({name for name in declared if not (DEST.parent / "fonts" / name).is_file()})
        report["font_urls"] = {"declared": len(declared), "dangling": dangling}
        if dangling:
            errors.append("fonts.css has dangling font URLs: " + ", ".join(dangling))
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "styles_sync.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"sync_styles: checked {len(report['sheets'])}/{len(SHEETS)} sheets under {DEST.relative_to(ROOT)}")
    if errors:
        for error in errors:
            print("  FAIL:", error)
        return 1
    print("sync_styles: PASS (book-owned sheets are present and all font URLs resolve)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
