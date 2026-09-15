#!/usr/bin/env python3
"""Check that every class used in the book's XHTML actually exists in the stylesheets.

Why this gate exists: a style block whose container class is real but whose child
classes are invented still passes the tree validator, then renders as unstyled
paragraph text in the reader. The only cheap proof is to diff every class token in
work_epub/OEBPS/text against the union of selectors in styles/stylesheet.css,
styles/fonts.css and, when this edition has one, styles/edition.css.

Usage:  python3 check_classes.py [--json]
Exit:   0 clean, 1 unknown classes found.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
BOOK = ROOT / "work_epub" / "OEBPS"
# The inherited sheet and the font fork, plus any edition-owned stylesheet present.
STYLE_FILES = [p for p in (BOOK / "styles" / "stylesheet.css",
                           BOOK / "styles" / "fonts.css",
                           BOOK / "styles" / "edition.css") if p.exists()]

CLASS_DECL = re.compile(r"\.([A-Za-z][A-Za-z0-9_-]*)")
USED = re.compile(r'class="([^"]*)"')


def declared_classes():
    live = set()
    for path in STYLE_FILES:
        if not path.exists():
            sys.exit(f"missing stylesheet: {path}")
        css = path.read_text(encoding="utf-8")
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        # only trust classes that appear on the left-hand side of a rule
        for sel in re.findall(r"([^{}]+)\{", css):
            if sel.strip().startswith("@"):
                continue
            live.update(CLASS_DECL.findall(sel))
    return live


def main():
    as_json = "--json" in sys.argv
    live = declared_classes()
    report = {}
    for page in sorted((BOOK / "text").glob("*.xhtml")):
        bad = {}
        for attr in USED.findall(page.read_text(encoding="utf-8")):
            for token in attr.split():
                if token not in live:
                    bad[token] = bad.get(token, 0) + 1
        if bad:
            report[page.name] = dict(sorted(bad.items(), key=lambda kv: (-kv[1], kv[0])))
    if as_json:
        print(json.dumps({"unknown_classes": report, "stylesheets_checked": [p.name for p in STYLE_FILES]}))
    else:
        if report:
            print(f"UNKNOWN CLASSES in {len(report)} page(s) (not declared in any stylesheet):")
            for name, tokens in report.items():
                print(f"  {name}")
                for tok, n in tokens.items():
                    print(f"      .{tok}  x{n}")
        else:
            print(f"classes OK — every class token in {len(list((BOOK / 'text').glob('*.xhtml')))} pages is declared in the stylesheets")
    return 1 if report else 0


if __name__ == "__main__":
    sys.exit(main())
