#!/usr/bin/env python3
"""Measure style-block coverage across the Peninsula chapter XHTML files.

This reports under-dressed chapters for human review; it does not rewrite prose. The thresholds
follow SKILL.md's style-block maximization rule.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEXT = ROOT / "epub" / "OEBPS" / "text"
CSS = ROOT / "epub" / "OEBPS" / "styles" / "stylesheet.css"
CH_RE = re.compile(r"^chapter(\d{2,3})\.xhtml$")
CLASS_RE = re.compile(r'class="([^"]+)"')
FURNITURE = {"page-wrapper", "chapter-header"}
FRONT_ONLY = {"char-card", "char-bio", "char-infobox", "toc-wrap", "cover-shell", "cover-overlay",
              "cover-body", "title-shell", "title-content", "title-vignette"}
REPEAT_OK = {"system-block", "scene-break", "char-intro-block", "location-stamp", "pullquote",
             "notification", "dialogue-line", "thought"}


def block_classes() -> set[str]:
    css = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
    out = set()
    for group in re.findall(r"([^{}]+)\{", css):
        for selector in group.split(","):
            selector = selector.strip()
            match = re.match(r"^\.([A-Za-z][\w-]*)(?:\s|:|$)", selector)
            if match and " " in selector:
                out.add(match.group(1))
    return out - FURNITURE - FRONT_ONLY


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json")
    parser.add_argument("--min-types", type=int, default=8)
    args = parser.parse_args()
    universe = block_classes()
    chapters = sorted((p for p in TEXT.glob("chapter*.xhtml") if CH_RE.match(p.name)), key=lambda p: p.name)
    if not chapters:
        print("style_audit: no chapters found")
        return 1
    rows, problems = [], []
    for page in chapters:
        source = page.read_text(encoding="utf-8")
        visible = re.sub(r"<[^>]+>", " ", source)
        words = len(re.findall(r"[A-Za-z]+(?:[’'-][A-Za-z]+)*", visible))
        counts = collections.Counter(token for value in CLASS_RE.findall(source)
                                      for token in value.split() if token in universe)
        distinct = len(counts)
        ratio = sum(counts.values()) / max(words, 1)
        repeats = sorted(name for name, count in counts.items() if count > 1 and name not in REPEAT_OK)
        row = {"chapter": page.name, "prose_words": words, "blocks": sum(counts.values()),
               "distinct_types": distinct, "blocks_per_1k_words": round(ratio * 1000),
               "used": ", ".join(sorted(counts)), "unused": ", ".join(sorted(universe - set(counts)))}
        rows.append(row)
        if distinct < args.min_types:
            problems.append(f"{page.name}: {distinct} distinct style blocks (floor {args.min_types})")
        if ratio > 0.25:
            problems.append(f"{page.name}: {ratio:.2f} blocks per prose word — over-carded")
        if repeats:
            problems.append(f"{page.name}: repeated non-repeat-safe blocks: {', '.join(repeats)}")
    for row in rows:
        print(f"== {row['chapter']} · {row['prose_words']} words · {row['blocks']} blocks · {row['distinct_types']} types")
        print(f"   used: {row['used']}")
    if args.json:
        out = Path(args.json)
        out = out if out.is_absolute() else ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"chapters": rows, "problems": problems}, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"style_audit: {'PASS' if not problems else 'REVIEW'} ({len(problems)} note(s))")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
