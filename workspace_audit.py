#!/usr/bin/env python3
"""Read-only full-tree audit for the Peninsula EPUB workspace.

The audit inventories the editable ``epub/`` tree, verifies OPF/spine/navigation/image references,
checks parity with ``public/Peninsula_Rising_Chaebol.epub`` when present, and optionally decodes all
images and WOFF files. It writes reports/ but never edits book files or rebuilds the package.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TREE = ROOT / "epub"
BOOK = ROOT / "public" / "Peninsula_Rising_Chaebol.epub"
REPORTS = ROOT / "reports"
X = "{http://www.w3.org/1999/xhtml}"
O = "{http://www.idpf.org/2007/opf}"
N = "{http://www.daisy.org/z3986/2005/ncx/}"
CONTAINER = "{urn:oasis:names:tc:opendocument:xmlns:container}"
CHAPTER_RE = re.compile(r"OEBPS/text/chapter(\d{2,3})\.xhtml$")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def visible(element) -> str:
    return " ".join("".join(element.itertext()).split()) if element is not None else ""


def classes(element) -> set[str]:
    return set(element.get("class", "").split())


def write_tsv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    with (REPORTS / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: " ".join(value.split()) if isinstance(value, str) else value
                             for key, value in row.items()})


def relpath(path: Path) -> str:
    return path.relative_to(TREE).as_posix()


def resolve_url(source_rel: str, url: str, errors: list[str], references: list[dict]) -> str | None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    source = (TREE / source_rel).resolve()
    target = (source.parent / urllib.parse.unquote(parsed.path)).resolve()
    try:
        target_rel = target.relative_to(TREE.resolve()).as_posix()
    except ValueError:
        errors.append(f"{source_rel}: path escapes epub tree: {url}")
        return None
    if not target.is_file():
        errors.append(f"{source_rel}: missing target: {url}")
    references.append({"source": source_rel, "url": url, "target": target_rel})
    return target_rel


def parse_documents(files: dict[str, Path], errors: list[str]) -> dict[str, ET.Element]:
    docs = {}
    for name, path in files.items():
        if path.suffix not in {".xml", ".opf", ".ncx", ".xhtml"}:
            continue
        try:
            docs[name] = ET.parse(path).getroot()
        except ET.ParseError as exc:
            errors.append(f"{name}: XML parse: {exc}")
    return docs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", action="store_true", help="decode all images and WOFF files")
    args = parser.parse_args()
    REPORTS.mkdir(exist_ok=True)
    errors: list[str] = []
    review: list[dict[str, str]] = []
    files = {p.relative_to(TREE).as_posix(): p for p in TREE.rglob("*") if p.is_file()} if TREE.is_dir() else {}
    if not files:
        print("workspace_audit: epub/ is missing or empty", file=sys.stderr)
        return 1
    payload = {name: path for name, path in files.items()
               if name == "mimetype" or name.startswith("META-INF/") or name.startswith("OEBPS/")}
    docs = parse_documents(payload, errors)
    references: list[dict] = []

    # Package document and manifest.
    container = docs.get("META-INF/container.xml")
    rootfile = container.find(".//" + CONTAINER + "rootfile") if container is not None else None
    opf_name = rootfile.get("full-path") if rootfile is not None else None
    if not opf_name or opf_name not in docs:
        errors.append("META-INF/container.xml does not point to a parsed OPF")
        opf = None
    else:
        opf = docs[opf_name]
    items = opf.findall(f"{O}manifest/{O}item") if opf is not None else []
    manifest = {item.get("id"): item for item in items}
    if len(manifest) != len(items):
        errors.append("duplicate OPF manifest IDs")
    for item in items:
        href = item.get("href", "")
        target = resolve_url(opf_name, href, errors, references) if opf_name else None
        if target and not target.startswith("OEBPS/"):
            errors.append(f"manifest href outside OEBPS: {href}")

    # Every document reference and every CSS font URL must resolve.
    for name, root in docs.items():
        ids = [element.get("id") for element in root.iter() if element.get("id")]
        if len(ids) != len(set(ids)):
            errors.append(f"{name}: duplicate XML IDs")
        for element in root.iter():
            for attr in ("href", "src"):
                url = element.get(attr)
                if url:
                    resolve_url(name, url, errors, references)
            if element.tag == X + "img" and not element.get("alt", "").strip():
                review.append({"file": name, "kind": "image-alt", "detail": element.get("src", "")})
    for name, path in payload.items():
        if path.suffix != ".css":
            continue
        css = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
        for url in re.findall(r"url\(\s*['\"]?([^\s)'\"]+)", css):
            resolve_url(name, url, errors, references)

    # Source payload must be manifest-covered (apart from OPF/nav/NCX conventionally handled by OPF).
    declared = set()
    for item in items:
        href = item.get("href", "")
        if opf_name:
            target = (TREE / opf_name).parent / urllib.parse.unquote(href)
            if target.is_file():
                declared.add(target.relative_to(TREE).as_posix())
    payload_resources = {name for name in payload if name.startswith("OEBPS/") and name != opf_name}
    unmanifested = sorted(payload_resources - declared)
    if unmanifested:
        review.append({"file": "epub/OEBPS", "kind": "unmanifested-resource",
                       "detail": ", ".join(unmanifested)})

    chapter_matches = [(int(match.group(1)), name) for name in files
                       if (match := CHAPTER_RE.fullmatch(name))]
    chapter_matches.sort()
    chapter_nums = [number for number, _ in chapter_matches]
    chapter_names = [name for _, name in chapter_matches]
    if chapter_nums != list(range(1, len(chapter_nums) + 1)):
        errors.append(f"chapter sequence is not contiguous: {chapter_nums[:3]} … {chapter_nums[-3:]}")

    spine = opf.findall(f"{O}spine/{O}itemref") if opf is not None else []
    spine_hrefs = [manifest[item.get("idref")].get("href") for item in spine
                   if item.get("idref") in manifest]
    expected_front = ["text/cover.xhtml", "nav.xhtml", "text/title.xhtml", "text/copyright.xhtml",
                      "text/characters.xhtml", "text/introductions.xhtml"]
    expected_chapters = [name.removeprefix("OEBPS/") for name in chapter_names]
    if spine_hrefs[:len(expected_front)] != expected_front:
        errors.append(f"spine front matter mismatch: {spine_hrefs[:len(expected_front)]}")
    if spine_hrefs[len(expected_front):len(expected_front) + len(expected_chapters)] != expected_chapters:
        errors.append("spine chapter order mismatch")

    nav_root = docs.get("OEBPS/nav.xhtml")
    nav_chapters = []
    if nav_root is not None:
        toc = next((element for element in nav_root.iter(X + "nav")
                    if "toc" in element.get("{http://www.idpf.org/2007/ops}type", "").split()), None)
        if toc is None:
            errors.append("nav.xhtml has no epub:type=\"toc\" navigation")
        else:
            nav_chapters = [element.get("href") for element in toc.iter(X + "a")
                            if re.fullmatch(r"text/chapter\d{2,3}\.xhtml", element.get("href", ""))]
            if nav_chapters != expected_chapters:
                errors.append("nav chapter sequence mismatch")
    ncx = docs.get("OEBPS/toc.ncx")
    points = list(ncx.iter(N + "navPoint")) if ncx is not None else []
    orders = [int(point.get("playOrder")) for point in points if point.get("playOrder", "").isdigit()]
    if orders != list(range(1, len(points) + 1)):
        errors.append("NCX playOrder is not contiguous")
    ncx_chapters = [element.get("src") for element in ncx.iter(N + "content")
                    if re.fullmatch(r"text/chapter\d{2,3}\.xhtml", element.get("src", ""))] if ncx is not None else []
    if ncx_chapters != expected_chapters:
        errors.append("NCX chapter sequence mismatch")

    chapter_rows = []
    style_usage = collections.Counter()
    for name in chapter_names:
        root = docs.get(name)
        body = root.find(X + "body") if root is not None else None
        body_text = visible(body)
        words = re.findall(r"[A-Za-z]+(?:[’'-][A-Za-z]+)*", body_text)
        dates = [visible(element) for element in root.iter() if "ls-date" in classes(element)] if root is not None else []
        for element in body.iter() if body is not None else []:
            style_usage.update(classes(element))
        title = next((visible(element) for element in root.iter() if "chapter-title" in classes(element)), "") if root is not None else ""
        chapter_rows.append({"chapter": Path(name).stem, "title": title, "body_words": len(words),
                             "date_stamps": " | ".join(dates)})
        if "\ufffd" in body_text:
            review.append({"file": name, "kind": "replacement-character", "detail": "U+FFFD present"})
        for match in re.finditer(r"\b([A-Za-z]+)\s+\1\b", body_text, re.I):
            review.append({"file": name, "kind": "doubled-word",
                           "detail": body_text[max(0, match.start() - 25):match.end() + 25]})
    write_tsv("chapter_index.tsv", chapter_rows)
    write_tsv("style_usage.tsv", [{"class": key, "occurrences": value} for key, value in sorted(style_usage.items())])

    # Optional binary decoding.
    assets = []
    if args.assets:
        try:
            from PIL import Image
            from fontTools.ttLib import TTFont
            for name, path in sorted(payload.items()):
                try:
                    if path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                        with Image.open(path) as image:
                            image.load()
                            assets.append({"path": name, "type": image.format,
                                           "detail": f"{image.width}x{image.height} {image.mode}", "status": "decoded"})
                    elif path.suffix.lower() == ".woff":
                        with TTFont(path, lazy=False) as font:
                            assets.append({"path": name, "type": "WOFF",
                                           "detail": f"{len(font.getBestCmap() or {})} mapped codepoints", "status": "decoded"})
                except Exception as exc:
                    review.append({"file": name, "kind": "asset-decode", "detail": str(exc)})
        except ImportError as exc:
            review.append({"file": "workspace_audit.py", "kind": "asset-dependencies", "detail": str(exc)})
        write_tsv("asset_validation.tsv", assets)

    # Compare the editable packaged payload with the current deliverable.
    archive_entries = []
    archive_only = tree_only = changed = []
    archive_sha = None
    package_state = "not-built"
    if BOOK.is_file():
        package_state = "built"
        archive_sha = sha(BOOK.read_bytes())
        with zipfile.ZipFile(BOOK) as archive:
            archive_entries = archive.infolist()
            archive_files = {info.filename for info in archive_entries if not info.filename.endswith("/")}
            source_files = set(payload)
            archive_only = sorted(archive_files - source_files)
            tree_only = sorted(source_files - archive_files)
            changed = sorted(name for name in source_files & archive_files
                             if (TREE / name).read_bytes() != archive.read(name))
            if len(archive_files) != len(set(archive_files)):
                errors.append("duplicate archive file entries")
            if archive.testzip() is not None:
                errors.append("archive CRC failure")
            first = archive.infolist()[0] if archive.infolist() else None
            if not first or first.filename != "mimetype" or first.compress_type != zipfile.ZIP_STORED \
                    or archive.read("mimetype") != b"application/epub+zip":
                errors.append("invalid mimetype packaging")
        if archive_only or tree_only or changed:
            review.append({"file": BOOK.name, "kind": "source-package-drift",
                           "detail": f"archive-only={len(archive_only)}, tree-only={len(tree_only)}, changed={len(changed)}"})

    # Run the cheap gates as subprocesses and retain their output.
    gate_commands = {
        "validate_tree": [sys.executable, "validate_tree.py"],
        "check_classes": [sys.executable, "check_classes.py"],
        "punct_quotes": [sys.executable, "punct_quotes.py"],
        "legacy_firewall": [sys.executable, "legacy_firewall.py"],
    }
    gates = {}
    for label, command in gate_commands.items():
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (REPORTS / f"{label}.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
        gates[label] = result.returncode

    summary = {
        "book": str(BOOK.relative_to(ROOT)), "package_state": package_state,
        "package_sha256": archive_sha, "package_bytes": BOOK.stat().st_size if BOOK.is_file() else None,
        "archive_entries": len(archive_entries), "archive_file_entries": len(archive_entries) - sum(i.filename.endswith("/") for i in archive_entries),
        "source_files": len(files), "packaged_source_files": len(payload),
        "archive_only": archive_only, "tree_only": tree_only, "changed_files": changed,
        "xml_documents": len(docs), "chapters": len(chapter_names), "spine_items": len(spine),
        "manifest_items": len(items), "nav_chapter_links": len(nav_chapters),
        "ncx_navpoints": len(points), "images": sum(i.get("media-type", "").startswith("image/") for i in items),
        "fonts": sum(i.get("href", "").endswith(".woff") for i in items),
        "references_checked": len(references), "assets_decoded": len(assets),
        "gate_exit_codes": gates, "review_counts": dict(collections.Counter(item["kind"] for item in review)),
        "structural_errors": sorted(set(errors)),
        "scope_note": "Automated structural and asset audit; editorial quality and AI identity require human/VLM review.",
    }
    (REPORTS / "workspace_audit.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
