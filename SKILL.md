# SKILL.md — Novel → Publisher-Grade EPUB 3 Production

**What this skill produces:** A complete, styled, illustrated EPUB 3 novel (Chinese web-novel source → publisher-grade English ebook) plus a synchronized Next.js landing page that serves the package for download.

**Proven on:** *Peninsula: My Rise to Chaebol Status Began with Ham Eun-jung* — 113 chapters, 20+ style-block families, 22 illustrated character files, wardrobe photo pages generated with identity-preserving AI, 10.8 MB package, browser-verified end to end.

**Division of documents (no duplication):**

| Document | Owns |
|---|---|
| `SKILL.md` (this file) | The **process** — stages, pipelines, quality gates, scripts, lessons |
| `epub/STYLE_GUIDE.md` | The **book's voice** — identity rules, translation replacements, tone |
| `epub/OEBPS/styles/stylesheet.css` | The **class catalog** — every style block's CSS (source of truth) |
| `epub/CHAPTERS_MANIFEST.md` | The **chapter map** — ch ↔ Chinese title ↔ English title ↔ line ranges |
| `worklog.md` | The **audit trail** — append a record after every session (template at end) |

---

## 0. The Four Standing Mandates (read first, every session)

| # | Mandate | Enforcement |
|---|---|---|
| 1 | **Deep Scan & Deep Thinking** | Read every relevant file/line BEFORE acting. Never write a chapter, block, or prompt from memory alone — re-scan precedents each session. |
| 2 | **Raws First** | Save the user's original text **verbatim** into `epub/raw/` before ANY other work. One file per chapter (`chNNN.txt`). Never edit raws after saving. |
| 3 | **Style Blocks — No Compromising** | Maximum style-block density in every chapter. When the raw gives thin context for a block, **complete it from deep-thinking world knowledge** (dates, amounts, org charts, clause language) rather than dropping the block. |
| 4 | **Pre-Package Deep Audit** | Before every packaging pass, re-scan the whole batch: question-mark parity, missing blocks, CJK leakage, XML validity, class coverage, image coverage, beat fidelity (§5). |

---

## 1. Workspace Anatomy

```
<repository-root>/
├── epub/                          # THE BOOK SOURCE (never delete)
│   ├── raw/                       # Verbatim source archive (mandate 2)
│   │   ├── full-novel-source-raw.txt     # original novel, ch 1–84
│   │   ├── pasted-batch-ch085-091.txt    # original paste, ch 85–91
│   │   └── chNNN.txt                      # per-chapter raws, ch 85+
│   ├── OEBPS/
│   │   ├── text/                  # chapterNN.xhtml + cover/title/copyright/
│   │   │                          # characters/introductions/nav.xhtml
│   │   ├── images/                # char-*.jpg|png portraits, wd-*.jpg wardrobe,
│   │   │                          # cover-bg.jpg/png
│   │   ├── styles/                # stylesheet.css (269 classes) + fonts.css
│   │   ├── fonts/                 # 17 .woff faces
│   │   ├── content.opf            # manifest + spine + dcterms:modified
│   │   └── toc.ncx                # legacy TOC (playOrder contiguous)
│   ├── META-INF/container.xml
│   ├── mimetype                   # "application/epub+zip" (created by packager)
│   ├── STYLE_GUIDE.md             # voice/translation bible
│   └── CHAPTERS_MANIFEST.md       # chapter map
├── public/
│   ├── book/                      # md5-identical copies of images the landing
│   │                              # page displays (kept in sync at install time)
│   ├── Peninsula_Rising_Chaebol.epub   # THE DELIVERABLE (10.8 MB, 185 entries)
│   └── logo.svg
├── scripts/                       # exactly 3 canonical scripts (§6)
│   ├── package_epub.sh
│   ├── wardrobe-crop.py
│   └── gen-wardrobe-110-113.mjs   # i2i pipeline reference implementation
├── src/app/page.tsx               # landing page (single route "/")
├── SKILL.md                       # this playbook
└── worklog.md                     # shared audit trail
```

**Clean-workspace rule:** disposable by design — image candidates (v1–v18), face crops, VLM result JSONs, browser verify screenshots, `tool-results/`, upload leftovers, one-off generation scripts. **Never disposable:** `epub/raw/`, the whole `epub/` tree, `public/book/` synced images, the packaged EPUB, the 3 canonical scripts, `worklog.md`.

---

## 2. Production Pipeline — Stages S0 → S10

Every new chapter batch runs the full sequence. Each stage is executed exactly once, in order.

### S0 — Save the Raws (mandate 2)
1. User pastes Chinese chapters → write each verbatim to `epub/raw/chNNN.txt` **before anything else**.
2. Batch-source pastes (multi-chapter) → also archive the whole paste as `pasted-batch-chNNN-NNN.txt`.
3. Update `epub/CHAPTERS_MANIFEST.md` rows (Ch / line-range / Chinese title / English title).

### S1 — Deep Scan Before Writing (mandate 1)
Re-read, every session:
- `epub/STYLE_GUIDE.md` **completely** (identity rules, replacement table, tone).
- `CHAPTERS_MANIFEST.md` rows for the incoming batch.
- The 2–3 most recently written chapters (voice + block-precedent refresh).
- Markup precedents for every block family you plan to touch (grep an old chapter that used it).
- Established terminology: honorifics (`Sajangnim`, `oppa`, `noona`), card names (`Healing Card`, `Radiant Charm Card`, `Twin Flowers Mirror`), nicknames, currency figures, dates, addresses.
- Continuity ledger: who knows what, relationship temperature, housing floors, company headcounts.

### S2 — Chapter Conversion (CN → styled EN XHTML)
- Output: one `epub/OEBPS/text/chapterNN.xhtml` per chapter (~3,000–3,600 words each).
- Translate per `STYLE_GUIDE.md` (Korean-American MC, romanized Korean names, LA→Seoul frame, K-pop era accuracy: 2012 T-ara crisis timeline).
- **Style-block maximization (mandate 3):** map every raw beat to the richest applicable family from §3. Rules of thumb:
  - Any teaching/explaining passage → `lecture-block` (fill the Q&A from world knowledge).
  - Any number run (money, leverage, org counts) → `finance-block` or `status-panel`.
  - Any deal → `contract-block` with real clause language (Article I–IV, figures, term).
  - Any time/place jump → `location-stamp`; any scene cut → `scene-break`.
  - System/game panels → `system-block`; phone UI → `notification` / `chat-container` / `phone-call`.
  - Fan/gossip reaction → `comment-thread` (floor numbers, handles, upvotes).
  - Outfit beat → `wardrobe-block` (+ wd-photo pipeline S4).
- Every direct interrogative in the raw **must** end with `?` in English (see gate G1).
- Aim: no long stretch of bare `<p>` prose without an inline device (`thought`, `sound-effect`, `pullquote`, `beat`).

### S3 — Character Portraits (real-person reference search)
1. Use the **image-search** skill (backend `z-ai-web-dev-sdk`, never client-side) for each new on-screen character.
2. Curate 3–6 candidates; pick the one matching age/look/era.
3. Install as `epub/OEBPS/images/char-<firstname>.jpg` (or `.png`).
4. VLM-verify the pick (identity, era-plausibility) before committing.
5. md5-copy to `public/book/` if the landing page will show it.
6. Write the `char-intro-block` in `introductions.xhtml` (chronological by first bow) and/or a `char-card` in `characters.xhtml`.

### S4 — Wardrobe Photos (i2i identity-preserving pipeline) ★ core image skill
**Principle:** never text-to-image a known face — identity scores 25–45/100. Feed the character's actual portrait as the **base input image** to `images.generations.edit` so the model paints real face pixels — scores 85–98/100.

Pipeline (all stages resumable/idempotent — safe across server restarts):
1. **gen** — 6 variants per round (up to 3 rounds = v1–v18) at **864×1152**, prompt = scene + full outfit item list + *"Preserve her exact facial identity from the original photo — same face shape, eyes, nose, lips, skin tone; do not beautify or slim the face."*
2. **crop** — Haar face crops to 768×768 via `scripts/wardrobe-crop.py` (reference portrait + every variant).
3. **fixcrops** — VLM audits each crop; Haar misfires (background/hands) get VLM-guided box re-crops.
4. **score** — **3 VLM trials per variant** with a forensic identity rubric; record the **MEDIAN** (honest scoring — single trials are bimodal).
5. **wardrobe** — VLM verifies **every outfit item** on every high-scoring variant, item by item.
6. **install** — strict gate: `median ≥ 80 AND all wardrobe items verified`. If no variant passes: `install <variantId>` force-installs the mildest miss and the compromise is **reported honestly** (e.g. "pillow crease never renders on any of 6 variants").
7. **final** — one VLM cross-verification installed-image vs base portrait.
8. Install writes `epub/OEBPS/images/wd-<name>-<scene>.jpg` + md5-identical copy to `public/book/`.

Reference implementation: `scripts/gen-wardrobe-110-113.mjs` (§6).

### S5 — Character Files & Introductions Refresh
- `characters.xhtml` cards: update Status / Housing / Handbook rows + bio paragraphs for characters whose state changed this batch.
- `introductions.xhtml`: add `char-intro-block` for newly on-screen characters; refresh stale "Also in Orbit" mentions.

### S6 — Metadata Wiring (N → N+k chapters)
Every batch must update **all** of:
1. `content.opf`: +k `<item>` manifest entries (text + any new images), +k `<itemref>` spine entries, refreshed `dcterms:modified` (UTC), updated `<dc:description>` chapter count.
2. `nav.xhtml`: +k `<li>` entries (labels = chapter `h1` titles exactly).
3. `toc.ncx`: +k `<navPoint>` entries, playOrders 1..N+k **contiguous**.
4. `title.xhtml` / `copyright.xhtml`: spelled-out chapter count ("One Hundred Thirteen Chapters").
5. `CHAPTERS_MANIFEST.md`: +k rows.
6. Landing page (S9).

### S7 — Pre-Package Deep Audit (mandate 4)
Run every gate in §5 over the whole batch. Fix and re-run until green.

### S8 — Package
```bash
bash scripts/package_epub.sh        # → public/Peninsula_Rising_Chaebol.epub
```
- Packager guarantees: `mimetype` FIRST entry, STORED uncompressed; rest deflated; `-X` no extra attrs.
- Update `dcterms:modified` in `content.opf` to the packaging minute **before** running.
- Verify: entry count, mimetype check output, byte size; spot-unzip and confirm new chapters + images are inside (md5-identical to disk).

### S9 — Landing Page Sync (`src/app/page.tsx`)
Update on every batch:
- Badge: `EPUB 3 · {size} MB` (two places).
- Edition feature: `"{N} Chapter Edition"`.
- `VOLUME_ONE/TWO/THREE` arrays: append rows `{ ch, title }`.
- Cast cards: descriptions for characters whose story moved.
- Keep download logic: `a.href = '/Peninsula_Rising_Chaebol.epub'` + `downloaded` state → "Downloaded — Enjoy!".

### S10 — Browser Verification (golden path, agent-browser)
1. `/` renders: badge text, "{N} Chapter Edition", "One Hundred {N} Chapters", "Ch. …–{N}" all present.
2. Volume accordion expands; newest rows visible.
3. Download button → success state; EPUB served with correct byte count + `application/epub+zip`.
4. Zero broken images; mobile 390px: zero horizontal overflow; footer stuck to bottom on short pages.
5. Console clean; `dev.log` all-200.

---

## 3. Style Block Library (catalog — one line per family)

Source of truth: `epub/OEBPS/styles/stylesheet.css` (269 classes). Use-when + precedent column lives in old chapters — grep the class to see real markup.

| Family | Key sub-classes | Use when |
|---|---|---|
| `chapter-header` | `chapter-number chapter-rule chapter-title chapter-divider` | every chapter opening |
| `location-stamp` | `ls-date ls-place ls-sub` | every time/place jump |
| `scene-break` | — | scene cuts |
| `lecture-block` | `lect-header lect-q` | any explaining/teaching passage |
| `contract-block` | `ct-header ct-clause ct-figure ct-note` | deals, agreements, terms |
| `finance-block` | `fb-header fb-row fb-label fb-value` | money/position math |
| `system-block` | `sys-header sys-line sys-key sys-value sys-note sys-ding sys-stat*` | Goddess-Handbook / game panels |
| `briefing-block` | `bf-band bf-title bf-source bf-item bf-key` | org charts, building floors, headcounts |
| `wardrobe-block` | `wd-header wd-tag wd-photo wd-caption wd-label wd-effect wd-note wd-item` | outfit beats (+ S4 photo) |
| `phone-call` | `pc-head pc-me pc-them pc-note` | live calls |
| `notification` | — | SMS / push alerts |
| `chat-container` | `chat-header chat-name chat-meta chat-sent chat-received chat-sticker chat-bubble chat-clear` | messenger threads |
| `comment-thread` | `comment-header comment-item comment-floor` | forum/fan reaction (Nate Pann) |
| `news-digest` | `nd-headline nd-source` | press headlines round-up |
| `official-statement` | `os-masthead os-title os-clause os-meta os-sign` | agency press releases |
| `official-post` | `op-band op-handle op-meta op-body` | official fancafe posts |
| `fanclub-block` | `fc-header fc-user fc-post fc-text fc-modnote` | fancafe community posts |
| `hate-wall` | `hw-header hw-note hw-scrawl hw-voice hw-reply hw-close` | malicious comment walls |
| `world-dispatch` | — | global industry reaction |
| `dossier-block` | `dg-header dg-flag dg-label dg-field dg-value dg-msg dg-transcript` | intelligence dossiers |
| `status-panel` | `sp-header sp-row sp-label sp-value sp-bar sp-total sp-subject sp-note` | measurable status boards |
| `studio-block` | `st-header st-row st-label st-value st-note` | recording-studio logs |
| `recording-block` | `rec-header rec-time rec-voice rec-voice2 rec-dot rec-note` | tape/voicemail transcripts |
| `performance-block` | `pf-header` | stage performance framing |
| `variety-block` | `vt-header vt-tag vt-mission vt-rule vt-verdict vt-caption` | variety-show segments |
| `acting-block` | `ac-heading ac-slate ac-direction ac-cue ac-line ac-note` | script/acting sides |
| `award-block` | `aw-header aw-laurel aw-winner aw-work aw-note` | award ceremonies |
| `box-office` | `bo-header bo-row bo-rank bo-title bo-figure bo-label bo-note` | chart numbers |
| `trend-block` | `tr-header tr-rank tr-artist tr-work tr-cat tr-hot` | trending/search charts |
| `lyric-block` | `lb-header lyric lb-note` | song lyrics |
| `memory-block` | `mb-label mb-voice` | flashback voices |
| `whisper-block` | `wh-label wh-voice wh-reply wh-close` | whispered exchanges |
| `placement-reel` | `pr-header pr-show pr-item pr-note` | product-placement beats |
| `hand-letter` / `hand-note` | `hl-label hl-sign hn-label` | handwritten notes |
| `char-card` | `char-bio char-note` | character profile cards |
| `char-infobox` / `char-intro-block` | `ci-name ci-role ci-photo ci-photo-wrap ci-caption ci-desc ci-group ci-table ci-born ci-tag ci-body` | character files & intros |
| `screen-view` | `sv-header sv-scene sv-line sv-note sv-caption` | device screens |
| `app-screen` | `app-title app-meta` | phone app UI |
| `pullquote` | — | one-line chapter-defining quotes |
| `sound-effect` | — | SFX (Ding! Beep! Click-clack!) |
| `thought` | — | inner monologue |
| `highlight` / `highlight2` | — | inline emphasis |
| `beat` / `action-beat` / `dialogue-line` / `no-indent` | — | prose rhythm devices |
| `cover-*` / `title-*` / `toc-wrap` / `page-wrapper` | — | book framing pages |

**Maximization doctrine (mandate 3):** a 4-chapter batch should land 15–20+ major blocks. Thin raw context is **not** a reason to skip a block — complete it from deep thinking (the lecture the MC would actually give, the clause a real contract would carry, the floor plan a real agency would have).

---

## 4. AI Image Skills (z-ai-web-dev-sdk — backend only, never client-side)

| Skill | API | Used for | Key parameters |
|---|---|---|---|
| **image-search** | image-search skill / SDK | real-person portrait references | curate 3–6 candidates, pick era-accurate |
| **image edit (i2i)** | `zai.images.generations.edit` | wardrobe photos, outfit edits | base = existing portrait; 864×1152; identity sentence in prompt |
| **VLM** | `zai.chat.completions.create` (image content) | scoring, wardrobe item checks, crop audits | forensic rubric; **3 trials → median** |
| **TTS / ASR / video** | available but unused in this pipeline | — | — |

**Honest scoring protocol (applies to every AI-generated image):**
1. Crop the face (Haar 768×768; VLM-guided re-crop on misfire) before comparing.
2. Score with **3 independent VLM trials**, take the **median** — single trials swing wildly (bimodal verdicts observed).
3. Gates: identity median ≥ 80 to install; wardrobe items **all** verified, else honest-compromise install with the failure named in the report.
4. Expect final full-frame-vs-portrait scores ~75–85 even for good installs (small figure vs close-up reference); face-crop medians are the real signal.

---

## 5. Quality Gates (run all before every packaging)

- **G1 Question-mark parity:** count `？`/interrogatives in each raw vs `?` in the English chapter. English count must be ≥ raw count. Known trap: translators "statement-ize" questions — run a restoration pass (ch111 once needed +14).
- **G2 Zero CJK:** no Chinese characters anywhere in shipped XHTML (`[\u4e00-\u9fff]` scan). Zero straight quotes `"` `'` in text nodes (curly only).
- **G3 XML + classes:** every changed file parses as XML; every class used exists in `stylesheet.css`.
- **G4 Images:** every `src` resolves on disk; every image in `text/` is manifest-covered in `content.opf`; landing-page copies in `public/book/` are md5-identical to `epub/OEBPS/images/`.
- **G5 Integration counts:** disk chapters = opf manifest = opf spine = nav entries = ncx navPoints = N; playOrders 1..N contiguous; nav labels exactly equal chapter `h1`s; no stale old counts anywhere (only legitimate title mentions excepted, e.g. ch109's own title).
- **G6 Beat fidelity:** spot-check 20+ raw beats per chapter survived translation (grep distinctive nouns/numbers both sides; resolve every false flag before packaging).
- **G7 Identity (images):** installed wd-photos carry face-crop median ≥ 80 (or documented honest compromise) + item-verification results in the worklog.

---

## 6. Canonical Scripts (the only 3 that live in `scripts/`)

| Script | Role | Usage |
|---|---|---|
| `scripts/package_epub.sh` | EPUB 3 packager | `bash scripts/package_epub.sh` → `public/Peninsula_Rising_Chaebol.epub`; mimetype-first/stored guaranteed |
| `scripts/wardrobe-crop.py` | Haar face-cropper | `python3 scripts/wardrobe-crop.py <job> [--boxes boxes.json]`; add a `JOBS` entry per new character; `--boxes` = VLM-guided overrides |
| `scripts/gen-wardrobe-110-113.mjs` | i2i wardrobe pipeline reference | `bun run scripts/gen-wardrobe-110-113.mjs <job> <stage> [arg]`, stages `gen [round] / crop / fixcrops / score / wardrobe / install [id] / final / describe` — fork it per new book: swap `JOBS` (refImg/outDir/destImg/prompts), keep the stage machine |

---

## 7. Gotchas Archive (each lesson cost real hours)

1. **Text-to-image cannot hold a known face** (25–45/100). Always i2i from the portrait itself.
2. **Single VLM verdicts are unstable** — always 3 trials, median.
3. **Haar face detection misfires** on hands/background — audit crops with VLM, re-crop from guided boxes.
4. **429 rate limits** hit during multi-variant VLM scoring — build retry/backoff, ride it out.
5. **Micro-details never render** (pillow creases, exact makeup-bare state) — when all variants fail one item, force-install the mildest and say so.
6. **The question-mark shortfall** is the most common pre-package bug — count per chapter, restore interrogatives.
7. **User-edited EPUB chapters arrive Calibre-mangled** — normalize XML declaration/DOCTYPE and straight quotes (text nodes only) when importing; preserve user content verbatim otherwise.
8. **Servers die mid-pipeline** — every generation script must be stage-based, idempotent, and resumable (`state.json`/per-stage outputs).
9. **Stale counts hide in five places** — opf description, nav, ncx, title page, landing page. G5 catches them.
10. **Raws are unrecoverable once lost** — ch92/ch93 raws predate the archive rule and are gone; the mandate exists because of this.

---

## 8. New-Book Bootstrap (start book #2 from this repo)

1. `mkdir -p epub/raw` → save the full source verbatim (S0). Build `CHAPTERS_MANIFEST.md` rows as chapters arrive.
2. Copy `epub/` tree skeleton: mimetype/META-INF/OEBPS structure, `stylesheet.css` + `fonts.css` + fonts (reuse the whole design system), cover/title/copyright templates.
3. Write a fresh `STYLE_GUIDE.md` for the new book's identity rules (name romanization policy, setting frame, tone).
4. Fork `gen-wardrobe-110-113.mjs` `JOBS` for the new cast; add `JOBS` entries to `wardrobe-crop.py`.
5. Run S1→S10 per batch. Append every session to `worklog.md`:

```markdown
---
Task ID: <id>
Agent: <agent name>
Task: <what was asked>

Work Log:
- <concrete steps>

Stage Summary:
- <key results / decisions / artifacts>
```

6. Clean as you go: candidates, crops, verify screenshots and one-off scripts are disposable; raws, book tree, synced images, canonical scripts, worklog are not.
