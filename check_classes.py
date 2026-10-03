#!/usr/bin/env python3
"""Check that every XHTML class token is declared by the Peninsula stylesheets.

Usage: ``python3 check_classes.py [--json]``. Exit 1 when a class is used but not styled.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
BOOK = ROOT / "epub" / "OEBPS"
STYLE_FILES = [p for p in (BOOK / "styles" / "stylesheet.css", BOOK / "styles" / "fonts.css",
                           BOOK / "styles" / "edition.css") if p.exists()]
USED = re.compile(r'class="([^"]*)"')


def declared_classes() -> set[str]:
    live: set[str] = set()
    for path in STYLE_FILES:
        css = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
        for selector_group in re.findall(r"([^{}]+)\{", css):
            if selector_group.strip().startswith("@"):
                continue
            live.update(re.findall(r"\.([A-Za-z][A-Za-z0-9_-]*)", selector_group))
    return live


def main() -> int:
    if not STYLE_FILES:
        print("check_classes: no stylesheets found under epub/OEBPS/styles", file=sys.stderr)
        return 1
    live = declared_classes()
    report: dict[str, dict[str, int]] = {}
    pages = sorted((BOOK / "text").glob("*.xhtml"))
    for page in pages:
        bad: dict[str, int] = {}
        for attr in USED.findall(page.read_text(encoding="utf-8")):
            for token in attr.split():
                if token not in live:
                    bad[token] = bad.get(token, 0) + 1
        if bad:
            report[page.name] = dict(sorted(bad.items(), key=lambda item: (-item[1], item[0])))
    if "--json" in sys.argv:
        print(json.dumps({"unknown_classes": report,
                          "stylesheets_checked": [p.name for p in STYLE_FILES],
                          "pages_checked": len(pages)}, ensure_ascii=False))
    elif report:
        print(f"UNKNOWN CLASSES in {len(report)} page(s):")
        for name, tokens in report.items():
            print(f"  {name}")
            for token, count in tokens.items():
                print(f"    .{token} ×{count}")
    else:
        print(f"classes OK — {len(pages)} pages, {len(live)} declared classes")
    return 1 if report else 0


if __name__ == "__main__":
    raise SystemExit(main())
