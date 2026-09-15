#!/usr/bin/env python3
"""Stylebook index — lists every numbered section of the book stylesheet and the class
vocabulary each one defines, with the CSS line where it is first declared.

Read-only: writes reports/style_index.tsv and reports/style_index.md, never the book.
Run from the repository root:  python3 style_index.py

Why this exists: SKILL.md §6 says "grep the stylesheet for an existing block first". This
index makes that one command instead of a 4,700-line scroll, and it is the authority for
which class names are legal (validate_tree.py fails any class not defined here).
"""
from __future__ import annotations

import csv
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHEETS = [ROOT / "work_epub" / "OEBPS" / "styles" / "stylesheet.css",
          ROOT / "work_epub" / "OEBPS" / "styles" / "fonts.css"]
REPORTS = ROOT / "reports"
BLOCK_COMMENT = re.compile(r"/\*(?P<body>.*?)\*/", re.S)
SECTION_TITLE = re.compile(r"^\s*\d{2}\s*[·-]\s*(?P<title>.+?)\s*$", re.M)


def sheets_text() -> tuple[str, str]:
    """Return (stylesheet text, mapping line-numbered for reporting)."""
    out, notes = "", {}
    for sheet in SHEETS:
        if not sheet.is_file():
            continue
        text = sheet.read_text(encoding="utf-8")
        notes[f"__file__{sheet.name}"] = text.count("\n") + 1
        # pad so line numbers of the stylesheet survive concatenation
        out += text + "\n"
    return out, notes


def sectionize(text: str) -> "OrderedDict[str, dict]":
    """Split on the house banner comments; collect class names per section."""
    sections: "OrderedDict[str, dict]" = OrderedDict()
    current = "00 · UNNUMBERED PROLOGUE"
    sections[current] = {"title": current, "classes": OrderedDict(), "first_line": 1,
                         "blurb": "", "selector_count": 0}
    pos = 0
    line_of = 1
    for m in BLOCK_COMMENT.finditer(text):
        body = m.group("body").strip()
        line = text.count("\n", 0, m.start()) + 1
        title = None
        # Section banners look like:  ──── \n 04 · CHAPTER HEADER (V4) \n ────
        if "·" in body and SECTION_TITLE.search(body):
            title = next(s.strip() for s in body.splitlines() if SECTION_TITLE.match(s))
        if title:
            blurb = " ".join(
                s.strip() for s in body.splitlines()
                if s.strip() and "─" not in s and "═" not in s and not SECTION_TITLE.match(s)
                and "·" not in s
            )
            current = title
            sections.setdefault(current, {"title": current, "classes": OrderedDict(),
                                          "first_line": line, "blurb": blurb,
                                          "selector_count": 0})
            sections[current]["first_line"] = line
            if blurb:
                sections[current]["blurb"] = blurb
        pos = m.end()
        line_of = line
    # second pass: assign classes to the section that precedes each rule
    stripped = BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    boundaries = sorted(((s["first_line"], name) for name, s in sections.items()))

    def owner(line: int) -> str:
        name = boundaries[0][1]
        for bl, n in boundaries:
            if line >= bl:
                name = n
            else:
                break
        return name

    for m in re.finditer(r"[.#][A-Za-z][A-Za-z0-9_-]*", stripped):
        line = stripped.count("\n", 0, m.start()) + 1
        name = owner(line)
        token = m.group(0)
        if token.startswith("."):
            cls = token[1:]
            sections[name]["classes"].setdefault(cls, line)
        sections[name]["selector_count"] += 1
    return sections


def check_skill(all_classes: set[str]) -> int:
    """--check-skill: every class token SKILL.md §5 cites must exist in the sheet.

    A playbook that names a class the stylesheet does not define teaches every future cycle to
    write markup that fails validate_tree.py, so the citation list is verified, not trusted.
    """
    skill = ROOT / "SKILL.md"
    if not skill.is_file():
        print("style_index: SKILL.md not found, nothing to check")
        return 0
    text = skill.read_text(encoding="utf-8")
    try:
        start = text.index("## 5 ·")
        end = text.index("## 6 ·", start)
    except ValueError:
        print("style_index: FAIL — SKILL.md has no §5/§6 boundary to check")
        return 1
    section = text[start:end]
    cited = {t.strip() for t in re.findall(r"`([A-Za-z][A-Za-z0-9_-]*)`", section)}
    prose = {"the", "and", "for", "with", "text", "name", "line", "body", "note", "sub", "title",
             "header", "label", "value", "values", "class", "classes", "block", "variant", "variants"}
    unknown = sorted(c for c in cited if c not in all_classes and c not in prose)
    if unknown:
        print(f"style_index: FAIL — SKILL.md §5 cites classes the stylesheet does not define: {unknown}")
        print("             fix the citation or add the block under §6; validate_tree.py would reject the markup")
        return 1
    print(f"style_index: SKILL.md §5 cites {len(cited)} tokens, all defined in the sheet — PASS")
    return 0


def main() -> int:
    text, _ = sheets_text()
    if not text.strip():
        print("style_index: no stylesheet found under work_epub/OEBPS/styles — nothing to index")
        return 1
    sections = sectionize(text)
    REPORTS.mkdir(exist_ok=True)
    rows = []
    for name, sec in sections.items():
        rows.append({
            "section": name,
            "css_line": sec["first_line"],
            "selectors": sec["selector_count"],
            "classes": ", ".join(sorted(sec["classes"])),
            "blurb": sec["blurb"][:400],
        })
    with (REPORTS / "style_index.tsv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    all_classes = sorted({c for s in sections.values() for c in s["classes"]})
    md = ["# Stylesheet index (generated by `python3 style_index.py`)",
          "",
          f"Sections: {len(sections)} · distinct classes: {len(all_classes)}",
          "",
          "| Section | First used at | Selectors | Classes |",
          "|---|---:|---:|---|"]
    for row in rows:
        classes = row["classes"] or "—"
        md.append(f"| {row['section']} | L{row['css_line']} | {row['selectors']} | {classes} |")
    md += ["", "## Full class vocabulary", "", "```text"]
    for i in range(0, len(all_classes), 6):
        md.append("  " + "  ".join(all_classes[i:i + 6]))
    md.append("```")
    (REPORTS / "style_index.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    if "--check-skill" in sys.argv:
        return check_skill(set(all_classes))
    print(f"style_index: {len(sections)} sections, {len(all_classes)} classes "
          f"→ reports/style_index.tsv, reports/style_index.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
