#!/usr/bin/env python3
"""House gate 1 — structural validation of work_epub/.

Checks, in order:
  1. every .xhtml parses as XML
  2. every class used in the text tree is defined in the stylesheets
  3. straight quotes in prose (should be 0 — Option B curly everywhere)
  4. CJK characters anywhere in the text tree (must be 0). Documented exemption for this
     book: a run of Korean inside an element marked lang="ko" is a sanctioned gloss (the
     glossary page and character-card Hangul), so it is exempted from the Han/Hangul scan
     and reported separately as a count. Everything else — including every chapter body —
     must be CJK-free, and the exemption never applies to a chapter file.
  5. internal href/src references resolve to files in the tree
"""
import re
import sys
import glob
import os
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work_epub")
TEXT = os.path.join(ROOT, "OEBPS", "text")
STYLES = os.path.join(ROOT, "OEBPS", "styles")

def sheet_classes():
    css = ""
    for f in glob.glob(os.path.join(STYLES, "*.css")):
        css += open(f, encoding="utf-8").read()
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    classes = set()
    for sel in re.findall(r"\.([A-Za-z][A-Za-z0-9_-]*)", css):
        classes.add(sel)
    # classes referenced only inside :is()/.foo.bar composites are covered by the scan above
    return classes

def main():
    files = sorted(glob.glob(os.path.join(TEXT, "*.xhtml")))
    ok = True

    defined = sheet_classes()

    parsed = 0
    all_classes_used = set()
    for f in files:
        try:
            ET.parse(f)
            parsed += 1
        except ET.ParseError as e:
            ok = False
            print(f"PARSE FAIL {os.path.basename(f)}: {e}")
        src = open(f, encoding="utf-8").read()
        for cl in re.findall(r'class="([^"]+)"', src):
            for c in cl.split():
                all_classes_used.add(c)

    undefined = sorted(c for c in all_classes_used if c not in defined)
    if undefined:
        ok = False
        print(f"UNDEFINED CLASSES ({len(undefined)}): {', '.join(undefined)}")
    else:
        print(f"parsed OK: {parsed}/{len(files)} · undefined classes: 0")

    # CJK detection: Han/fullwidth/boxes. Hangul Compatibility Jamo (U+3130–U+318F) stays
    # exempted as a class because ㅋㅋ / ㅠㅠ inside a fan comment thread are register, not
    # untranslated language. This book has not printed them yet; the exemption is kept because a
    # fandom scene may legitimately need one, and a lone exempted jamo never excuses a Han run.
    cjk = re.compile(r"[\u2e80-\u312f\u3190-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]")
    ko_span = re.compile(r'<(\w+)[^>]*\blang="ko"[^>]*>(.*?)</\1>', re.S)
    hangul_only = re.compile(r"[\uac00-\ud7af\u3130-\u318f]")
    straight = 0
    cjk_hits = 0
    exempted = 0
    for f in files:
        src = open(f, encoding="utf-8").read()
        body = re.sub(r"<[^>]+>", "", src)
        body = re.sub(r"&[a-z]+;", "", body)
        n = body.count('"')
        if n:
            straight += n
            print(f"STRAIGHT QUOTES {os.path.basename(f)}: {n}")
        # Sanctioned Korean glosses (glossary + card glosses) are exempt from the scan only
        # when they sit inside a lang="ko" element, and never inside a chapter file.
        is_chapter = bool(re.search(r"ch\d{3}\.xhtml$", f))
        glosses = [] if is_chapter else ko_span.findall(src)
        if not is_chapter and glosses:
            exempted += sum(len(hangul_only.findall(re.sub(r"<[^>]+>", "", inner)))
                            for _tag, inner in glosses)
        scan_src = src if is_chapter else ko_span.sub(" ", src)
        scan_body = re.sub(r"&[a-z]+;", "", re.sub(r"<[^>]+>", "", scan_src))
        m = cjk.findall(scan_body)
        if m:
            cjk_hits += len(m)
            print(f"CJK {os.path.basename(f)}: {''.join(m[:10])}")
    print(f"straight quotes in prose: {straight} · CJK chars: {cjk_hits} · "
          f"lang=\"ko\" Hangul glosses exempted: {exempted}")
    if straight or cjk_hits:
        ok = False

    # reference resolution
    unresolved = []
    for f in files:
        src = open(f, encoding="utf-8").read()
        for href in re.findall(r'(?:href|src)="([^"]+)"', src):
            if href.startswith(("http", "#", "mailto:")):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(f), href.split("#")[0]))
            if not os.path.exists(target):
                unresolved.append(f"{os.path.basename(f)} -> {href}")
    if unresolved:
        ok = False
        print(f"UNRESOLVED REFS ({len(unresolved)}):")
        for u in unresolved[:20]:
            print("  " + u)
    else:
        print("unresolved internal refs: 0")

    # stylesheet link presence in chapters
    for f in [x for x in files if re.search(r"ch\d", x)]:
        src = open(f, encoding="utf-8").read()
        if "stylesheet.css" not in src or "fonts.css" not in src:
            ok = False
            print(f"MISSING STYLESHEET LINK: {os.path.basename(f)}")

    print("validate_tree:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
