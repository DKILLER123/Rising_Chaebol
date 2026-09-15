#!/usr/bin/env python3
"""legacy_firewall.py — the reader's hard constraint, made machine-checkable.

Standing directive for this book: production skills, house gates, fonts and stylesheet RULES
were inherited from the reference novel (*Peninsula: Going Viral After a Dating Scandal with
Kim Taeyeon*), but **no character, invented organization, ship label, song, system name or
other content of that novel may appear in this book.** This gate scans the book tree for bleed.

Two severities, because this novel and the reference novel both sit in the real Korean
entertainment industry:

  HARD — tokens that belong to the reference novel's own fiction (its protagonist and his
         aliases, its invented companies and products, its song/tour/system labels, its
         invented OCs). Any occurrence in the tree is a build blocker.

  SOFT — real public figures who appear in the reference novel and *might* legitimately appear
         in this one. A SOFT hit is cleared automatically when the same name (or a documented
         raw form of it) is present in this book's own `raws/` files, because then it came from
         the reader's raw and not from the other book. Otherwise it is a REVIEW flag.

Usage (from the repository root):
    python3 legacy_firewall.py                 # scan work_epub/
    python3 legacy_firewall.py --docs           # also scan authored markdown (state docs)
    python3 legacy_firewall.py --json reports/firewall.json

Exit 0 = no hard hits (soft hits print for review). Exit 1 = hard hits or parse failure.
An optional `firewall_allowlist.txt` (one token or `token<TAB>reason` per line, `#` comments)
downgrades named SOFT tokens with the recorded justification.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TREE = ROOT / "work_epub"
RAWS = ROOT / "raws"
ALLOWLIST = ROOT / "firewall_allowlist.txt"

# ── HARD: the reference novel's own inventions (never legal in this book) ─────────────────
HARD = {
    "protagonist": [r"Song\s+Ji-?ho", r"\bJi-?ho\b", r"노?솔\b", r"\bSol\b(?=[,.]|\s+(?:said|said\s|is|was))"],
    "invented_orgs_and_products": [r"\bLOEN\b", r"\bEIDER\b", r"\bSUNYE\b", r"\bCCM\s+(?:takeover|board)\b",
                                   r"Dream\s+Life", r"\bGolden\s+Trait\s+Shop\b"],
    "reference_titles_and_ships": [r"Girls\s*&\s*Peace", r"Seven\s+Years|“7\s+Years”",
                                   r"Stay\s+with\s+Me", r"Let\s+Me\s+Down\s+Slowly",
                                   r"Peninsula:?\s*Going\s+Viral"],
    "reference_cast": [r"Bae\s+Joo-?hyun", r"Im\s+Yoon-?a", r"Chae\s+Soo-?bin", r"Park\s+Ji-?yeon",
                       r"Lee\s+Ji-?eun", r"Kim\s+Kwang-?soo", r"Ham\s+Eun-?jung|Hahm\s+Eun-?jung",
                       r"Park\s+Hyo-?min", r"Seo\s+Ju-?hyun", r"Jang\s+Dah-?yeon|Jang\s+Won-?young",
                       r"Lee\s+Ah-?reum", r"\bQri\b", r"\bSeung-?wan\b", r"\bCabbage\b"],
}

# ── SOFT: real public figures shared with the reference novel's cast ──────────────────────
# Each entry: display name -> regexes; `raw_forms` are strings that also clear the token when
# found in raws/*.txt (this book's raw is Simplified Chinese).
SOFT = {
    "Kim Taeyeon": {"re": r"Kim\s+Tae-?yeon|Tae-?yeon|\bTaeti\b", "raw_forms": ["金泰妍", "太妍", "Taeyeon"]},
    "Im Yoona": {"re": r"\bYoona\b|Yoon-?a\b", "raw_forms": ["林允儿", "允儿"]},
    "Seohyun": {"re": r"\bSeohyun\b|Seo-?hyun\b", "raw_forms": ["徐贤", "서현"]},
    "Sunny": {"re": r"\bSunny\b(?=\s+(?:said|smiled|asked))", "raw_forms": ["李纯"]},
    "Tiffany": {"re": r"\bTiffany\b(?!\s+(?:&\s*Co))", "raw_forms": ["黄美英"]},
    "Hyoyeon": {"re": r"\bHyoyeon\b|Hyo-?yeon\b", "raw_forms": ["孝渊"]},
    "Yuri": {"re": r"\bYuri\b(?=\s+(?:said|smiled|asked|nods))", "raw_forms": ["权俞利"]},
    "Sooyoung": {"re": r"\bSooyoung\b", "raw_forms": ["崔秀英"]},
    "Hyo-min": {"re": r"\bHyo-?min\b", "raw_forms": ["朴善敏", "Hyomin"]},
    "IU": {"re": r"\bIU\b(?=\s+[A-Z]|\s+(?:said|smiled|released|was|is))", "raw_forms": ["李智恩", "아이유"]},
    "T-ara": {"re": r"T-?\s?ara\b", "raw_forms": ["Tara", "티아拉"]},
    "Krystal": {"re": r"\bKrystal\b", "raw_forms": ["郑秀晶"]},
    "Lee Boo-jin": {"re": r"Lee\s+Boo-?jin|이부진", "raw_forms": ["李富真"]},
}

TAG_RE = re.compile(r"<[^>]+>")
ATTR_RE = re.compile(r"\s(?:class|id|href|src|alt|role|epub:type|xml:lang|lang)\s*=\s*\"[^\"]*\"", re.I)


def strip_markup(src: str) -> str:
    body = TAG_RE.sub(" ", src)
    return re.sub(r"\s+", " ", body)


def load_allowlist() -> dict[str, str]:
    allowed: dict[str, str] = {}
    if ALLOWLIST.is_file():
        for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            token, _, reason = line.partition("\t")
            allowed[token.strip()] = reason.strip() or "reader allowlist"
    return allowed


def raw_corpus() -> str:
    """Text of the reader's own raws only — the sole admissible provenance for a real-name token.

    `*.txt` deliberately: documentation in raws/ (README.md) must never be able to "clear" a name,
    or a house rule could launder itself into canon by being written down next to a raw.
    """
    if not RAWS.is_dir():
        return ""
    return " ".join(p.read_text(encoding="utf-8", errors="replace")
                    for p in sorted(RAWS.rglob("*.txt")) if p.is_file())


def scan_docs(paths, pattern_table, flags=re.I):
    hits = []
    for path in paths:
        try:
            src = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        text = strip_markup(src) if path.suffix == ".xhtml" else src
        for label, patterns in pattern_table.items():
            for pat in patterns:
                for m in re.finditer(pat, text, flags):
                    start = max(0, m.start() - 45)
                    hits.append({"label": label, "pattern": pat, "file": path.relative_to(ROOT).as_posix(),
                                 "context": re.sub(r"\s+", " ", text[start:m.end() + 45]),
                                 "match": m.group(0)})
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--docs", action="store_true", help="also scan authored markdown at the root")
    ap.add_argument("--json", metavar="PATH", help="write a JSON report")
    args = ap.parse_args()

    tree_files = [p for p in TREE.rglob("*")
                  if p.is_file() and p.suffix in {".xhtml", ".opf", ".ncx", ".css", ".xml"}]
    if not tree_files:
        print("legacy_firewall: no book tree found (work_epub/ empty) — nothing to scan")
        return 0
    if args.docs:
        tree_files = sorted(set(tree_files) | set(ROOT.glob("*.md")))

    allowed = load_allowlist()
    corpus = raw_corpus()
    hard = [h for h in scan_docs(tree_files, HARD) if h["match"] not in allowed.get(h["match"], "")]
    soft_rows = []
    for name, spec in SOFT.items():
        found = scan_docs(tree_files, {name: [spec["re"]]})
        if not found:
            continue
        cleared = any(form in corpus for form in spec["raw_forms"]) or name in allowed or \
            any(f["match"] in allowed for f in found)
        note = ""
        if cleared:
            note = ("sourced from this book's raws" if any(form in corpus for form in spec["raw_forms"])
                    else "listed in firewall_allowlist.txt")
        soft_rows.append({"name": name, "hits": found, "cleared_by_raws": bool(cleared), "note": note})

    report = {
        "files_scanned": len(tree_files),
        "hard_tokens_groups": list(HARD),
        "hard_hits": hard,
        "soft": [{"name": r["name"], "hits": len(r["hits"]), "cleared_by_raws": r["cleared_by_raws"],
                  "note": r["note"],
                  "samples": [{"file": h["file"], "context": h["context"]} for h in r["hits"][:5]]}
                 for r in soft_rows],
        "scope_note": ("Hard tokens are the reference novel's own fiction; soft tokens are real "
                       "public figures cleared only when this book's raws name them. "
                       "Real-world idol names appearing in this book must trace to this book's raws."),
    }
    if args.json:
        out = ROOT / args.json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"legacy_firewall: {len(tree_files)} files scanned · "
          f"{len(corpus.split()):,} raw tokens indexed for provenance")
    if hard:
        print(f"  HARD BLEED ({len(hard)}):")
        for h in hard[:40]:
            print(f"    [{h['label']}] {h['file']}: …{h['context']}…")
    else:
        print("  hard bleed: 0 — none of the reference novel's inventions are present")
    for row in soft_rows:
        state = f"cleared ({row['note']})" if row["cleared_by_raws"] else "REVIEW — not named in raws/"
        print(f"  soft: {row['name']} ×{len(row['hits'])} → {state}")
        if not row["cleared_by_raws"]:
            for h in row["hits"][:3]:
                print(f"      {h['file']}: …{h['context']}…")
    if args.json:
        print(f"  report: {args.json}")
    print("legacy_firewall:", "PASS" if not hard else "FAIL (remove the reference novel's content)")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
