---
name: movie-srt-zh-tw
description: >-
  End-to-end automated workflow to translate English movie, documentary, or
  series `.srt` subtitles into idiomatic Taiwan Traditional Chinese
  (`_zh-TW.srt`) with lossless 1-to-1 timeline verification, a unified
  `Translation_Bible.md`, parallel semantic chunk translation, and automated
  `QA_Report.md` validation. Use when the user asks to translate, localize, or
  QA an English `.srt` subtitle file into Taiwan Traditional Chinese.
---

# Movie SRT to Taiwan Traditional Chinese (`movie-srt-zh-tw`)

Automated pipeline combining deterministic Python chunking/QA with context-aware LLM semantic translation so long feature-length `.srt` files (>3,000 lines) never suffer truncation, drifted timecodes, broken multi-line sentences, inconsistent character names, or Mainland Chinese phrasing.

- Bundled script: [srt_helper.py](./scripts/srt_helper.py) (`split`, `boundaries`, `merge`, `qa`)
- Style & punctuation reference: [localization_rules.md](./references/localization_rules.md)

---

## Prerequisites

1. **Locate Python 3:** Verify `python` (or on Windows check `$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe`). If missing on Windows, install Python 3.12 user-scope silently via `winget install --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements`.
2. **Stage Input File:** If the user uploaded an `.srt` file outside the active workspace, copy it into the workspace preserving its original filename. Determine `<output_srt>` as `<stem>_zh-TW.srt` (stripping trailing `.eng` / `.en` / `_en` if present, e.g., `Film.2026.eng.srt` → `Film.2026_zh-TW.srt`).
3. **Copy or Invoke Helper:** Copy [srt_helper.py](./scripts/srt_helper.py) into the working folder (if the user wants standalone workspace tooling) or invoke it directly by path from the working folder.

---

## Stage 1: Split & Source Timeline Audit

Run `split` on the source English `.srt`:

```powershell
python "<skill_dir>/scripts/srt_helper.py" split --input "<source.srt>"
```

**Verify output before continuing:**
- Confirm `./chunks/chunk_01.json`..`chunk_NN.json` (60 cues each, with `prev_context` and `next_context`) were created.
- Check the printed **Source timeline sanity** metrics (`non_seq_ids`, `non_pos_dur`, `out_of_order`, `overlaps`). If any source overlap or zero/negative duration exists, note it for the final QA report.
- Note whether the source track is **SDH/CC** (contains `<i>`, `SPEAKER:`, `(SFX)`) or **clean narrative** (pure dialogue + optional `♪` lyrics).

---

## Stage 2: Build `Translation_Bible.md`

Quickly survey all `./chunks/chunk_*.json` files (for long films ≥ 15 chunks, delegate a read-only `research` subagent to read every chunk and also inspect speakers/acronyms/proper nouns via Python), then write `Translation_Bible.md` in the workspace (concise, high-density, ≤ 1,500 Chinese characters):

1. **劇情基調與時代背景：** Genre, era, overall register, and dialogue tone.
2. **核心角色、性格與稱謂表：** All principals (real people vs. re-enactment actors if documentary/meta), gender, personality, nicknames, and fixed pronoun choice (e.g., universal `你` vs. `您`).
3. **專有名詞、雙關語與特殊格式對照表：** Standardized Taiwan Traditional Chinese names for people, places, organizations, media titles, recurring puns/songs/catchphrases, and rules for handling `<i>`, speaker prefixes, sound cues, or dual-speaker `- A - B` lines.

Read [localization_rules.md](./references/localization_rules.md) to ensure every rule is reflected in `Translation_Bible.md`.

---

## Stage 3: Semantic Chunk Translation

1. **Plan Contiguous Scene-Bounded Batches:**
   - For short files (≤ 5 chunks), translate sequentially yourself.
   - For feature films (> 5 chunks), run:
     ```powershell
     python "<skill_dir>/scripts/srt_helper.py" boundaries --chunks-dir chunks
     ```
     Group chunks into 6–10 contiguous batches of **4–7 chunks each**, placing every batch split strictly on a `CLEAN` sentence-end boundary (preferably at silence gaps ≥ 0.7s).
2. **Delegate Parallel Batches (`srt-translator`):**
   - Define a subagent (`EnableWriteTools: true`) using `Model: "inherit"` whose system prompt enforces [localization_rules.md](./references/localization_rules.md) and `Translation_Bible.md`.
   - Give each subagent a **disjoint** contiguous range (`chunk_XX.json`–`chunk_YY.json`) plus batch-specific plot/pun/song notes so recurring scenes across batches use identical wording.
   - Instruct each subagent to:
     - Read chunks in ascending order, reading 3–5 cues ahead (including `next_context`) and reconstructing natural Taiwanese Mandarin word order proportional to `duration`.
     - Update **only** the `"zh"` field in each chunk JSON (never alter `id`, `timecode`, `duration`, `en`, `prev_context`, `next_context`).
     - Apply contextual Chinese punctuation automatically (`，`、`、`、`：`、`。`、`？`、`！` — never use `\u3000` fullwidth spaces for pauses, keep line ends/breaks free of trailing `。`, omit halfwidth spaces between Chinese and English/digits like `歡迎收聽ABC音訊的` and `120奈米`, and leave no stray spaces adjacent to Chinese punctuation).
     - Self-verify its assigned chunks with Python before finishing (0 empty `zh`, 0 `<i>`, 0 `\u3000`, 0 CN/EN/digit spaces, 0 stray spaces near Chinese punctuation, 0 halfwidth `,`/non-decimal `.`/`..`/`--`, ≤ 2 lines, ≤ 16 fullwidth target / 0 > 18, CPS ≤ 13, 0 Simplified/Mainland terms).
   - Do not poll; wait for all batches to complete.

---

## Stage 4: Merge, Bidirectional QA, Polish & Cleanup

1. **Merge & Run QA (Fully Automated — No User Review Pause):**
   ```powershell
   python "<skill_dir>/scripts/srt_helper.py" merge --input "<source.srt>" --output "<output_srt>"
   python "<skill_dir>/scripts/srt_helper.py" qa --input "<source.srt>" --output "<output_srt>"
   ```
2. **Cross-Batch Audit & Iterative Fix:**
   - Read `QA_Report.md` completely.
   - Also run a quick check across all chunks for:
     - Cross-batch boundary continuity (last 3 / first 3 cues at every batch seam).
     - Pronoun consistency (`你` vs. `妳` vs. `您` — watch for misgendered `妳` on off-screen speakers).
     - `residual_en` tokens (confirm every remaining ASCII token is an intentional brand/acronym like `AI`, `Wi-Fi`, `YouTube`, `Netflix`, `Hulu`; translate accidental English like `Email` if appropriate, and ensure no halfwidth spaces surround them in Chinese sentences).
     - Split compound words across line breaks.
   - Fix any issues directly in `./chunks/chunk_XX.json` automatically (do NOT pause to ask the user for line-by-line review), then re-run `merge` and `qa` until:
     - **Critical errors = `0`** (100% 1-to-1 `id` + `timecode` match, 0 empty, 0 HTML, 0 >2 lines, 0 >18 fullwidth, 0 `\u3000`/CN-EN-digit spaces/stray punct spaces/halfwidth punct, 0 Simplified/Mainland terms).
     - **17–18 fullwidth warnings = `0`** (target ≤ 16 fullwidth units everywhere).
     - **CPS > 13 (`>= 1.0s`) = `0`** (and minimize `< 1.0s` cues).
3. **Verify Timeline & Cleanup:**
   - Verify 100% 1-to-1 `id` and `timecode` parity between `<source.srt>` and `<output_srt>` and inspect the head and tail of `<output_srt>`.
   - Delete temporary `./chunks/` directory (keep `<output_srt>`, `Translation_Bible.md`, `QA_Report.md`, and `srt_helper.py` if copied to workspace).
   - Present clickable `file:///` links for download and summarize timeline verification + QA results.
