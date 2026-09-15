# Project handoff — *Peninsula: My Rise to Chaebol Status Began with Ham Eun-jung*

This repository is the production workspace for the 113-chapter English EPUB edition of
*Peninsula: My Rise to Chaebol Status Began with Ham Eun-jung*. It is an EPUB translation and
illustration workspace, not a web app; do not start a dev server here.

## Read first

1. `SKILL.md` — the production process and quality gates.
2. `epub/STYLE_GUIDE.md` — voice, continuity, names, terminology, and XHTML conventions.
3. `epub/CHAPTERS_MANIFEST.md` — chapter map and raw-source custody notes.
4. `worklog.md` — the complete audit trail; the newest entry is the workspace-setup checkpoint.
5. `WORKSPACE_SETUP.md` — the extracted-package inventory and current source-of-truth map.

## Non-negotiables

- **Book identity:** title *Peninsula: My Rise to Chaebol Status Began with Ham Eun-jung*;
  protagonist **Song Ji-yeon**. Do not import identities, companies, terminology, or plot from
  another book.
- **Source of truth:** editable EPUB files live under `epub/` (`epub/OEBPS/` plus `epub/raw/`).
  `extracted/` is an immutable unpacked snapshot of the latest supplied package and is not the
  working tree for editorial edits.
- **Raw-first:** preserve user-supplied source verbatim under `epub/raw/`. Never edit an archived
  raw file in place.
- **Image realism and identity:** portraits represent the intended real-person reference. A
  wardrobe image must be generated from that character’s actual portrait using the identity-
  preserving image-to-image workflow in `SKILL.md`; never text-to-image a known face and call it
  a match. Verify the face and every wardrobe item before installation, and record compromises in
  `worklog.md`.
- **Package output:** the deliverable is `public/Peninsula_Rising_Chaebol.epub`. Do not rebuild it
  casually: run the pre-package gates and update the worklog first.
- **No secrets:** do not put API keys, tokens, or private credentials in the repository.

## Current tree

```text
epub/
  META-INF/                 EPUB container metadata
  OEBPS/                    extracted/editable book tree
    text/                   113 chapters plus front matter
    images/                 portraits, cover art, and installed wardrobe plates
    styles/                 stylesheet.css and fonts.css
    fonts/                  embedded WOFF faces
  raw/                      verbatim source archive
  STYLE_GUIDE.md
  CHAPTERS_MANIFEST.md
extracted/                  exact unpacked snapshot of public/*.epub
public/
  Peninsula_Rising_Chaebol.epub
  book/                     landing-page image copies
scripts/                    canonical packaging and wardrobe helpers
```

## Useful commands

```bash
python3 validate_tree.py
python3 check_classes.py
python3 punct_quotes.py
python3 audit_marks.py epub/OEBPS/text/chapter110.xhtml
python3 style_index.py --check-skill
python3 style_audit.py --json reports/style_audit.json
python3 legacy_firewall.py --json reports/firewall.json
python3 workspace_audit.py --assets
python3 build_epub.py                 # only after an authorized editorial/package pass
bash scripts/package_epub.sh          # same deliverable, shell packager
```

`install_fonts.py` is reproducible when the matching `@fontsource` packages are available; the
setup already contains the 17 embedded faces extracted from the latest EPUB. The wardrobe helper
is resumable and stage-based; keep generated variants and crops disposable unless an installed
asset is explicitly required.

## Current verified baseline

- 113 chapter XHTML files are present in `epub/OEBPS/text/`.
- The supplied package has 185 ZIP entries, 179 file entries, 113 chapter documents, 37 images,
  and 17 WOFF faces.
- The package was extracted byte-for-byte into `extracted/`; its SHA-256 is recorded in
  `WORKSPACE_SETUP.md`.
- The latest package remains the baseline deliverable. This setup checkpoint does not editorially
  change chapter prose or package metadata.
