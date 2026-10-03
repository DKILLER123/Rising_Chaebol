#!/usr/bin/env python3
"""House structural gate for the editable ``epub/`` tree.

Checks XML parsing, stylesheet class coverage, curly-quote/CJK hygiene, internal references,
chapter sequence, and chapter stylesheet links. This is a fast structural gate, not a substitute
for EPUBCheck or human editorial review.
"""
from __future__ import annotations

import glob
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "epub"
TEXT = ROOT / "OEBPS" / "text"
STYLES = ROOT / "OEBPS" / "styles"
CHAPTER_RE = re.compile(r"chapter(\d{2,3})\.xhtml$")


def sheet_classes() -> set[str]:
    live: set[str] = set()
    for path in STYLES.glob("*.css"):
        css = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
        live.update(re.findall(r"\.([A-Za-z][A-Za-z0-9_-]*)", css))
    return live


def main() -> int:
    files = sorted(TEXT.glob("*.xhtml"))
    if not files:
        print("validate_tree: no XHTML files under epub/OEBPS/text", file=sys.stderr)
        return 1
    ok = True
    defined = sheet_classes()
    used: set[str] = set()
    parsed = 0
    for path in files:
        try:
            ET.parse(path)
            parsed += 1
        except ET.ParseError as exc:
            ok = False
            print(f"PARSE FAIL {path.name}: {exc}")
        source = path.read_text(encoding="utf-8")
        for value in re.findall(r'class="([^"]+)"', source):
            used.update(value.split())
    undefined = sorted(used - defined)
    if undefined:
        ok = False
        print(f"UNDEFINED CLASSES ({len(undefined)}): {', '.join(undefined)}")
    print(f"parsed OK: {parsed}/{len(files)} · undefined classes: {len(undefined)}")

    # Scan visible text only. The EPUB XML itself necessarily contains double quotes in attributes.
    cjk = re.compile(r"[\u2e80-\u312f\u3190-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]")
    straight = cjk_hits = 0
    for path in files:
        source = path.read_text(encoding="utf-8")
        body = re.sub(r"<[^>]+>", "", source)
        body = re.sub(r"&[A-Za-z][A-Za-z0-9#]*;", "", body)
        if '"' in body:
            n = body.count('"')
            straight += n
            print(f"STRAIGHT QUOTES {path.name}: {n}")
        matches = cjk.findall(body)
        if matches:
            cjk_hits += len(matches)
            print(f"CJK {path.name}: {''.join(matches[:20])}")
    print(f"straight quotes in prose: {straight} · CJK chars: {cjk_hits}")
    ok = ok and not straight and not cjk_hits

    # Resolve the href/src values used by XHTML pages. External links and fragment-only links are
    # intentionally ignored; manifest/CSS resolution is covered by workspace_audit.py.
    unresolved = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        for url in re.findall(r'(?:href|src)="([^"]+)"', source):
            if url.startswith(("http:", "https:", "mailto:", "#")):
                continue
            target = (path.parent / url.split("#", 1)[0]).resolve()
            if not target.is_file():
                unresolved.append(f"{path.name} -> {url}")
    if unresolved:
        ok = False
        print(f"UNRESOLVED REFS ({len(unresolved)}):")
        for ref in unresolved[:30]:
            print("  " + ref)
    else:
        print("unresolved XHTML refs: 0")

    chapter_paths = sorted((p for p in files if CHAPTER_RE.search(p.name)),
                          key=lambda path: int(CHAPTER_RE.search(path.name).group(1)))
    nums = [int(CHAPTER_RE.search(p.name).group(1)) for p in chapter_paths]
    if nums != list(range(1, len(nums) + 1)):
        ok = False
        print("CHAPTER SEQUENCE FAIL:", nums[:5], "…", nums[-5:])
    else:
        print(f"chapter sequence: 1–{len(nums)} contiguous")
    for path in chapter_paths:
        source = path.read_text(encoding="utf-8")
        if "stylesheet.css" not in source or "fonts.css" not in source:
            ok = False
            print(f"MISSING STYLESHEET LINK: {path.name}")

    print("validate_tree:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
