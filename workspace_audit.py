#!/usr/bin/env python3
"""Read-only workspace audit for *Dominating South Korea: Starting with a Golden Trait*.
Writes reports/, never edits or rebuilds the book. Safe to run with no EPUB built yet: the
package-parity section is skipped and recorded as `package-not-built` for review.

python3 workspace_audit.py             # standard-library structural/content inventory
.venv/bin/python workspace_audit.py --assets  # additionally decode images and WOFFs

Exit 1 means integrity/structural failures. Editorial heuristics are REVIEW, not fixes.
This supplements the legacy house gates, not EPUBCheck or a full editorial proofread.
"""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parent
TREE = ROOT / 'work_epub'
REPORTS = ROOT / 'reports'
BOOK = ROOT / 'Dominating_South_Korea_Starting_with_a_Golden_Trait.epub'
# Required front-matter order for this edition (reader directive): cover, synopsis, contents,
# character info, introductions, glossary, then Chapter 1 onward.
FRONT_ORDER = ['text/cover.xhtml', 'text/synopsis.xhtml', 'text/nav.xhtml',
               'text/characters.xhtml', 'text/introductions.xhtml', 'text/glossary.xhtml']
X = '{http://www.w3.org/1999/xhtml}'
O = '{http://www.idpf.org/2007/opf}'
N = '{http://www.daisy.org/z3986/2005/ncx/}'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text(element):
    return ''.join(element.itertext()) if element is not None else ''


def classes(element):
    return set(element.get('class', '').split())


def compact(element):
    return ' '.join(text(element).split())


def tsv(name, rows):
    if not rows:
        return
    with (REPORTS / name).open('w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]), delimiter='\t')
        writer.writeheader()
        writer.writerows({k: ' '.join(v.split()) if isinstance(v, str) else v for k, v in row.items()} for row in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', action='store_true')
    args = parser.parse_args()
    if args.assets:
        from PIL import Image
        from fontTools.ttLib import TTFont
    REPORTS.mkdir(exist_ok=True)
    errors, review = [], []
    files = {p.relative_to(TREE).as_posix(): p for p in TREE.rglob('*') if p.is_file()}
    if not files:
        parser.error('work_epub/ is missing or empty. Setup order: python3 sync_styles.py, python3 install_fonts.py, then seed the front-matter pages; chapter cycles rebuild from raws/')
    infos, archive_only, tree_only, changed, inventory = [], [], [], [], []
    if BOOK.exists():
        with zipfile.ZipFile(BOOK) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            if len(names) != len(set(names)):
                errors.append('Duplicate archive entries')
            if archive.testzip() is not None:
                errors.append('Archive CRC failure')
            first = infos[0]
            if not (first.filename == 'mimetype' and first.compress_type == zipfile.ZIP_STORED
                    and archive.read('mimetype') == b'application/epub+zip'):
                errors.append('Invalid mimetype packaging')
            archive_only = sorted(set(names) - files.keys())
            tree_only = sorted(files.keys() - set(names))
            changed = sorted(n for n in files.keys() & set(names)
                             if files[n].read_bytes() != archive.read(n))
            if archive_only or tree_only or changed:
                errors.append('Tree/archive parity differs; see summary JSON')
            inventory = [{'path': i.filename, 'bytes': i.file_size,
                          'sha256': sha(archive.read(i)), 'compression': i.compress_type}
                         for i in infos]
        tsv('archive_inventory.tsv', inventory)
    else:
        review.append({'file': BOOK.name, 'kind': 'package-not-built',
                       'detail': 'No EPUB at the deliverable path yet. Expected during workspace '
                                 'setup; build_epub.py runs only after an authorized editorial cycle.'})
    docs = {}
    for name, path in files.items():
        if path.suffix in {'.xml', '.opf', '.ncx', '.xhtml'}:
            try:
                docs[name] = ET.parse(path).getroot()
            except ET.ParseError as exc:
                errors.append(f'{name}: XML: {exc}')
    container = docs.get('META-INF/container.xml')
    rootfile = container.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile') if container is not None else None
    if rootfile is None:
        parser.error('No container rootfile')
    opf_name = rootfile.get('full-path')
    opf = docs.get(opf_name)
    if opf is None:
        parser.error('Package document missing or unparsable')
    opf_path = TREE / opf_name
    items = opf.findall(f'{O}manifest/{O}item')
    manifest = {i.get('id'): i for i in items}
    if len(manifest) != len(items):
        errors.append('Duplicate manifest IDs')
    hrefs = [i.get('href') for i in items]
    if len(hrefs) != len(set(hrefs)):
        errors.append('Duplicate manifest hrefs')
    references = []

    def resolve(source, url):
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc:
            return None
        target = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source.resolve()
        if not target.is_relative_to(TREE.resolve()):
            errors.append(f'{source.relative_to(TREE)}: path escapes tree: {url}')
            return None
        rel = target.relative_to(TREE.resolve()).as_posix()
        if not target.is_file():
            errors.append(f'{source.relative_to(TREE)}: missing target: {url}')
        if parsed.fragment and rel in docs:
            ids = {e.get('id') or e.get('{http://www.w3.org/XML/1998/namespace}id') for e in docs[rel].iter()}
            if unquote(parsed.fragment) not in ids:
                errors.append(f'{source.relative_to(TREE)}: missing fragment: {url}')
        references.append((source.relative_to(TREE).as_posix(), url, rel))
        return rel

    declared = {resolve(opf_path, i.get('href')) for i in items}
    packaged_resources = {n for n in files if n.startswith(str(Path(opf_name).parent) + '/') and n != opf_name}
    undeclared = sorted(packaged_resources - declared)
    if undeclared:
        errors.append(f'Unmanifested resources: {undeclared}')
    for name, doc in docs.items():
        ids = [e.get('id') for e in doc.iter() if e.get('id')]
        if len(ids) != len(set(ids)):
            errors.append(f'{name}: duplicate XML IDs')
        for e in doc.iter():
            for attr in ('href', 'src', 'full-path'):
                if attr not in e.attrib or attr == 'full-path':
                    continue
                resolve(TREE / name, e.get(attr))
            if e.tag == X + 'img' and not e.get('alt', '').strip():
                review.append({'file': name, 'kind': 'image-alt', 'detail': e.get('src')})
            if e.tag == X + 'p' and any(c.tag in {X + t for t in ['div', 'p', 'table', 'section', 'ul', 'ol']} for c in e.iter() if c is not e):
                errors.append(f'{name}: block element nested inside p')
    for name, path in files.items():
        if path.suffix == '.css':
            css = re.sub(r'/\*.*?\*/', '', path.read_text(), flags=re.S)
            for url in re.findall(r'url\(\s*[\'"]?([^\s)\'"]+)', css):
                resolve(path, url)
    spine = opf.findall(f'{O}spine/{O}itemref')
    spine_hrefs = []
    for item in spine:
        if item.get('idref') not in manifest:
            errors.append(f'Missing spine ID: {item.get("idref")}')
        else:
            spine_hrefs.append(manifest[item.get('idref')].get('href'))
    chapter_names = sorted(n for n in files if re.fullmatch(r'OEBPS/text/ch\d{3}\.xhtml', n))
    expected = [f'OEBPS/text/ch{n:03}.xhtml' for n in range(1, len(chapter_names) + 1)]
    if chapter_names != expected:
        errors.append('Chapter sequence has gaps')
    if [h for h in spine_hrefs if re.fullmatch(r'text/ch\d{3}\.xhtml', h)] != [n.removeprefix('OEBPS/') for n in expected]:
        errors.append('Spine chapter order mismatch')
    if spine_hrefs[:len(FRONT_ORDER)] != FRONT_ORDER:
        errors.append('Spine front-matter order mismatch: the reader-mandated order is '
                      + ' > '.join(FRONT_ORDER) + f'; the spine opens with {spine_hrefs[:len(FRONT_ORDER)]}')
    for position, name in enumerate(chapter_names, start=1):
        want = f'text/ch{position:03d}.xhtml'
        if len(spine_hrefs) < len(FRONT_ORDER) + position or spine_hrefs[len(FRONT_ORDER) + position - 1] != want:
            errors.append(f'Spine chapter slot {position} should be {want}')
            break
    nav = docs['OEBPS/text/nav.xhtml']
    toc = next(e for e in nav.iter(X + 'nav') if 'toc' in e.get('{http://www.idpf.org/2007/ops}type', '').split())
    nav_chapters = [a.get('href') for a in toc.iter(X + 'a') if re.fullmatch(r'ch\d{3}\.xhtml', a.get('href', ''))]
    if nav_chapters != [Path(n).name for n in expected]:
        errors.append('Navigation chapter sequence mismatch')
    ncx = docs['OEBPS/toc.ncx']
    points = list(ncx.iter(N + 'navPoint'))
    if [int(p.get('playOrder')) for p in points] != list(range(1, len(points) + 1)):
        errors.append('NCX playOrder not contiguous')
    ncx_chapters = [e.get('src') for e in ncx.iter(N + 'content') if re.fullmatch(r'text/ch\d{3}\.xhtml', e.get('src', ''))]
    if ncx_chapters != [n.removeprefix('OEBPS/') for n in expected]:
        errors.append('NCX chapter sequence mismatch')
    chapter_rows, block_usage = [], collections.defaultdict(collections.Counter)
    for name in chapter_names:
        doc = docs.get(name)
        if doc is None:
            continue
        body = doc.find(X + 'body')
        body_text = text(body)
        words = re.findall(r"[A-Za-z]+(?:[’'-][A-Za-z]+)*", body_text)
        ps = [text(p) for p in body.iter(X + 'p')]
        title = next((compact(e) for e in body.iter() if 'chapter-title' in classes(e)), '')
        dates = [compact(e) for e in body.iter() if 'ls-date' in classes(e)]
        paragraph_max = max((len(re.findall(r"[A-Za-z]+(?:[’'-][A-Za-z]+)*", p)) for p in ps), default=0)
        dash_density = round(1000 * body_text.count('—') / max(len(words), 1), 2)
        row = {'chapter': Path(name).stem, 'title': title, 'body_words': len(words),
               'max_p_words': paragraph_max, 'dashes_per_1000': dash_density,
               'open_quotes': body_text.count('“'), 'close_quotes': body_text.count('”'),
               'date_stamps': ' | '.join(dates)}
        chapter_rows.append(row)
        for e in body.iter():
            for c in classes(e):
                block_usage[c][Path(name).stem] += 1
            if 'whisper-block' in classes(e):
                speakers = [next(iter(classes(c) & {'wh-voice', 'wh-reply'})) for c in e if classes(c) & {'wh-voice', 'wh-reply'}]
                if any(a == b for a, b in zip(speakers, speakers[1:])) or not len(e) or 'wh-close' not in classes(e[-1]):
                    review.append({'file': name, 'kind': 'whisper-policy', 'detail': 'Nonalternation and/or missing final wh-close; compare actual context to SKILL.md'})
        for match in re.finditer(r'\b([A-Za-z]+)\s+\1\b', body_text, re.I):
            review.append({'file': name, 'kind': 'doubled-word', 'detail': body_text[max(0, match.start()-35):match.end()+35]})
        if '\ufffd' in body_text:
            review.append({'file': name, 'kind': 'replacement-character', 'detail': 'Unicode replacement character present'})
        # Keep Hangul glosses and fan Jamo separate from untranslated Han characters.
        hangul = re.findall(r'[\uac00-\ud7af]', body_text)
        if hangul:
            review.append({'file': name, 'kind': 'hangul-syllables', 'detail': f'{len(hangul)} syllables; manual context check'})
        if paragraph_max > 100 or dash_density > 5:
            review.append({'file': name, 'kind': 'metrics-band', 'detail': f'max p {paragraph_max}; dashes/1k {dash_density}; includes furniture'})
    tsv('chapter_index.tsv', chapter_rows)
    character_rows = []
    for card in docs['OEBPS/text/characters.xhtml'].iter():
        if 'char-card' in classes(card):
            name = next((compact(e) for e in card.iter() if 'ci-name' in classes(e)), '')
            portraits = [e.get('src') for e in card.iter(X + 'img')]
            character_rows.append({'name': name, 'portraits': ' | '.join(portraits), 'anchor': card.get('id', '')})
    tsv('character_index.tsv', character_rows)
    tsv('glossary_index.tsv', [{'term': compact(e)} for e in docs['OEBPS/text/glossary.xhtml'].iter() if 'gl-term' in classes(e)])
    variants = ['Bae Do-yoon', 'Do-yoon', 'Bae Yun', 'Pei Yun', 'Jessica Jung', 'Jessica',
                'Lee Boo-jin', "Girls' Generation", 'SNSD', 'SM Entertainment',
                'Seoul National University', 'Han River', 'Favor of Rich Women',
                'Favoured by Rich Women', 'Golden Trait']
    variant_rows = []
    for variant in variants:
        counts = {Path(n).stem: len(re.findall(r'(?<![A-Za-z])' + re.escape(variant) + r'(?![A-Za-z])', text(docs[n].find(X + 'body')))) for n in chapter_names if n in docs}
        counts = {k: v for k, v in counts.items() if v}
        variant_rows.append({'variant': variant, 'occurrences': sum(counts.values()), 'chapters': ', '.join(counts)})
    tsv('name_variants.tsv', variant_rows)
    tsv('style_usage.tsv', [{'class': c, 'occurrences': sum(uses.values()), 'chapters': ', '.join(sorted(uses))} for c, uses in sorted(block_usage.items())])
    tsv('editorial_review.tsv', review)
    source_rows = []
    for folder in ['raws', 'image-search']:
        for path in sorted((ROOT / folder).glob('*')):
            if not path.is_file():
                continue
            data = path.read_bytes()
            source_rows.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data), 'sha256': sha(data)})
    tsv('source_inventory.tsv', source_rows)
    assets = []
    if args.assets:
        for name, path in sorted(files.items()):
            try:
                if path.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
                    with Image.open(path) as image:
                        image.load()
                        assets.append({'path': name, 'type': image.format, 'detail': f'{image.width}x{image.height} {image.mode}', 'status': 'decoded'})
                elif path.suffix == '.woff':
                    with TTFont(path, lazy=False) as font:
                        for tag in font.keys():
                            _ = font[tag]
                        assets.append({'path': name, 'type': 'WOFF', 'detail': f'{len(font.getBestCmap() or {})} mapped codepoints', 'status': 'decoded'})
            except Exception as exc:
                errors.append(f'{name}: asset decoding: {exc}')
        tsv('asset_validation.tsv', assets)
    gates = {}
    commands = {
        'validate_tree': [sys.executable, 'validate_tree.py'],
        'punct_quotes': [sys.executable, 'punct_quotes.py'],
        'audit_marks': [sys.executable, 'audit_marks.py', *['work_epub/' + n for n in chapter_names]]
        if chapter_names else None,
        'repeat_check': [sys.executable, 'repeat_check.py', *[Path(n).name for n in chapter_names]]
        if chapter_names else None,
        'legacy_firewall': [sys.executable, 'legacy_firewall.py', '--json', 'reports/firewall.json'],
    }
    lint = ROOT / 'node_modules/.bin/stylelint'
    if lint.exists():
        commands['stylelint'] = [str(lint), '--config', '.sl.json', 'work_epub/OEBPS/styles/*.css']
    for label, command in commands.items():
        if not command:
            gates[label] = 'no chapters in tree yet'
            continue
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (REPORTS / f'{label}.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
        gates[label] = result.returncode
    if not lint.exists():
        gates['stylelint'] = 'not installed; npm ci required'
    summary = {
        'epub': BOOK.name, 'packaged': BOOK.exists(),
        'sha256': sha(BOOK.read_bytes()) if BOOK.exists() else None,
        'bytes': BOOK.stat().st_size if BOOK.exists() else None,
        'archive_entries': len(infos), 'extracted_files': len(files),
        'package_state': 'built' if BOOK.exists() else 'not built yet (setup cycle)',
        'archive_only': archive_only, 'tree_only': tree_only, 'changed_files': changed,
        'xml_documents': len(docs), 'chapters': len(chapter_names),
        'xhtml_files': sum(n.endswith('.xhtml') for n in files),
        'manifest_items': len(items), 'spine_items': len(spine),
        'ncx_navpoints': len(points), 'nav_li': len(list(nav.iter(X + 'li'))),
        'images': sum(i.get('media-type', '').startswith('image/') for i in items),
        'fonts': sum(i.get('href', '').endswith('.woff') for i in items),
        'highest_numeric_image_id': max((int(i.get('id')[3:]) for i in items if re.fullmatch(r'id-\d+', i.get('id', ''))), default=0),
        'image_manifest_items': sum(1 for i in items if re.fullmatch(r'id-\d+', i.get('id', ''))),
        'glossary_cards': sum('glossary-card' in classes(e) for e in docs['OEBPS/text/glossary.xhtml'].iter()),
        'introductions_cards': sum('char-intro-block' in classes(e) for e in docs['OEBPS/text/introductions.xhtml'].iter()),
        'front_matter_order': spine_hrefs[:len(FRONT_ORDER)],
        'next_chapter_slot': f'ch{len(chapter_names) + 1:03d}',
        'next_ncx_play_order': len(points) + 1,
        'next_nav_li_after_chapters': len(chapter_names) + 8,
        'character_cards': sum('char-card' in classes(e) for e in docs['OEBPS/text/characters.xhtml'].iter()),
        'reference_checks_note': 'Every href, src and CSS url() resolved inside the tree; fragments checked against document IDs.',
        'reference_checks': len(references), 'body_words_including_furniture': sum(r['body_words'] for r in chapter_rows),
        'asset_decoding': 'performed' if args.assets else 'not requested',
        'assets_decoded': len(assets), 'legacy_gate_exit_codes': gates,
        'editorial_review_counts': dict(collections.Counter(r['kind'] for r in review)),
        'structural_errors': sorted(set(errors)),
        'scope_note': f'Automated full-tree scan, not semantic proof of all {len(chapter_names)} chapters; regex editorial flags require human review. This script does not perform EPUBCheck or reader rendering; see separate cycle reports for any additional proof.',
    }
    (REPORTS / 'workspace_audit.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
