#!/usr/bin/env python3
"""Generate a compact index of the book-owned CSS class vocabulary."""
from __future__ import annotations

import csv
import re
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHEETS = [ROOT / "epub" / "OEBPS" / "styles" / "stylesheet.css",
          ROOT / "epub" / "OEBPS" / "styles" / "fonts.css"]
REPORTS = ROOT / "reports"
SECTION_TITLE = re.compile(r"^\s*(\d{2})\s*[·-]\s*(.+?)\s*$", re.M)


def index_sections(text: str) -> OrderedDict[str, dict]:
    sections: OrderedDict[str, dict] = OrderedDict()
    current = "00 · UNNUMBERED PROLOGUE"
    sections[current] = {"first_line": 1, "classes": set(), "selectors": 0}
    boundaries = [(1, current)]
    for match in re.finditer(r"/\*(?P<body>.*?)\*/", text, re.S):
        title = SECTION_TITLE.search(match.group("body"))
        if title:
            current = f"{title.group(1)} · {title.group(2).strip()}"
            sections.setdefault(current, {"first_line": text.count("\n", 0, match.start()) + 1,
                                          "classes": set(), "selectors": 0})
            boundaries.append((sections[current]["first_line"], current))
    stripped = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    boundaries.sort()
    for match in re.finditer(r"([^{}]+)\{", stripped):
        line = stripped.count("\n", 0, match.start()) + 1
        owner = boundaries[0][1]
        for boundary, name in boundaries:
            if line >= boundary:
                owner = name
            else:
                break
        section = sections[owner]
        section["selectors"] += 1
        section["classes"].update(re.findall(r"\.([A-Za-z][A-Za-z0-9_-]*)", match.group(1)))
    return sections


def main() -> int:
    existing = [p for p in SHEETS if p.is_file()]
    if not existing:
        print("style_index: no stylesheets under epub/OEBPS/styles", file=sys.stderr)
        return 1
    text = "\n".join(p.read_text(encoding="utf-8") for p in existing)
    sections = index_sections(text)
    REPORTS.mkdir(exist_ok=True)
    rows = [{"section": name, "css_line": data["first_line"], "selectors": data["selectors"],
             "classes": ", ".join(sorted(data["classes"]))} for name, data in sections.items()]
    with (REPORTS / "style_index.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader(); writer.writerows(rows)
    all_classes = sorted({c for row in rows for c in row["classes"].split(", ") if c})
    markdown = ["# Stylesheet index", "", f"Sections: {len(rows)} · distinct classes: {len(all_classes)}", "",
                "| Section | CSS line | Selectors | Classes |", "|---|---:|---:|---|"]
    markdown += [f"| {r['section']} | L{r['css_line']} | {r['selectors']} | {r['classes'] or '—'} |" for r in rows]
    markdown += ["", "## Full class vocabulary", "", "```text"]
    markdown += ["  " + "  ".join(all_classes[i:i + 6]) for i in range(0, len(all_classes), 6)]
    markdown += ["```", ""]
    (REPORTS / "style_index.md").write_text("\n".join(markdown), encoding="utf-8")
    print(f"style_index: {len(rows)} sections, {len(all_classes)} classes → reports/style_index.tsv/.md")
    if "--check-skill" in sys.argv:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        # Only the catalog section is a CSS-class contract. Other sections use backticks for
        # commands, paths, API names, and data values that are not meant to be selectors.
        match = re.search(r"^## 3\..*?$(.*?)(?=^## 4\.)", skill, re.M | re.S)
        catalog = match.group(1) if match else ""
        cited = set(re.findall(r"`([A-Za-z][A-Za-z0-9_-]*)`", catalog))
        unknown = sorted(c for c in cited if c not in all_classes and c not in {"the", "and", "for", "with"})
        if unknown:
            print("style_index: SKILL catalog cites undeclared classes:", ", ".join(unknown))
            return 1
        print(f"style_index: SKILL catalog class citations pass ({len(cited)} tokens)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
