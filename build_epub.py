#!/usr/bin/env python3
"""House packer — builds the deliverable EPUB from work_epub/.

OVERWRITES the root deliverable: never run it to inspect the book, and never run it without an
authorized editorial cycle, a worklog §8 entry and all §9 gates green (SKILL.md §2 step 7).

Rules (fixed by this project's worklog):
  * mimetype MUST be the first entry, STORED, raw bytes 'application/epub+zip'
  * everything else ZIP_DEFLATED
  * entry order: mimetype, META-INF/*, then the OEBPS tree
"""
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.join(HERE, "work_epub")
OUT = os.path.join(HERE, "Dominating_South_Korea_Starting_with_a_Golden_Trait.epub")

def entries():
    files = []
    for root, _dirs, names in os.walk(TREE):
        for n in names:
            p = os.path.join(root, n)
            rel = os.path.relpath(p, TREE).replace(os.sep, "/")
            files.append(rel)
    files.sort()
    # fixed ordering: mimetype first, then META-INF, then everything else
    head = [f for f in files if f == "mimetype"]
    mid = sorted(f for f in files if f.startswith("META-INF/"))
    tail = sorted(f for f in files if f != "mimetype" and not f.startswith("META-INF/"))
    return head + mid + tail

def main():
    lst = entries()
    with zipfile.ZipFile(OUT, "w") as z:
        for rel in lst:
            p = os.path.join(TREE, rel)
            if rel == "mimetype":
                zi = zipfile.ZipInfo("mimetype")
                zi.compress_type = zipfile.ZIP_STORED
                z.writestr(zi, b"application/epub+zip")
            else:
                z.write(p, rel, compress_type=zipfile.ZIP_DEFLATED)
    size = os.path.getsize(OUT)
    with zipfile.ZipFile(OUT) as z:
        infos = z.infolist()
        first_stored = infos[0].filename == "mimetype" and infos[0].compress_type == zipfile.ZIP_STORED
        bad = z.testzip()
    import hashlib
    sha = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    print(f"built {os.path.basename(OUT)}")
    print(f"entries: {len(infos)} · size: {size} B · sha256: {sha[:16]}…")
    print(f"mimetype first/STORED: {first_stored} · testzip: {bad}")
    if not first_stored or bad:
        sys.exit(1)

if __name__ == "__main__":
    main()
