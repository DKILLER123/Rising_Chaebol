#!/usr/bin/env python3
"""Install the embedded WOFF faces for this book from the locally vendored @fontsource
packages into work_epub/OEBPS/fonts/, under the house file names fonts.css expects.

Why a script and not manual copies: fonts.css references 20 faces by exact file name, the
jsdelivr/GStatic CDNs are unreachable from this sandbox, and every future cycle must be able
to reproduce the face set bit-for-bit from npm.

Usage (from the repository root):
    npm install --no-audit --no-fund @fontsource/<family>...   # or: npm run fonts
    python3 install_fonts.py            # copy + report
    python3 install_fonts.py --verify   # additionally check glyph coverage with fontTools

Face set (identical to the reference book's 20 faces, per the reader's directive that
fonts.css/stylesheet.css define this book's typography):
    Lora 400/400i/700 · Crimson Pro 400/400i/600 · Cormorant Garamond 600/700 ·
    IM Fell English 400/400i · Courier Prime 400/700 · Caveat 400/600 ·
    Permanent Marker 400 · Bebas Neue 400 · Inter 400 · Libre Baskerville 700 ·
    Cardo 700 · EB Garamond 400i
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULES = ROOT / "node_modules" / "@fontsource"
DEST = ROOT / "work_epub" / "OEBPS" / "fonts"

# house file name -> (package, fontsource latin file stem)
FACES: dict[str, tuple[str, str]] = {
    "Lora-400.woff": ("lora", "lora-latin-400-normal"),
    "Lora-400i.woff": ("lora", "lora-latin-400-italic"),
    "Lora-700.woff": ("lora", "lora-latin-700-normal"),
    "CrimsonPro-400.woff": ("crimson-pro", "crimson-pro-latin-400-normal"),
    "CrimsonPro-400i.woff": ("crimson-pro", "crimson-pro-latin-400-italic"),
    "CrimsonPro-600.woff": ("crimson-pro", "crimson-pro-latin-600-normal"),
    "CormorantGaramond-600.woff": ("cormorant-garamond", "cormorant-garamond-latin-600-normal"),
    "CormorantGaramond-700.woff": ("cormorant-garamond", "cormorant-garamond-latin-700-normal"),
    "IMFellEnglish-400.woff": ("im-fell-english", "im-fell-english-latin-400-normal"),
    "IMFellEnglish-400i.woff": ("im-fell-english", "im-fell-english-latin-400-italic"),
    "CourierPrime-400.woff": ("courier-prime", "courier-prime-latin-400-normal"),
    "CourierPrime-700.woff": ("courier-prime", "courier-prime-latin-700-normal"),
    "Caveat-400.woff": ("caveat", "caveat-latin-400-normal"),
    "Caveat-600.woff": ("caveat", "caveat-latin-600-normal"),
    "PermanentMarker-400.woff": ("permanent-marker", "permanent-marker-latin-400-normal"),
    "BebasNeue-400.woff": ("bebas-neue", "bebas-neue-latin-400-normal"),
    "Inter-400.woff": ("inter", "inter-latin-400-normal"),
    "LibreBaskerville-700.woff": ("libre-baskerville", "libre-baskerville-latin-700-normal"),
    "Cardo-700.woff": ("cardo", "cardo-latin-700-normal"),
    "EBGaramond-400i.woff": ("eb-garamond", "eb-garamond-latin-400-italic"),
}

# Glyphs the house CSS paints through ::before content or requires in prose.
CRITICAL = {"\u2018": "‘", "\u2019": "’", "\u201c": "“", "\u201d": "”",
            "\u2013": "–", "\u2014": "—", "\u2026": "…", "\u00b7": "·",
            "\u00a0": "nbsp"}
BODIES = ["\u2033", "\u2032", "\u2022"]  # prime/double-prime/bullet, seen in prose


def verify(path: Path) -> dict:
    """Decode the face, then measure the two things the house rules depend on.

    1. Critical glyphs: curly quotes, apostrophe, en/em dash, ellipsis, middot (prose) — a missing
       one silently changes what the reader sees.
    2. Figure style: chapter titles must use LINING digits. An oldstyle face draws "1" at x-height
       and it reads as a capital "I" (this is why Cardo won the title slot and EB Garamond /
       Cormorant did not). Measured from glyph bounds, not assumed from the family name.
    """
    from fontTools.ttLib import TTFont  # only when --verify, so the copy step needs no venv

    out: dict[str, object] = {}
    with TTFont(path, lazy=False) as font:
        cmap = font.getBestCmap() or {}
        out["codepoints"] = len(cmap)
        out["missing_critical"] = [label for cp, label in CRITICAL.items() if ord(cp) not in cmap]
        out["extra_missing"] = [f"U+{ord(ch):04X}" for ch in BODIES if ord(ch) not in cmap]
        out["tables"] = sorted(font.keys())
        # GSUB features decide whether a figure style can be pinned by font-feature-settings,
        # which is what "the latin subset carries no lnum" actually means. Measured per face.
        features: set[str] = set()
        if "GSUB" in font:
            try:
                records = font["GSUB"].table.FeatureList.FeatureRecord or []
                features = {r.FeatureTag.strip() for r in records}
            except Exception as exc:  # noqa: BLE001 - a broken table is reported, never guessed
                features = set()
                out["gsub_error"] = f"{type(exc).__name__}: {exc}"
        out["features"] = sorted(features)
        out["has_lnum"] = "lnum" in features
        out["has_onum"] = "onum" in features
        digits = [cmap.get(ord(d)) for d in "0123456789"]
        out["digits_present"] = all(digits)
        wanted = {c: cmap.get(ord(c)) for c in ("1", "H", "x")}
        if all(wanted.values()):
            try:
                from fontTools.pens.boundsPen import BoundsPen

                glyphs = font.getGlyphSet()

                def y_max(ch: str) -> tuple[float, float]:
                    pen = BoundsPen(glyphs)
                    glyphs[wanted[ch]].draw(pen)
                    x_min, _y_min, x_max, y_top = pen.bounds or (0, 0, 0, 0)
                    return y_top, x_max - x_min

                cap, xh, digit = y_max("H"), y_max("x"), y_max("1")
                out["cap_height"], out["x_height"], out["digit_top"] = cap[0], xh[0], digit[0]
                if digit[0] >= cap[0] * 0.92:
                    out["figures"] = "lining"
                elif digit[0] <= xh[0] * 1.08:
                    out["figures"] = "oldstyle"
                else:
                    out["figures"] = "unclear"
            except Exception as exc:  # report, never guess
                out["figures_error"] = f"{type(exc).__name__}: {exc}"
        else:
            out["figures"] = "unmeasurable"
    return out


def main() -> int:
    verify_flag = "--verify" in sys.argv
    DEST.mkdir(parents=True, exist_ok=True)
    copied, skipped, missing_pkg = [], [], []
    for target, (pkg, stem) in FACES.items():
        src = MODULES / pkg / "files" / f"{stem}.woff"
        if not src.is_file():
            missing_pkg.append(f"{pkg} (npm install @fontsource/{pkg})")
            continue
        data = src.read_bytes()
        if data[:4] != b"wOFF":
            missing_pkg.append(f"{src.name}: not a WOFF file")
            continue
        dest = DEST / target
        if dest.is_file() and dest.read_bytes() == data:
            skipped.append(target)
            continue
        dest.write_bytes(data)
        copied.append(f"{target} ({len(data):,} B)")

    # fonts.css is the contract: every url() it declares must exist on disk
    css = (ROOT / "work_epub" / "OEBPS" / "styles" / "fonts.css")
    declared = []
    if css.is_file():
        declared = re.findall(r"url\(\s*\.\./fonts/([^)\s'\"]+)", css.read_text(encoding="utf-8"))
    undeclared = sorted(set(declared) - set(FACES))
    dangling = sorted(f for f in declared if not (DEST / f).is_file())

    report: dict[str, object] = {"dest": str(DEST.relative_to(ROOT)), "faces": len(FACES),
                                "copied": copied, "unchanged": skipped,
                                "packages_missing": sorted(set(missing_pkg)),
                                "declared_in_fonts_css": len(declared),
                                "undeclared_by_fonts_css": undeclared,
                                "dangling_after_copy": dangling}
    if verify_flag:
        report["verification"] = {t: verify(DEST / t) for t in FACES if (DEST / t).is_file()}
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "fonts_install.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"install_fonts: {len(copied)} copied, {len(skipped)} already current, "
          f"{len(FACES)} faces expected")
    for line in copied:
        print(f"  + {line}")
    if missing_pkg:
        print("  ! packages/files missing:\n    " + "\n    ".join(sorted(set(missing_pkg))))
    if undeclared:
        print(f"  ! faces present in the mapping but not referenced by fonts.css: {undeclared}")
    if dangling:
        print(f"  FAIL fonts.css references files that do not exist: {dangling}")
        return 1
    if missing_pkg:
        return 1
    print(f"  fonts.css declares {len(declared)} faces; all resolve under {DEST.relative_to(ROOT)}/")
    if verify_flag:
        bad = [k for k, v in report["verification"].items() if v.get("missing_critical")]
        print(f"  glyph check: {'ALL OK' if not bad else 'MISSING CRITICAL IN ' + ', '.join(bad)}")
        if bad:
            return 1
        print("  figure check (measured digit height vs cap/x-height, and pinning features):")
        for k, v in sorted(report["verification"].items()):
            print(f"    {k:30s} {str(v.get('figures')):12s} lnum={str(v.get('has_lnum')):5s} "
                  f"onum={v.get('has_onum')}")
        title = report["verification"].get("Cardo-700.woff", {})
        if title.get("figures") != "lining":
            print("  FAIL the chapter-title face must draw lining digits (see SKILL.md §6.4)")
            return 1
        print("  title face Cardo 700: lining as required")
    print("install_fonts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
