from pathlib import Path
import json, re, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "epub" / "OEBPS" / "text"
RAW = ROOT / "epub" / "raw"
EPUB = ROOT / "epub" / "OEBPS"

chapters = {
    118: (RAW / "ch118-2026-09-28.txt", "Gulp—You’re the President of an Entertainment Company?"),
    119: (RAW / "ch119.txt", "Keep the Music Playing, Keep Dancing"),
    120: (RAW / "ch120.txt", "Sulli: I Love Hearing the Truth"),
}
anchors = {
    118: ["BukwangPharm", "Good Luck Card", "Kangshifu", "Hirai Momo", "Minatozaki Sana", "ShiningYouth Entertainment"],
    119: ["Park Jin-young", "Sexy Love", "red-eye", "passport", "Keep the music playing"],
    120: ["Incheon International Airport", "Paris", "Dongdaemun", "hotteok", "Jung Soo-jung", "boyfriend"],
}
report = {"scope": "second deep scan for revised chapters 118–120", "errors": [], "chapters": {}}

# CSS classes and OPF manifest.
css = (EPUB / "styles" / "stylesheet.css").read_text(encoding="utf-8")
css_classes = set(re.findall(r"\.([A-Za-z][A-Za-z0-9_-]*)", css))
opf = ET.parse(EPUB / "content.opf").getroot()
ns = {"opf": "http://www.idpf.org/2007/opf"}
manifest = {x.attrib["href"] for x in opf.findall("opf:manifest/opf:item", ns)}

for n, (raw_path, title) in chapters.items():
    xhtml_path = TEXT / f"chapter{n}.xhtml"
    raw = raw_path.read_text(encoding="utf-8")
    source = xhtml_path.read_text(encoding="utf-8")
    root = ET.parse(xhtml_path).getroot()
    visible = " ".join("".join(root.itertext()).split())
    used = {c for el in root.iter() for c in el.attrib.get("class", "").split()}
    missing_classes = sorted(used - css_classes)
    imgs = [el.attrib.get("src", "") for el in root.iter() if el.tag.endswith("img")]
    image_errors = []
    for src in imgs:
        disk = (xhtml_path.parent / src).resolve()
        href = src.removeprefix("../")
        if not disk.exists(): image_errors.append(f"missing image: {src}")
        if href not in manifest: image_errors.append(f"image not in OPF: {href}")
    h1s = ["".join(el.itertext()) for el in root.iter() if el.tag.endswith("h1")]
    missing_anchors = [a for a in anchors[n] if a.lower() not in visible.lower()]
    result = {
        "raw_bytes": len(raw.encode("utf-8")),
        "raw_nonempty_lines": sum(bool(line.strip()) for line in raw.splitlines()),
        "english_words": len(visible.split()),
        "raw_question_marks": raw.count("？"),
        "english_question_marks": source.count("?"),
        "question_parity": source.count("?") >= raw.count("？"),
        "h1": h1s[0] if h1s else None,
        "title_match": h1s == [title],
        "cjk_chars": len(re.findall(r"[\u3400-\u9fff]", visible)),
        "undefined_classes": missing_classes,
        "image_refs": imgs,
        "image_errors": image_errors,
        "missing_content_anchors": missing_anchors,
        "has_notification_class": 'notification' in used,
        "style_blocks": sorted({c for c in used if c in {"location-stamp", "wardrobe-block", "briefing-block", "finance-block", "performance-block", "phone-call", "chat-container", "pullquote", "scene-break"}}),
    }
    report["chapters"][str(n)] = result
    if result["cjk_chars"] or missing_classes or image_errors or missing_anchors or not result["question_parity"] or not result["title_match"]:
        report["errors"].append({f"chapter{n}": result})

# Cross-file requirements: the user specifically rejected a notification block for message content in ch118.
ch118_text = (TEXT / "chapter118.xhtml").read_text(encoding="utf-8")
if 'class="notification"' in ch118_text:
    report["errors"].append({"chapter118": "notification class remains in revised chapter 118"})

# 120-chapter package wiring before build.
chapter_paths = sorted(TEXT.glob("chapter*.xhtml"), key=lambda p: int(re.search(r"chapter(\d+)", p.name).group(1)))
counts = {
    "disk_chapters": len(chapter_paths),
    "opf_manifest_chapters": len([h for h in manifest if re.fullmatch(r"text/chapter\d+\.xhtml", h)]),
    "opf_spine_chapters": len([x for x in opf.findall("opf:spine/opf:itemref", ns) if "chapter" in x.attrib.get("idref", "")]),
}
report["integration_counts"] = counts
if set(counts.values()) != {120}:
    report["errors"].append({"integration_counts": counts})

report["status"] = "PASS" if not report["errors"] else "REVIEW"
(Path(__file__).with_suffix(".json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
