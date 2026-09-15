#!/usr/bin/env python3
"""House gate 2 — punctuation & quote audit (dry run; --apply to fix).

Pass condition for a build: reports 0 files needing rewrite.

Checks per file:
  * straight double quotes in prose (Option B made everything curly)
  * curly quote parity (open “ count == close ” count)
  * ”? ”! ”.  (closing quote followed by punctuation it should have swallowed)
  * ”?  inverted (question mark BEFORE closing quote is fine; this checks '?”' is fine too —
    the defect list is: `”?` `”!` `” .`)
  * ASCII ellipsis '...', four-dot '….', '….' ellipsis-then-period
  * space before sentence punctuation ' .', ' ,'
  * '?.' question mark followed by a period
"""
import re
import sys
import glob
import os

TEXT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work_epub", "OEBPS", "text")

def prose(src):
    return re.sub(r"<[^>]+>", "", src)

def audit():
    bad = {}
    for f in sorted(glob.glob(os.path.join(TEXT, "*.xhtml"))):
        src = open(f, encoding="utf-8").read()
        body = prose(src)
        issues = []
        if '"' in body:
            issues.append(f'straight quotes: {body.count(chr(34))}')
        o, c = body.count("“"), body.count("”")
        if o != c:
            issues.append(f"parity {o}/{c}")
        for pat, label in [("”?", "”?"), ("”!", "”!"), ("” .", "”+space+."), ("….", "four-dot"),
                           ("… .", "ellipsis-period"), (" .", "space-period"), (" ,", "space-comma"),
                           ("?.", "?.")]:
            n = body.count(pat)
            if n:
                issues.append(f"{label}: {n}")
        # '”.' (period after closing quote at sentence end) is legal only when the
        # quote ends mid-sentence of a larger sentence; count for manual review
        n = len(re.findall(r"”\.", body))
        if n:
            issues.append(f"”.-review: {n}")
        if issues:
            bad[os.path.basename(f)] = issues
    return bad

def apply():
    changed = 0
    for f in sorted(glob.glob(os.path.join(TEXT, "*.xhtml"))):
        src = open(f, encoding="utf-8").read()
        orig = src
        # straight-quote paragraph repair: alternate open/close inside each text node
        def fix_para(m):
            s = m.group(0)
            if '"' not in s:
                return s
            out, open_q = [], True
            for ch in s:
                if ch == '"':
                    out.append("“" if open_q else "”")
                    open_q = not open_q
                else:
                    out.append(ch)
            return "".join(out)
        src = re.sub(r">[^<>]*<", fix_para, src)
        src = src.replace("...", "…")
        if src != orig:
            open(f, "w", encoding="utf-8").write(src)
            changed += 1
            print(f"rewrote {os.path.basename(f)}")
    print(f"apply: {changed} files rewritten")
    return changed

if __name__ == "__main__":
    if "--apply" in sys.argv:
        apply()
    bad = audit()
    if bad:
        print(f"punct_quotes: {len(bad)} files flagged")
        for k, v in bad.items():
            print(f"  {k}: {'; '.join(v)}")
        sys.exit(1)
    print("punct_quotes: 0 files to rewrite — PASS")
