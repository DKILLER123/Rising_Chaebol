#!/usr/bin/env python3
"""style_audit.py — is every chapter dressed in the stylesheet, and is the dressing varied?

The inherited sheet ships dozens of scene-type blocks (§8–§56). A chapter translated as nothing
but `<p>` blocks is legal markup and a flat read at the same time, so this gate measures the
ratio per chapter and prints the block vocabulary a chapter never touched.

Rules of thumb this edition holds itself to:
  * at least 8 distinct style-block types per chapter;
  * body prose kept above roughly 4 style blocks in 5 (blocks <= 0.25 x prose);
  * no block type used twice inside one chapter unless it is the same device recurring
    legitimately (system panels for entry cards, scene breaks, char-intro cards);
  * every interrogative in the raw keeps a question mark (checked by audit_marks.py).

Usage (from the repository root):
    python3 style_audit.py                 # all chapters
    python3 style_audit.py --json reports/style_audit.json

Exit 0 = every chapter clears the floor. Exit 1 = a chapter is under-dressed or repeats a
block type the sheet already used for a different purpose in the same chapter.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEXT = ROOT / "work_epub" / "OEBPS" / "text"
CSS = ROOT / "work_epub" / "OEBPS" / "styles" / "stylesheet.css"

# The block containers the sheet defines, minus page furniture counted separately.
FURNITURE = {'page-wrapper', 'chapter-header'}
# Front-matter containers: they belong to a page type, not to a chapter's wardrobe.
FRONT_ONLY = {'char-card', 'char-bio', 'char-infobox', 'glossary-card', 'glossary-deck',
              'glossary-footer', 'glossary-grid', 'glossary-hero', 'glossary-index',
              'glossary-kicker', 'glossary-note', 'glossary-rule', 'glossary-section',
              'glossary-update', 'glossary-wrap', 'toc-wrap', 'placement-reel',
              'cover-shell', 'cover-overlay', 'cover-body'}
# Devices that may legitimately repeat within a chapter.
REPEAT_OK = {'system-block', 'scene-break', 'char-intro-block', 'location-stamp', 'char-card',
             'author-aside', 'pullquote', 'notification'}

CH_RE = re.compile(r'^ch(\d{3})\.xhtml$')
CLASS_RE = re.compile(r'class="([^"]+)"')


def block_classes():
    """Container classes = classes that appear as a descendant selector root in the sheet."""
    css = re.sub(r'/\*.*?\*/', '', CSS.read_text(encoding='utf-8'), flags=re.S)
    blocks = set()
    for sel in re.findall(r'([^{}]+)\{', css):
        for part in sel.split(','):
            part = part.strip()
            m = re.match(r'^\.([A-Za-z][\w-]*)(?:\s|:|$)', part)
            if m and ' ' in part:
                blocks.add(m.group(1))
    return {b for b in blocks if b not in FURNITURE and b not in FRONT_ONLY}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=None)
    ap.add_argument('--min-types', type=int, default=8)
    args = ap.parse_args()

    universe = block_classes()
    chapters = sorted((p for p in TEXT.glob('ch*.xhtml') if CH_RE.match(p.name)),
                      key=lambda p: p.name)
    if not chapters:
        print('style_audit: no chapters translated yet — nothing to dress')
        return 0

    report, problems = [], []
    for page in chapters:
        src = page.read_text(encoding='utf-8')
        prose_words = len(re.findall(r'\w+', re.sub(r'<[^>]+>', ' ', src)))
        counts = collections.Counter()
        for attr in CLASS_RE.findall(src):
            for token in attr.split():
                if token in universe:
                    counts[token] += 1
        blocks_total = sum(counts.values())
        distinct = len(counts)
        ratio = (blocks_total / prose_words) if prose_words else 0
        repeats = sorted(k for k, v in counts.items() if v > 1 and k not in REPEAT_OK)
        report.append({'chapter': page.name, 'prose_words': prose_words, 'blocks': blocks_total,
                       'distinct_types': distinct, 'blocks_per_1k_words': round(ratio * 1000),
                       'used': ', '.join(sorted(counts)),
                       'unused': ', '.join(sorted(universe - set(counts)))})
        if distinct < args.min_types:
            problems.append(f'{page.name}: only {distinct} distinct style blocks (floor {args.min_types})')
        if ratio > 0.25:
            problems.append(f'{page.name}: {ratio:.2f} blocks per prose word — over-carded, thin on prose')
        if repeats:
            problems.append(f'{page.name}: block type repeated in one chapter: {", ".join(repeats)}')

    for row in report:
        print(f"== {row['chapter']} · {row['prose_words']} words · {row['blocks']} style blocks "
              f"({row['blocks_per_1k_words']}/1k words) · {row['distinct_types']} distinct types")
        print(f"   used:   {row['used']}")
        print(f"   unused: {row['unused']}")
    if problems:
        print('\n'.join(f'  !! {p}' for p in problems))
        print(f'style_audit: REVIEW ({len(problems)} note(s))')
    else:
        print(f'style_audit: PASS ({len(chapters)} chapter(s))')

    if args.json:
        out = Path(args.json)
        out = out if out.is_absolute() else ROOT / out
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({'chapters': report, 'problems': problems}, indent=2), encoding='utf-8')
        print(f'report: {out.relative_to(ROOT)}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
