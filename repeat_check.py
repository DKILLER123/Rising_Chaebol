#!/usr/bin/env python3
"""House gate 3 — repetition check.

Usage:  python3 repeat_check.py ch001.xhtml            # bare filename, from the repo root
        python3 repeat_check.py ch003.xhtml ch001.xhtml ch002.xhtml   # explicit scope

For each named chapter, reports:
  * internal 8-gram repeats (the same 8 consecutive words twice inside the chapter)
  * cross-chapter 8-gram repeats against the previous chapters given as scope
    (default scope: the three chapters immediately before the newest named one)

Dialogue lines quoted on purpose (lyric blocks) must be reviewed by hand, not auto-fixed.
"""
import re
import sys
import os
import glob
import collections

TEXT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work_epub", "OEBPS", "text")
N = 8

def words(path):
    src = open(path, encoding="utf-8").read()
    src = re.sub(r"<head>.*?</head>", " ", src, flags=re.S)          # <title> repeats the chapter heading
    src = re.sub(r'<header class="chapter-header">.*?</header>', " ", src, flags=re.S)
    body = re.sub(r"<[^>]+>", " ", src)
    body = re.sub(r"&[a-z]+;", " ", body)
    return [w.lower() for w in re.findall(r"[a-z’']+", body)]

def grams(ws):
    return collections.Counter(tuple(ws[i:i + N]) for i in range(len(ws) - N + 1))

def num(name):
    m = re.search(r"ch(\d+)", name)
    return int(m.group(1)) if m else 0

def main():
    targets = [a for a in sys.argv[1:] if a.endswith(".xhtml")]
    if not targets:
        print("usage: repeat_check.py chNNN.xhtml [scope-chapters…]")
        return
    own = [t for t in targets if re.match(r"ch\d+\.xhtml$", t)]
    explicit_scope = [t for t in targets if not re.match(r"ch\d+\.xhtml$", t)]
    newest = max(num(t) for t in own)
    scope_files = explicit_scope
    if not scope_files:
        scope_files = [os.path.basename(p) for p in sorted(glob.glob(os.path.join(TEXT, "ch*.xhtml")))
                       if 0 < newest - num(os.path.basename(p)) <= 3]
    ok = True
    for t in own:
        n = num(t)
        sc = explicit_scope or [os.path.basename(p) for p in sorted(glob.glob(os.path.join(TEXT, "ch*.xhtml")))
                                if 0 < n - num(os.path.basename(p)) <= 3]
        sc = [x for x in sc if x != t]
        w = words(os.path.join(TEXT, t))
        g = grams(w)
        internal = {k: v for k, v in g.items() if v > 1}
        print(f"== {t} · {len(w)} words · scope: {', '.join(sc) or 'none'}")
        if internal:
            ok = False
            print(f"  INTERNAL repeats: {len(internal)}")
            for k in list(internal)[:6]:
                print(f"    x{internal[k]}: {' '.join(k)}")
        else:
            print("  internal repeats: 0")
        cross = 0
        for s in sc:
            ws2 = words(os.path.join(TEXT, s))
            g2 = grams(ws2)
            shared = [k for k in g if k in g2]
            if shared:
                cross += len(shared)
                for k in shared[:6]:
                    print(f"  vs {s}: {' '.join(k)}")
        print(f"  cross-chapter 8-grams: {cross}")
        if cross:
            ok = False
    print("repeat_check:", "PASS" if ok else "REVIEW (deliberate lyric quotes may be legitimate)")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
