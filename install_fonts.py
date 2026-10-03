#!/usr/bin/env python3
"""Install or verify the 17 WOFF faces used by the Peninsula EPUB.

If matching ``@fontsource`` packages are installed, missing/outdated faces are copied into
``epub/OEBPS/fonts/``. Existing extracted faces are accepted when the npm packages are absent, so
workspace setup remains offline-safe. Use ``--verify`` for fontTools glyph checks.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULES = ROOT / "node_modules" / "@fontsource"
DEST = ROOT / "epub" / "OEBPS" / "fonts"
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
}
CRITICAL = "‘’“”—–…·"


def font_report(path: Path) -> dict[str, object]:
    from fontTools.ttLib import TTFont
    with TTFont(path, lazy=False) as font:
        cmap = font.getBestCmap() or {}
        missing = [char for char in CRITICAL if ord(char) not in cmap]
        return {"bytes": path.stat().st_size, "codepoints": len(cmap), "missing_critical": missing}


def main() -> int:
    verify = "--verify" in sys.argv
    DEST.mkdir(parents=True, exist_ok=True)
    copied, unchanged, unavailable = [], [], []
    for target, (package, stem) in FACES.items():
        source = MODULES / package / "files" / f"{stem}.woff"
        dest = DEST / target
        if source.is_file() and source.read_bytes()[:4] == b"wOFF":
            if dest.is_file() and dest.read_bytes() == source.read_bytes():
                unchanged.append(target)
            else:
                shutil.copyfile(source, dest)
                copied.append(target)
        elif dest.is_file() and dest.read_bytes()[:4] == b"wOFF":
            unchanged.append(target + " (extracted baseline)")
        else:
            unavailable.append(f"{target} — install @fontsource/{package}")

    css = DEST.parent / "styles" / "fonts.css"
    declared = re.findall(r"url\(\s*\.\./fonts/([^)'\"\s]+)", css.read_text(encoding="utf-8")) if css.is_file() else []
    dangling = sorted({name for name in declared if not (DEST / name).is_file()})
    report: dict[str, object] = {"dest": str(DEST.relative_to(ROOT)), "expected": len(FACES),
                                "copied": copied, "unchanged": unchanged,
                                "packages_unavailable": unavailable, "declared": len(declared),
                                "dangling": dangling}
    verification_skipped = False
    if verify:
        try:
            report["verification"] = {name: font_report(DEST / name) for name in FACES
                                       if (DEST / name).is_file()}
        except ImportError as exc:
            verification_skipped = True
            report["verification_error"] = str(exc)
            print(f"  glyph check skipped: {exc}")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "fonts_install.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"install_fonts: {len(copied)} copied, {len(unchanged)} current, {len(FACES)} expected")
    if unavailable:
        print("  offline/unavailable: " + "; ".join(unavailable))
    if dangling or unavailable and len(unchanged) + len(copied) < len(FACES):
        print("install_fonts: FAIL")
        return 1
    print(f"  fonts.css declares {len(declared)} faces; all resolve")
    if verify and not verification_skipped:
        missing = {k: v["missing_critical"] for k, v in report.get("verification", {}).items() if v["missing_critical"]}
        print("  glyph check:", "PASS" if not missing else f"FAIL {missing}")
        if missing:
            return 1
    elif verify:
        print("  glyph check: SKIPPED (install requirements-audit.txt to run fontTools)")
    print("install_fonts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
