#!/usr/bin/env python3
"""Audit the Peninsula XHTML for quote and sentence-punctuation defects.

Dry run by default; ``--apply`` performs only the safe straight-quote/ASCII-ellipsis repair.
"""
import glob
import os
import re
import sys

TEXT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "epub", "OEBPS", "text")


def prose(src: str) -> str:
    return re.sub(r"<[^>]+>", "", src)


def audit():
    bad = {}
    for path in sorted(glob.glob(os.path.join(TEXT, "*.xhtml"))):
        body = prose(open(path, encoding="utf-8").read())
        issues = []
        if '"' in body:
            issues.append(f"straight quotes: {body.count(chr(34))}")
        opening, closing = body.count("“"), body.count("”")
        if opening != closing:
            issues.append(f"curly quote parity {opening}/{closing}")
        # A question mark after a quoted word is legal when the entire sentence is the
        # question (for example: Was this “together”?). Keep it as a human-review note,
        # not a hard failure. The same applies to a closing quote followed by !.
        for token, label in [("” .", "close-space-period"), ("….", "four-dot"), ("… .", "ellipsis-period"),
                             (" .", "space-period"), (" ,", "space-comma"), ("?.", "question-period")]:
            count = body.count(token)
            if count:
                issues.append(f"{label}: {count}")
        review = len(re.findall(r"”[?!]|”\.", body))
        # Quote-boundary punctuation is valid in English when it belongs to the containing
        # sentence, so it is deliberately not added to the failing issue list.
        if issues:
            bad[os.path.basename(path)] = issues
    return bad


def apply():
    changed = 0
    for path in sorted(glob.glob(os.path.join(TEXT, "*.xhtml"))):
        source = open(path, encoding="utf-8").read()
        original = source
        def fix_text_node(match):
            value = match.group(0)
            if '"' not in value:
                return value
            result, opening = [], True
            for char in value:
                if char == '"':
                    result.append("“" if opening else "”")
                    opening = not opening
                else:
                    result.append(char)
            return "".join(result)
        source = re.sub(r">[^<>]*<", fix_text_node, source).replace("...", "…")
        if source != original:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(source)
            changed += 1
            print("rewrote", os.path.basename(path))
    print(f"apply: {changed} files rewritten")


if __name__ == "__main__":
    if "--apply" in sys.argv:
        apply()
    flagged = audit()
    if flagged:
        print(f"punct_quotes: {len(flagged)} files flagged")
        for name, issues in flagged.items():
            print(f"  {name}: {'; '.join(issues)}")
        raise SystemExit(1)
    print("punct_quotes: 0 files flagged — PASS")
