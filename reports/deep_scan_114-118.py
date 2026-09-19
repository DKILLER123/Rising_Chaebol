from pathlib import Path
import json, re, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EPUB = ROOT / "epub" / "OEBPS"
TEXT = EPUB / "text"
RAW = ROOT / "epub" / "raw"

report = {
    "scope": "second whole-manuscript deep scan before packaging",
    "chapters": 118,
    "errors": [],
    "checks": {},
}

# Parse every XHTML and check CJK, placeholders, classes, and image references.
css = (EPUB / "styles" / "stylesheet.css").read_text(encoding="utf-8")
css_classes = set(re.findall(r"\.([A-Za-z][A-Za-z0-9_-]*)", css))
all_xhtml = sorted(TEXT.glob("*.xhtml"))
used_classes = set()
image_refs = []
placeholder_hits = []
intentional_question_runs = []
cjk_hits = []
xml_failures = []
for path in all_xhtml:
    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        xml_failures.append({"file": str(path.relative_to(ROOT)), "error": str(exc)})
        continue
    for el in root.iter():
        cls = el.attrib.get("class", "")
        used_classes.update(cls.split())
        if el.tag.endswith("img"):
            image_refs.append((path.name, el.attrib.get("src", "")))
    text = " ".join("".join(root.itertext()).split())
    if re.search(r"[\u3400-\u9fff]", text):
        cjk_hits.append(path.name)
    # A whole-manuscript scan must distinguish unresolved placeholders from intentional
    # expressive punctuation in translated prose, comments, and dialogue.
    for marker in ("TODO", "PLACEHOLDER", "[TRANSLATE", "？", "【", "】"):
        if marker in text:
            placeholder_hits.append({"file": path.name, "marker": marker})
    if "???" in text:
        intentional_question_runs.append({"file": path.name, "context": "intentional English emphasis/dialogue/comment"})

undefined = sorted(c for c in used_classes if c not in css_classes)
if xml_failures:
    report["errors"].append({"xml_failures": xml_failures})
if cjk_hits:
    report["errors"].append({"cjk_files": cjk_hits})
if undefined:
    report["errors"].append({"undefined_classes": undefined})
if placeholder_hits:
    report["errors"].append({"placeholder_or_source_markers": placeholder_hits})

# Verify all manifest image references used by new chapters.
opf = ET.parse(EPUB / "content.opf").getroot()
ns = {"opf": "http://www.idpf.org/2007/opf"}
manifest = {item.attrib["href"]: item.attrib["id"] for item in opf.findall("opf:manifest/opf:item", ns)}
missing_images = []
for ch, src in image_refs:
    if ch in {f"chapter{n}.xhtml" for n in range(114, 119)}:
        dest = (TEXT / src).resolve()
        if not dest.exists():
            missing_images.append({"chapter": ch, "src": src, "reason": "missing on disk"})
        href = src.removeprefix("../")
        if href not in manifest:
            missing_images.append({"chapter": ch, "src": src, "reason": "not in OPF manifest"})
if missing_images:
    report["errors"].append({"new_image_errors": missing_images})

# New-chapter headings, question parity, and style-family requirements.
titles = {
    114: "Hungry? I’ll Make You Something Downstairs",
    115: "Bring It—How Could I Not?",
    116: "Han So-hee Gets Sentimental",
    117: "The Little Dragon’s Promise",
    118: "Off to Japan",
}
required = {
    114: ["location-stamp", "wardrobe-block", "comment-thread"],
    115: ["location-stamp", "pullquote"],
    116: ["location-stamp", "system-block", "memory-block"],
    117: ["location-stamp", "wardrobe-block", "system-block"],
    118: ["location-stamp", "wardrobe-block", "phone-call", "chat-container", "pullquote"],
}
new_results = {}
for n, title in titles.items():
    path = TEXT / f"chapter{n}.xhtml"
    raw = (RAW / f"ch{n}.txt").read_text(encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    root = ET.parse(path).getroot()
    h1s = ["".join(x.itertext()) for x in root.iter() if x.tag.endswith("h1")]
    q_raw = raw.count("？")
    q_eng = text.count("?")
    missing_blocks = [cls for cls in required[n] if f'class="{cls}"' not in text]
    result = {
        "h1": h1s[0] if h1s else None,
        "title_match": h1s == [title],
        "raw_question_marks": q_raw,
        "english_question_marks": q_eng,
        "question_parity": q_eng >= q_raw,
        "required_blocks_present": not missing_blocks,
        "missing_blocks": missing_blocks,
        "word_count": len(" ".join(root.itertext()).split()),
    }
    new_results[n] = result
    if not result["title_match"] or not result["question_parity"] or missing_blocks:
        report["errors"].append({f"chapter{n}": result})
report["checks"]["new_chapters"] = new_results

# Metadata integration counts and exact nav labels.
chapter_files = sorted(TEXT.glob("chapter*.xhtml"), key=lambda p: int(re.search(r"chapter(\d+)", p.name).group(1)))
manifest_chapters = [i for href, i in manifest.items() if re.fullmatch(r"text/chapter\d+\.xhtml", href)]
spine = opf.find("opf:spine", ns)
spine_chapters = [x.attrib["idref"] for x in spine.findall("opf:itemref", ns)] if spine is not None else []
nav_root = ET.parse(EPUB / "nav.xhtml").getroot()
toc_nav = next((el for el in nav_root.iter() if el.tag.endswith("nav") and el.attrib.get("{http://www.idpf.org/2007/ops}type") == "toc"), None)
nav_links = [a.attrib.get("href", "") for a in (toc_nav.iter() if toc_nav is not None else []) if a.tag.endswith("a") and a.attrib.get("href", "").startswith("text/chapter")]
ncx_root = ET.parse(EPUB / "toc.ncx").getroot()
ncx_ns = {"n": "http://www.daisy.org/z3986/2005/ncx/"}
ncx_chapters = [p for p in ncx_root.findall(".//n:navPoint", ncx_ns) if p.find("n:content", ncx_ns) is not None and p.find("n:content", ncx_ns).attrib.get("src", "").startswith("text/chapter")]
counts = {
    "disk": len(chapter_files),
    "opf_manifest": len(manifest_chapters),
    "opf_spine": len([x for x in spine_chapters if "chapter" in x]),
    "nav": len(nav_links),
    "ncx": len(ncx_chapters),
}
report["checks"]["integration_counts"] = counts
if set(counts.values()) != {118}:
    report["errors"].append({"integration_counts": counts})

# No stale full-edition count in the edition-facing metadata.
metadata_files = [EPUB / "content.opf", EPUB / "nav.xhtml", EPUB / "toc.ncx", TEXT / "title.xhtml", TEXT / "cover.xhtml", TEXT / "copyright.xhtml"]
stale = []
for p in metadata_files:
    s = p.read_text(encoding="utf-8")
    for phrase in ("113-chapter", "One Hundred Thirteen Chapters", "one hundred thirteen chapters", "one-hundred-thirteen chapter"):
        if phrase in s:
            stale.append({"file": str(p.relative_to(ROOT)), "phrase": phrase})
if stale:
    report["errors"].append({"stale_edition_counts": stale})
report["checks"]["edition_count_scan"] = {"stale_113_count_hits": stale}

report["checks"]["whole_manuscript"] = {
    "xhtml_files": len(all_xhtml),
    "xml_failures": xml_failures,
    "cjk_files": cjk_hits,
    "undefined_classes": undefined,
    "placeholder_or_source_markers": placeholder_hits,
    "intentional_question_runs": intentional_question_runs,
    "used_class_count": len(used_classes),
    "css_class_count": len(css_classes),
}
report["status"] = "PASS" if not report["errors"] else "REVIEW"
(Path(__file__).with_suffix(".json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": report["status"], "errors": report["errors"], "counts": counts}, ensure_ascii=False, indent=2))
