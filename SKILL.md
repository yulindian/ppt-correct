---
name: ppt-correct
description: Use when producing a corrected, editable, teaching-animated PPT/PPTX from an image-based PDF reference and editable deck, especially with OCR, typography, layout, question-answer reveal, or classroom sequence requirements.
---

# PPT Correct

## Purpose

Repair an editable PPT/PPTX so its editable text layer matches an image-based PDF reference as closely as practical, then add a verified teaching animation timeline without pausing for user approval between phases. Text content and typography are the primary correction target. Illustrations, decorative images, and unrelated artwork are protected inputs: keep them unchanged and exclude harmless raster/compression differences from the correction score. This is correction plus teaching sequencing, not redesign, and full-page PDF images must not be used to cover editable slides as a shortcut.

Change an illustration only when the user explicitly requests it, it is missing or displaced in a way that changes meaning or obstructs text, or it contains semantic text that must become editable. Reconstruct semantic image-baked text locally; leave decorative lettering and non-instructional artwork in the image.

`ppt-correct` is the sole production entry point for correction and teaching animation. It produces exactly one final PPTX: `NAME_动画版.pptx`. Do not automatically invoke `ppt-lesson-writer`, `ppt-photo`, or generate their Word/image outputs. Run those skills only when the user explicitly requests them in the current task or when an external package controller owns that work.

## Inputs

Required:

- Source PDF: final visual/content reference.
- Editable PPT/PPTX: editable layer converted from the PDF.

High-priority when present:

- `PPT内容大纲.txt`: primary source for fast text/OCR correction.
- `字体说明.txt`: primary source for fast font family, role, weight/style, and fallback correction.

Folder mode:

- Find the PDF, editable PPT/PPTX, outline, and font spec in the supplied folder.
- Prefer `NAME.pdf` with `NAME.pdf.pptx`, then `NAME.pptx`.
- Ignore generated files containing `_PDF原图页_隐藏可编辑页` unless the user asks to revise one.
- If the pair is genuinely ambiguous, ask the user to choose.

Combined/interleaved mode:

- Identify editable slides and image-only reference slides from actual contents/hidden state; do not assume odd/even mapping without checking.
- Preserve visible PDF/image pages and edit only editable slides unless the user explicitly asks otherwise.

## Fast Required Workflow

Follow [references/correction-sop.md](references/correction-sop.md). Use OfficeCLI for inspection, batch edits, read-back, and structural validation; read the installed `officecli` skill and confirm its current command schema before use.

The correction phase has three distinct passes:

1. A low-resolution preflight render used only to register pages and triage text differences.
2. A fast correction pass driven by `PPT内容大纲.txt`, `字体说明.txt`, PDF text/OCR evidence, and editable PPT properties.
3. One final full-deck PDF/PPT text reconciliation after the batch correction is stable.

Do not begin with a high-resolution manual page-by-page inspection. Create one inexpensive low-resolution baseline for triage, then render only changed slides or text regions until the final full-deck audit. Do not repeatedly render the full deck after each text box or font change.

Minimum reliable loop:

1. Resolve the PDF/PPT/outline/font-spec inputs and confirm page count, order, dimensions, and editable-slide mapping.
2. Read the outline and font spec completely. Extract editable PPT text and relevant style properties once with OfficeCLI.
3. Render a low-resolution PDF/PPT baseline at matching dimensions. Register page pairs, ignore illustration-only differences, and triage slides as `pass`, `text-content`, `text-style/layout`, or `structural/reconstruction`. Freeze `pass` slides.
4. Build a compact correction ledger for affected text objects. Record the source evidence and confidence for copy changes, preserve pre-edit text/run/style properties, and group same-template peers.
5. Apply high-confidence fixes in batches: text/OCR, font family, weight/bold, size, color/effects only where specified or clearly inconsistent, then text-box stability. Do not change low-confidence copy merely because one source disagrees.
6. Read back the edited content with OfficeCLI, scan for OCR leftovers, and run `validate` / `view issues`. Fix structural or editable-text problems before visual rendering.
7. Re-render changed slides or text regions. Keep a change only when content is correct and the text region is at least as close to the PDF; otherwise restore the saved pre-edit properties and escalate the object.
8. After the batch correction stabilizes, render the final PPT and source PDF once at matching dimensions and compare every page pair in order, prioritizing text and confirming that protected illustrations were not altered.
9. Fix only mismatched text regions. Re-render only affected slides or regions. Re-render the whole deck again only when a global change could affect many slides.
10. Run the static sections of [references/qa-checklist.md](references/qa-checklist.md) and the bundled font/page verifier. This is an internal gate, not a user-approval checkpoint.
11. After the static gate passes, read [references/animation-logic.md](references/animation-logic.md), inspect the lesson plan/speech script and stable shape IDs, and build a temporary per-slide animation plan.
12. Scan exercise slides for embedded or separate answer tokens and judgment marks. Split semantic answers into independent editable shapes when required so no answer leaks before its reveal.
13. Rebuild the teaching timeline in exact plan order. Use restrained entrance effects and keep backgrounds, illustrations, and decorative furniture static.
14. Run `scripts/audit-ppt-animation.ps1`; require zero duplicate animated shapes and zero plan mismatches. Then run final structural validation and render a full contact sheet to confirm animation work did not alter layout.
15. If `$ppt-combine` is also requested, combine only after static correction passes, then apply and verify animation on the combined editable deck.

Do not stop for approval between correction and animation. Maintain a recoverable internal working copy while processing, but deliver only `NAME_动画版.pptx`.

The final one-to-one PDF comparison is mandatory for text acceptance and collateral-change detection; illustration-only raster differences are not repair defects.

## Hard Completion Gate

The final deck is complete only when all of these are true:

- No visible PDF/PPT text mismatch remains in copy, font appearance, hierarchy, size, weight, geometry, wrapping, or clipping, except an explicitly recorded and user-accepted limitation.
- A structural pass or “no overflow” result never overrides a visible mismatch.
- After any font substitution, the affected text objects are rebalanced as a unit: font slots, visible size, weight, line spacing, margins, box geometry, wrapping, and autofit/fontScale.
- For high-salience cover and section titles, matching a broad role label such as “行楷感” is not enough. The rendered stroke mass, glyph structure, width, and visual density must match the PDF closely; compare a closer installed/packaged face when the first role-matched font is visibly different.
- Any cover metadata or heading that is a single line in the reference must remain one line in the delivery application. Use fixed font sizing, `autoFit=none`, explicit margins, and horizontal safety headroom; do not accept `autoFit=shape` or a box that only barely fits in one renderer.
- A matching text-box rectangle is not sufficient when the rendered glyphs have shifted inside it. For titles, labels, questions, and other text associated with a brush stroke, card, banner, tab, or highlight, the visible text ink must occupy the same relative region of that backing element as in the PDF.
- For text inside a card, border, step block, or answer panel, derive a safe content rectangle from the visible backing first. Place and size the text inside that inset; never treat the converter's original text-box rectangle as the positioning authority when it is tiny, offset, or visibly inconsistent with the backing.
- Treat an icon/number badge plus its adjacent text as one row component. Repeated rows must share a common text left edge and the same icon-to-first-line alignment rule; for multiline rows, align the first visible text line to the peer row template instead of centering independent shapes by their raw boxes.
- Same-tier multiline peers must share the complete paragraph geometry of a verified peer: font, size, line spacing, paragraph spacing, margins, vertical anchor, width policy, and autofit. Shape-level font equality alone is not sufficient.
- Do not leave substituted text on application-dependent `normAutofit`/`autoFit=normal`. Use fixed sizing or an explicit stable scale, then verify the affected slide again.
- Protected illustrations and unrelated artwork remain unchanged. Harmless resampling, compression, or renderer differences inside illustration-only regions do not block acceptance.
- Semantic text baked into an image is either reconstructed as editable text or explicitly recorded as a limitation; decorative lettering remains part of the protected illustration.
- The real PowerPoint timing order matches the temporary animation plan, with `duplicateAnimatedShapeCount = 0` and `planMismatchCount = 0`.
- Questions, choices, and learner prompts appear before answers, explanations, model responses, or judgment marks; no answer token is visible on entry unless explicitly intended.
- The fully revealed animated slide matches the corrected static state and source PDF in text and layout.
- When WPS is the known delivery environment, or the user supplies WPS evidence, WPS edit-mode rendering is part of acceptance. If WPS cannot be inspected, label the file a candidate and disclose that it is not final.

If any gate fails, continue correction or report a blocked/candidate result. Do not describe the deck as verified, passed, final, or complete.

## Escalation for Difficult Visual Mismatches

Use [references/visual-matching.md](references/visual-matching.md) only when the final reconciliation reveals an unresolved typography/text-backing mismatch, the font spec is missing or unusable, or the user explicitly requests quantitative high-precision text matching.

Do not build a machine-wide font catalog, run per-text candidate searches, create a region manifest, or require `visual-verification.json` during the ordinary fast path. When escalation is necessary, limit it to the affected font role, slide, or region.

## Style Contract

- Preserve the original conversion-layer style when it already matches the reference.
- Resolve copy from converging evidence: PDF embedded text or high-confidence OCR, `PPT内容大纲.txt`, and existing PPT text. Use the PDF image to settle visible ambiguity. Record rather than silently guess when authoritative sources conflict.
- Treat `字体说明.txt` as authoritative for font roles and fallbacks; use the PDF to judge final visual fit.
- If `字体说明.txt` describes an image-generation “visual target,” treat its families as candidates rather than proof of an exact editable-font match. The PDF remains authoritative for visible size, stroke weight, and spacing.
- Same-template, same-role objects should share font family, size, weight/bold, and color unless the reference intentionally differs.
- Preserve hierarchy between titles, subtitles, body, labels, numbers, captions, and notes.
- Preserve object-specific RGB, partial emphasis, outlines, shadows, highlights, backing shapes, borders, and geometry unless the reference proves they are wrong.
- Repair wrapping, margins, autofit/fontScale, clipping, overflow, vertical stacking, and single-character columns without moving unrelated artwork.
- Treat illustrations, decorative images, and unrelated artwork as locked. Do not include illustration-only pixel differences in font, geometry, or completion decisions.
- Treat a text object and its visual backing as one placement unit. After changing its font, compare the rendered glyph bounds—not only the text-box bounds—with the PDF and the backing region. Correct vertical anchor first, then internal margins, then box `y`/height; do not shrink the font merely to hide positional drift.
- When a converter leaves a tiny or near-zero-height text box, or when edited copy changes the number of lines, rebuild deterministic height from the intended line count and the peer line spacing. Normalize `spaceBefore`/`spaceAfter`, margins, anchor, and autofit explicitly before adjusting `y`.
- Use a visually correct repeated item as the row/paragraph template. Copy its full layout contract to peers, then adjust only the content-dependent height and the backing-relative position. Do not let each peer inherit unrelated source paragraph metrics.
- Keep visible text editable. Use local reconstruction only when a converted object cannot be repaired in place.

## Font Handling

Use this order:

1. Apply `字体说明.txt` mappings and listed fallbacks first. This is the default source of font-role decisions.
2. Reuse a visually compatible Chinese font already present in the deck.
3. If the result still visibly mismatches the PDF, search installed local fonts and select a closer face by glyph coverage and rendered appearance.
4. Use a common compatible Chinese system font only when the earlier choices do not produce a closer match.

When `字体说明.txt` exists, use its role mapping first, but do not ban an unfamiliar, Japanese-, Korean-, or other named family solely because of its name. Such a font may remain only when all three conditions are proven: the exact local font file is present on this machine, that exact face covers every character assigned to it, and the file is copied into the sibling `fonts` package. An embedded font or visually plausible fallback is not enough evidence.

Before final delivery, enumerate directly used typefaces, resolve every family to an exact local `.ttf`, `.otf`, `.ttc`, or `.otc` file, and verify run-character coverage. Replace any unresolved or incomplete-coverage face in all Latin/East-Asian/complex-script slots and at run level. Copy every verified directly used font file into `fonts`, then re-run with `--require-font-files-for-used-fonts`; zero missing mappings and zero missing glyphs are required.

Avoid converter-assigned Japanese or unrelated script fonts for Chinese text. Set Latin, East Asian, and complex-script font slots consistently for Chinese runs when the editing method exposes them.

Check glyph coverage and exact rendered candidate matching only for fonts that display missing glyphs, produce obvious final-PDF mismatches, or are being packaged for portability. Do not make machine-level font cataloging or exhaustive candidate ranking a prerequisite for ordinary correction.

When a newly selected local font is actually used in the final deck, add its exact `.ttf`, `.otf`, or containing `.ttc` file to the sibling `fonts` package. Reuse an existing `fonts` folder; create it only when a newly adopted font is not already packaged. Copy only fonts used by the deck, never the whole Windows font library, and verify that the packaged face supports every assigned character. Keep the PPT font slots and the packaged font family/file mapping consistent.

After a font change, re-check the affected peer group for wrapping, clipping, visible size, weight, color, alignment, and the visible glyph position inside any associated backing element. A tall single-line text box left on top alignment is a high-risk signal: use the PDF to decide whether middle alignment or a reference-matched inset is required. Render representative pages only when needed during the batch pass; the complete deck is rendered for the final audit.

For high-salience cover/display titles, choose by rendered glyph evidence rather than font-category wording alone. Compare stroke thickness, character proportions, terminal/brush shape, total line width, and visual center against the PDF. A readable calligraphic font is still wrong when its strokes are substantially thinner, more cursive, or differently proportioned than the reference.

For cross-application delivery, prefer fixed font sizes and deterministic text-box geometry. `normAutofit` is not a safe compatibility fix because WPS, PowerPoint, and headless renderers may calculate different scales. For reference-single-line cover text, also avoid `autoFit=shape`: widen the text box within the intended visual gap, use explicit zero/reference-matched margins, and keep enough spare width for font substitution and WPS metrics before making a small size or spacing reduction.

Apply that rule to every required single-line heading, card title, banner title, and scene title—not only the cover. A line that merely fits in the OfficeCLI/headless render is not safe. Use `autoFit=none`, zero/reference-matched margins, and at least 15% horizontal headroom (25% for decorative Chinese fonts) relative to the measured rendered line width. If the user supplies a PowerPoint/WPS screenshot showing a wrap, that application screenshot is authoritative over the headless render; repair against it and re-check the same object class across the deck.

If WPS verification is specifically required, inspect in WPS edit mode when available. Otherwise report that WPS was not directly verified rather than delaying the standard workflow.

## Outputs

- Save the sole final deck beside the source material as `NAME_动画版.pptx`.
- Use temporary working copies for the static gate and animation rebuild; after successful verification, do not retain intermediate decks, animation-plan JSON, contact sheets, verification JSON, or trial PPTX files.
- Do not overwrite the original PDF, PPT/PPTX, outline, or font spec.
- Do not create Word companion files, `type-03` images, or a companion-photo folder automatically.
- Maintain the sibling `fonts` package when a newly selected local font is used. Do not rebuild it or add unrelated fonts.
- If `$ppt-combine` is used, the corrected combined deck is an internal intermediate; the animated combined deck is the final `NAME_动画版.pptx`.
- Remove temporary renders, working copies, and superseded intermediate PPTX files after successful verification unless the user asks to keep them. Keep the compact final correction ledger and verification JSON beside the job when they contain unresolved limitations or evidence needed to reproduce the result.
- In the delivery folder, retain the original source files and the final deliverable. Delete superseded trial/repair PPTX files only after the final deck has been verified and the exact deletion targets have been enumerated.

## Verification

Before completion, verify:

- page count/order, slide dimensions, and editable-slide mapping;
- text matches the outline/PDF and no known OCR leftovers remain;
- editable text remains editable;
- slides that passed the preflight baseline were not unnecessarily modified;
- same-template font size, family, color, and boldness are consistent;
- titles, labels, questions, and emphasized text remain visually seated inside their original brush strokes, cards, tabs, banners, and highlight blocks;
- no clipping, overflow, unexpected wrapping, or vertical stacking;
- the final PPTX opens/parses and OfficeCLI validation issues are resolved or disclosed;
- the final full-deck PDF/PPT comparison covers every page pair in order, with text regions as the acceptance target;
- protected illustrations and unrelated artwork were not modified, and illustration-only raster differences did not trigger reconstruction;
- remaining text or semantic image-baked-text limitations are explicitly recorded;
- visible PDF/image reference pages were not modified in combined mode.
- every animated slide follows the teaching sequence recorded in the temporary plan;
- answers, answer letters, reference-answer panels, and judgment marks reveal only after their matching question context;
- the animation audit reports zero duplicate shapes and zero order mismatches;
- the fully revealed animation state preserves the corrected static layout.
- no opaque fill or decorative block was added behind editable text unless the reference visibly contains that same backing; text-box fills must never be used to hide conversion artifacts;
- every mixed-color sentence was checked at run level after whole-shape text replacement, with each emphasized substring retaining its reference-supported color;
- every answer token or judgment mark is visually centered inside its own brackets in the fully revealed state; coordinates may not be reused across questions without per-item verification;
- image-backed/custom-geometry shapes were not treated as ordinary text boxes merely because they expose OCR text metadata;
- high-risk regions were reviewed at slide resolution: paragraph-on-illustration, mixed-color title, bracketed answer, and color-coded label.

Run the bundled verifier for the final deck:

```powershell
python C:\Users\yulin\.codex\skills\ppt-correct\scripts\verify_pptx_fonts_pages_size.py `
  --final "NAME_动画版.pptx" `
  --expected-slide-count N `
  --report "JOB\verification.json" `
  --allow-unembedded-system-fonts `
  --fail-on-normal-autofit
```

Use `verify_visual_regions.py` and `--visual-report` only for specific unresolved/high-risk regions that were escalated under `visual-matching.md`; they are not mandatory for the ordinary fast path.

Audit the real animation timeline before delivery:

```powershell
& C:\Users\yulin\.codex\skills\ppt-correct\scripts\audit-ppt-animation.ps1 `
  -PptPath "NAME_动画版.pptx" `
  -PlanPath "TEMP_ANIMATION_PLAN.json"
```
