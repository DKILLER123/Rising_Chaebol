#!/usr/bin/env python3
"""Guard the Peninsula tree against accidental bleed from the other-book templates.

The copied starter scripts came from a different novel. This book has its own legitimate cast and
companies, so the old reference-book cast list is not a valid gate here. The gate below keeps only
foreign protagonist/title/brand tokens that must never enter this edition.

Usage: ``python3 legacy_firewall.py [--docs] [--json reports/firewall.json]``.
Exit 1 on a forbidden hit; real Peninsula character names are intentionally not banned.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TREE = ROOT / "epub"
FORBIDDEN = {
    "foreign_protagonist": [r"\bSong\s+Ji-?ho\b", r"\bBae\s+Do-?yoon\b", r"\bPei\s+Yun\b"],
    "foreign_book_title": [r"Peninsula:?\s*Going\s+Viral", r"Dominating\s+South\s+Korea",
                            r"Golden\s+Trait"],
    "foreign_brands_and_labels": [r"\bLOEN\b", r"\bEIDER\b", r"\bSUNYE\b",
                                   r"Dream\s+Life", r"Girls\s*&\s*Peace",
                                   r"Let\s+Me\s+Down\s+Slowly"],
}
TEXT_EXTS = {".xhtml", ".opf", ".ncx", ".css", ".xml"}


def visible(source: str) -> str:
    source = re.sub(r"<[^>]+>", " ", source)
    return re.sub(r"\s+", " ", source)


def scan(paths: list[Path]) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for path in paths:
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if path.suffix in {".xhtml", ".opf", ".ncx", ".xml"}:
            text = visible(raw)
        elif path.suffix == ".css":
            # Legacy provenance in comments is not reader-visible and is removed from the scan.
            text = re.sub(r"/\*.*?\*/", " ", raw, flags=re.S)
        else:
            text = raw
        for group, patterns in FORBIDDEN.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.I):
                    start = max(0, match.start() - 55)
                    hits.append({"group": group, "pattern": pattern,
                                 "file": path.relative_to(ROOT).as_posix(),
                                 "match": match.group(0),
                                 "context": text[start:match.end() + 55]})
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", action="store_true", help="also scan authored root markdown")
    parser.add_argument("--json", metavar="PATH")
    args = parser.parse_args()
    paths = sorted(p for p in TREE.rglob("*") if p.is_file() and p.suffix in TEXT_EXTS)
    if args.docs:
        paths += sorted(ROOT.glob("*.md"))
    hits = scan(paths)
    report = {"files_scanned": len(paths), "forbidden_groups": list(FORBIDDEN),
              "hits": hits,
              "scope_note": "Foreign template tokens only; Peninsula cast and plot names are legal."}
    if args.json:
        out = ROOT / args.json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"legacy_firewall: {len(paths)} files scanned")
    if hits:
        print(f"  forbidden bleed ({len(hits)}):")
        for hit in hits[:40]:
            print(f"    [{hit['group']}] {hit['file']}: …{hit['context']}…")
    else:
        print("  forbidden bleed: 0")
    if args.json:
        print(f"  report: {args.json}")
    print("legacy_firewall:", "PASS" if not hits else "FAIL")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
