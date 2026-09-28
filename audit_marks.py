#!/usr/bin/env python3
"""audit_marks.py — standing pre-package gate (reader directive, inherited with the pipeline).

Checks, per chapter file given as a bare filename or path:
  1. QUESTION MARKS
     a. Flattened questions: interrogative-led sentences inside “quotes”
        ending in '.'  → NO-QM? flags (triage: wh-clefts and temporal
        clauses are legitimate periods — the raw's 嗎/？ forms are the
        tie-breaker).
     b. Malformed sequences: ”? order, doubled ??, space-before-?,
        ?”. — flagged directly.
  2. PHONE-CALL BLOCKS (ElementTree, not regex)
     pc-head must be the first child; body classes must be a subset of
     pc-me / pc-them / pc-note. The .sinister variant is legal.

Usage:  python3 audit_marks.py epub/OEBPS/text/chapter110.xhtml [more files ...]
(the gate needs real paths: a bare filename resolves to nothing and prints a misleading success).
Exit 0 = no hard flags (NO-QM? items print for human triage; exit 1 only
on malformations, structure errors, or XML parse failures).
"""
import re
import sys
import xml.etree.ElementTree as ET

QW = (r"(?:Where|What|How|Why|Who|Whose|When|Which|Do|Does|Did|Is|Are|Was|Were|"
      r"Can|Could|Would|Will|Shall|Should|May|Have|Has|Had|Isn|Wasn|Aren|Don|"
      r"Didn|Won|Wouldn|Couldn|Haven|Hasn)[\w’]*")
XH = "{http://www.w3.org/1999/xhtml}"


def audit(path):
    soft, hard = [], []
    try:
        s = open(path, encoding="utf-8").read()
    except OSError as e:
        return [("", f"cannot read: {e}")], []
    body = re.sub(r"<[^>]+>", " ", s)

    # 1a — flattened questions (triage class)
    for m in re.finditer(r"“([^”]{4,300}?)”", body):
        for sent in re.split(r"(?<=[.!?…])\s+", m.group(1).strip()):
            if not sent or not re.match(rf"^{QW}\b", sent):
                continue
            if sent.endswith(".") and not sent.endswith("..."):
                soft.append(("NO-QM?", f"“…{sent[-70:]}”"))

    # 1b — hard malformations. NOTE: runs of three or more question marks
    # (???+) are the house's documented fan-board idiom (raw ？？？) and are
    # ALLOWED; exactly-two runs (??) are errors — incredulity is written "?!",
    # per the standing punctuation rules.
    for pat, tag in [(r"”\s*\?", "QM-AFTER-CLOSE"),
                     (r"\?(?<!\?\?)\?(?!\?)", "DOUBLE-QM"),
                     (r"\s\?", "SPACE-QM"), (r"\?”\.", "QM-PERIOD")]:
        for m in re.finditer(pat, body):
            a = max(0, m.start() - 35)
            ctx = re.sub(r"\s+", " ", body[a:m.end() + 25])
            hard.append((tag, f"…{ctx}"))

    # 2 — phone-call structure
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        hard.append(("XML", str(e)))
        return soft, hard
    for div in root.iter(XH + "div"):
        cls = div.get("class", "")
        if "phone-call" not in cls:
            continue
        kids = [(c.tag.split("}")[-1], c.get("class")) for c in div]
        head_ok = bool(kids) and kids[0][1] == "pc-head"
        bad = [k for k in kids[1:] if k[1] not in ("pc-me", "pc-them", "pc-note")]
        if not head_ok or bad:
            hard.append(("PC-STRUCT", f".{cls} head_ok={head_ok} bad={bad}"))

    return soft, hard


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    any_hard = False
    for f in argv[1:]:
        soft, hard = audit(f)
        print(f"== {f}")
        if not soft and not hard:
            print("   clean")
        for tag, msg in soft:
            print(f"   [{tag}] {msg}")
        for tag, msg in hard:
            any_hard = True
            print(f"   [{tag}] !! {msg}")
    if any_hard:
        print("RESULT: FAIL (fix hard flags)")
        return 1
    print("RESULT: OK (triage any NO-QM? lines above)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
