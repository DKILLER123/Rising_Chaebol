#!/usr/bin/env python3
"""Check internal and recent cross-chapter 8-gram repetition.

Use ``python3 repeat_check.py chapter113.xhtml`` from the repository root. Explicit paths are also
accepted. Reported repeats are review flags because deliberate repeated dialogue or lyrics can be
valid.
"""
import collections
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEXT = ROOT / "epub" / "OEBPS" / "text"
N = 8
CH_RE = re.compile(r"chapter(\d{2,3})\.xhtml$")


def resolve(name: str) -> Path:
    path = Path(name)
    return path if path.is_file() else TEXT / name


def words(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    source = re.sub(r"<head>.*?</head>", " ", source, flags=re.S)
    source = re.sub(r'<header class="chapter-header">.*?</header>', " ", source, flags=re.S)
    source = re.sub(r"<[^>]+>", " ", source)
    source = re.sub(r"&[a-z]+;", " ", source)
    return [word.lower() for word in re.findall(r"[a-z’']+", source)]


def grams(items):
    return collections.Counter(tuple(items[i:i + N]) for i in range(len(items) - N + 1))


def number(path: Path) -> int:
    match = CH_RE.search(path.name)
    return int(match.group(1)) if match else 0


def main() -> int:
    args = [resolve(arg) for arg in sys.argv[1:] if arg.endswith(".xhtml")]
    if not args:
        print("usage: repeat_check.py chapterNN.xhtml [scope chapter files…]")
        return 2
    own = [path for path in args if CH_RE.match(path.name)]
    explicit = [path for path in args if path not in own]
    if not own:
        print("repeat_check: no chapter target supplied")
        return 2
    ok = True
    for target in own:
        scope = explicit or [p for p in TEXT.glob("chapter*.xhtml")
                             if 0 < number(target) - number(p) <= 3]
        target_words = words(target)
        internal = {gram: count for gram, count in grams(target_words).items() if count > 1}
        print(f"== {target.name} · {len(target_words)} words · scope {', '.join(p.name for p in scope) or 'none'}")
        if internal:
            ok = False
            print(f"  INTERNAL repeats: {len(internal)}")
            for gram, count in list(internal.items())[:6]:
                print(f"    ×{count}: {' '.join(gram)}")
        else:
            print("  internal repeats: 0")
        cross = 0
        target_grams = grams(target_words)
        for peer in scope:
            shared = [gram for gram in target_grams if gram in grams(words(peer))]
            cross += len(shared)
            for gram in shared[:6]:
                print(f"  vs {peer.name}: {' '.join(gram)}")
        print(f"  cross-chapter 8-grams: {cross}")
        if cross:
            ok = False
    print("repeat_check:", "PASS" if ok else "REVIEW")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
