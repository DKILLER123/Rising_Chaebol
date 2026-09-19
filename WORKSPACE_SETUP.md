# Workspace setup — Peninsula EPUB

**Setup date:** 2026-09-15 (UTC)
**Book:** *Peninsula: My Rise to Chaebol Status Began with Ham Eun-jung*
**MC:** Song Ji-yeon
**Edition at extraction:** Version 3 English edition, 113 chapters (the immutable setup snapshot; current editable/package state is 118 chapters)

## What was done

- Read the repository handoff, production skill, style guide, chapter manifest, worklog, source
  raws, packaging scripts, audit scripts, and the supplied EPUB metadata.
- Extracted every file from `public/Peninsula_Rising_Chaebol.epub` into `extracted/`.
- Restored the editable EPUB source tree under `epub/` from that extraction. Existing `epub/raw/`,
  `epub/STYLE_GUIDE.md`, and `epub/CHAPTERS_MANIFEST.md` were preserved.
- Kept `extracted/` as the exact package snapshot for future comparison. Editorial changes belong
  in `epub/`, never in the snapshot.
- Reconciled the copied helper scripts with this book’s paths and identity so future gates operate
  on `epub/` rather than the other book’s `work_epub/` tree.
- No chapter prose, character art, wardrobe plate, or packaged EPUB was changed by setup.

## Extraction inventory

| Check | Result |
|---|---:|
| ZIP entries, including directory entries | 185 |
| ZIP file entries | 179 |
| Extracted files | 179 |
| Chapter XHTML files | 113 (`chapter01.xhtml`–`chapter113.xhtml`) |
| Front-matter XHTML files | 5 |
| Images | 37 |
| Embedded WOFF faces | 17 |
| `mimetype` | first ZIP entry, stored, `application/epub+zip` |
| Archive CRC test | passed |

The package contains `META-INF/container.xml`, `OEBPS/content.opf`, `OEBPS/nav.xhtml`,
`OEBPS/toc.ncx`, all text, image, style, and font payloads, and the root `mimetype` file. Raw
source files remain only in `epub/raw/`; they were never part of the EPUB payload.

## Integrity fingerprints

```text
public/Peninsula_Rising_Chaebol.epub
  SHA-256 f62ebf225202e67b5828c5093bc91ec78abdca630b32787a691875a9dc5b55f4
  10,821,795 bytes

extracted/mimetype
  SHA-256 e468e350d1143eb648f60c7b0bd6031101ec0544a361ca74ecef256ac901f48b

extracted/OEBPS/content.opf
  SHA-256 5d7e7ed0e55ac495fddedd371f3341c58c3469d2fd4e9204fc5b4591f4835e34

extracted/OEBPS/styles/stylesheet.css
  SHA-256 8948f9279aa16f4e8d1880345cf5ea851e9d1a6c1b1b5db9391fd089535e21e9
```

## Working rules for the next cycle

- Edit chapter files and metadata in `epub/OEBPS/`; package only `mimetype`, `META-INF/`, and
  `OEBPS/`. Do not package `epub/raw/` or reports.
- Use `epub/OEBPS/images/char-*.jpg|png` as the identity references for real-person portraits.
  For a `wardrobe-block`, use the matching portrait as the image-to-image base and keep the
  installed image byte-identical in `public/book/` only when the landing page needs it.
- Run the structural gates before packaging. `workspace_audit.py --assets` writes machine-readable
  reports under `reports/`; reports are audit artifacts, not EPUB payload.
- The extracted snapshot is a forensic baseline. If the working source intentionally changes, the
  archive parity report should show those changes; do not overwrite `extracted/` to hide them.

## Baseline notes discovered during the scan

- The extracted snapshot is the 113-chapter build documented at the end of the setup checkpoint in `worklog.md`; the current deliverable is the subsequent 118-chapter build.
- At extraction, `epub/OEBPS/text/copyright.xhtml` still contained a historical “one-hundred-nine
  chapter” description while the package metadata and title page identified 113 chapters. The
  authorized 114–118 editorial pass corrected the front matter to 118 chapters and re-ran the
  count/package gates.
- The raw archive has the documented historical gap for chapters 92–93; the corresponding English
  chapter XHTML files are present and packaged.
- The question-parity report (`reports/question_parity.tsv`) covers 110 chapters with retained raws:
  97 pass the simple raw-`？` versus English-`?` count and 13 need an editorial restoration review
  (chapters 16, 17, 25, 30, 31, 48, 54, 76, 87, 91, 94, 96, and 99). This is intentionally
  recorded rather than silently altering existing translation during setup.
- The full mark audit and style audit are also preserved under `reports/`. The mark audit found
  existing phone-call continuation blocks without a header and punctuation/question triage in
  older chapters; the style report records that the extracted 113-chapter baseline was below the
  eight-distinct-block floor in many chapters. These remain the inherited editorial QA queue, not
  package extraction failures.
