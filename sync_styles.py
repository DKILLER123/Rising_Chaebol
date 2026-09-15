#!/usr/bin/env python3
"""Fork the reader-supplied reference stylesheets into the book tree for
*Dominating South Korea: Starting with a Golden Trait*.

The reader's rule: `fonts.css` and `stylesheet.css` in the repository root are the fonts and
styles this book must use. They are reader-supplied reference files, so this script never edits
them — it installs copies into `work_epub/OEBPS/styles/` with:

  * the top banner relabelled for this book (the reference banner names the other novel, and a
    shipped stylesheet must not brand this edition with another title),
  * the reference novel's proper nouns and chapter-map provenance removed from CSS comments
    (house firewall: no content of that novel may appear in this book),
  * **every rule byte-identical**: the script compares the comment-stripped sheets line by line
    and fails on any difference, so "styles preserved exactly" is machine-proved.

Usage (from the repository root):  python3 sync_styles.py
Idempotent: re-running on a current tree reports `= … already current`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TREE_STYLES = ROOT / "work_epub" / "OEBPS" / "styles"

BANNER = """/* ═══════════════════════════════════════════════════════════════
   DOMINATING SOUTH KOREA: STARTING WITH A GOLDEN TRAIT · V1
   PUBLISHER-GRADE STYLESHEET (EPUB EDITION)
   Typography, block vocabulary and every rule are inherited byte-for-
   byte from the reader-supplied reference sheet in the repository root
   (stylesheet.css), which stays untouched. Nothing in a rule may be
   edited to suit one chapter: a genuinely new context gets a NEW
   numbered section under SKILL.md §6, never a mutation of an existing
   block. Load order: fonts.css FIRST, then this stylesheet.
   PROVENANCE: the section comments below were inherited from the
   reference sheet, whose cast, brands, song titles and chapter
   numbering are NOT this book's. "First used in the reference
   edition" marks a provenance line that has been genericized. This
   edition's chapters start at Chapter 1 from this book's own raws.
   ═══════════════════════════════════════════════════════════════ */
"""

FONTS_BANNER = """/* ═══════════════════════════════════════════════════════════════
   DOMINATING SOUTH KOREA: STARTING WITH A GOLDEN TRAIT · V1
   EMBEDDED FONTS (fonts.css)
   All typefaces bundled locally for offline EPUB rendering.
   Format: WOFF (application/font-woff — EPUB 3 core media type).
   The face set and every @font-face rule are inherited byte-for-byte
   from the reader-supplied reference fonts.css in the repository root.
   Families: Lora (body serif) · Crimson Pro (editorial serif) ·
   Cormorant Garamond (display) · IM Fell English (antique) ·
   Courier Prime (system/mono) · Caveat (handwriting) · Permanent
   Marker (hate-wall scrawl) · Cardo (chapter titles) · EB Garamond
   Italic (pullquotes) · Bebas Neue / Inter (introduction cards) ·
   Libre Baskerville (title fallback). 20 WOFF faces, reproducible with
   `python3 install_fonts.py`. All faces SIL OFL 1.1.
   FIGURE GUARD (measured at setup by `install_fonts.py --verify`,
   not inherited as folklore): the shipped latin subsets draw OLDSTYLE
   digits in Cormorant Garamond 600/700 and in both IM Fell English
   faces — their “1” is cut at x-height and reads as a capital “I”, so
   numerals never go in them. IM Fell has no lnum feature at all, so
   nothing could pin it, and Cormorant’s lnum cannot be trusted to
   survive an EPUB reader. Chapter titles are set in CARDO 700, which
   measures lining at cap height with no feature dependency, so
   “Chapter 3” renders upright everywhere. Lora, Crimson Pro, Inter,
   Courier Prime, Libre Baskerville and EB Garamond Italic all measure
   lining; Caveat measures “unclear” by design and is handwriting only.
   ═══════════════════════════════════════════════════════════════ */
"""

# Legacy proper nouns / plot provenance from the reference novel. Comments only — the table
# never touches a selector or a declaration. Applied to stylesheet.css only.
COMMENT_REWRITES: list[tuple[str, str]] = [
    ('so “Bae Joo-hyun, 161 Centimeters” renders',
     'so “Chapter 161 · 161 Centimeters” renders'),
    ("detective's findings on the T-ara affair.",
     "a detective's findings on one group's affair."),
    ("Returning for Ji-yeon's recovered night.",
     "Returning for a recovered night out."),
    ("The MC's full Dream Life attribute readout:",
     "The protagonist's full system attribute readout:"),
    ("Returning for the SUNYE release ledger.",
     "Returning for a release ledger."),
    ('Returning for "Balladeer Prince" on stage.',
     "Returning for a balladeer on stage."),
    ("Returning for the EIDER ambassadorship.",
     "Returning for a brand ambassadorship."),
    ("Returning for the partner confirmation and\n   the gift packs.",
     "Returning for a partnership confirmation\n   and its gift packs."),
    ("First used: Chapter 275 (lover development quest).",
     "First used in the reference edition."),
    ("First used: Chapter 290 (ECHO's three editions).",
     "First used in the reference edition."),
    ("First used: Chapter 291 (NOCT, second floor).",
     "First used in the reference edition."),
    ("Returning for the Happy Camp taping.",
     "Returning for a variety-show taping."),
    ("First used: Chapter 273 (Napa Valley shoot).",
     "First used in the reference edition."),
    ("Chapter 144 montage: one album, many cities.",
     "one album, many cities."),
    ("Built for Jiyeon’s yoga class in Chapter 277, and usable",
     "Built for a celebrity yoga class, and usable"),
]

# any remaining “First used (in|:) Chapter NNN (…)” provenance in a comment
FIRST_USED = re.compile(r"First used\s*(?:in|:)\s*Chapter\s+\d+[^.]*\.", re.S)


def strip_comments(css: str) -> str:
    """Comments out, keeping the exact byte layout of what remains."""
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), css, flags=re.S)


def rule_lines(css: str) -> list[str]:
    return [ln.rstrip() for ln in strip_comments(css).splitlines() if ln.strip()]


def banner_replaced(text: str, banner: str) -> str:
    m = re.match(r"\s*/\*.*?\*/\s*", text, flags=re.S)
    if not m:
        raise SystemExit("sync_styles: reference file has no leading banner comment")
    return banner + "\n" + text[m.end():]


def process(name: str, banner: str, rewrites: list[tuple[str, str]], out_dir: Path) -> int:
    src = (ROOT / name).read_text(encoding="utf-8")
    text = src
    for old, new in rewrites:
        if old not in text:
            print(f"  note: rewrite anchor not present, skipped: {old.strip()[:52]!r}")
            continue
        text = text.replace(old, new)
    text = FIRST_USED.sub("First used in the reference edition.", text)
    text = banner_replaced(text, banner)

    # firewall: nothing the reference novel invented may survive in a shipped asset
    residual = []
    try:
        sys.path.insert(0, str(ROOT))
        from legacy_firewall import HARD  # single source of the banned-token list

        for group, patterns in HARD.items():
            for pat in patterns:
                if re.search(pat, text, flags=re.I):
                    residual.append(f"{group}:{pat}")
    except ImportError:
        residual = re.findall(r"Taeyeon|Song Ji-?ho|LOEN|Dream Life|Girls\s*&\s*Peace", text)
    if residual:
        print(f"sync_styles: FAIL — reference-novel tokens remain in {name}: {sorted(set(residual))}")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / name
    if dest.is_file() and dest.read_text(encoding="utf-8") == text:
        print(f"  = {name} already current ({dest.stat().st_size:,} B)")
    else:
        dest.write_text(text, encoding="utf-8")
        print(f"  + {name} installed ({dest.stat().st_size:,} B)")

    ref_lines, new_lines = rule_lines(src), rule_lines(text)
    if ref_lines != new_lines:
        print(f"sync_styles: FAIL — rule text differs from the reference {name}")
        for i, (a, b) in enumerate(zip(ref_lines, new_lines)):
            if a != b:
                print(f"    rule line {i + 1}:\n      ref: {a!r}\n      new: {b!r}")
                break
        else:
            print(f"    length differs: reference {len(ref_lines)} lines vs installed {len(new_lines)}")
        return 1
    print(f"  ✓ {name}: {len(new_lines)} rule lines byte-identical to the reference")
    return 0


def main() -> int:
    rc = process("stylesheet.css", BANNER, COMMENT_REWRITES, TREE_STYLES)
    rc |= process("fonts.css", FONTS_BANNER, [], TREE_STYLES)
    print("sync_styles: PASS" if rc == 0 else "sync_styles: FAIL")
    return rc


if __name__ == "__main__":
    sys.exit(main())
