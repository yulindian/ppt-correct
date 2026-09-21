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

Follow [references/correction-sop.md](references/correction-sop.md) for the operating steps. Read the installed `officecli` skill and confirm its current command schema before using OfficeCLI.

1. **Register and triage.** Confirm the PDF/PPT page mapping and dimensions; read the outline and font spec when present. Use one matching-size, low-resolution baseline to classify editable slides and freeze those whose text already matches.
2. **Correct in batches.** Use PDF/OCR, outline, and editable-text evidence to repair only affected text. Preserve pre-edit properties, group repeated peers, and use OfficeCLI for scoped edits, read-back, `validate`, and `view issues`. Re-render changed slides or regions rather than the whole deck after each edit.
3. **Pass the static gate.** Once edits stabilize, compare every PDF/PPT page pair at matching dimensions, prioritizing text and checking protected artwork for unintended changes. Resolve visible mismatches, then run the applicable pre-animation [QA checks](references/qa-checklist.md) and font/page verifier. Defer answer-overlay, animation, and final-delivery checks until step 5; structural validation cannot substitute for visual comparison.
4. **Build teaching animation.** Only after the static gate passes, read [animation logic](references/animation-logic.md), plan stable shape-ID order, isolate answer tokens, and animate teaching steps without revealing answers early. If `$ppt-combine` is requested, combine after static acceptance and animate the combined editable deck.
5. **Audit and deliver.** Require zero duplicate animated shapes and plan-order mismatches in `scripts/audit-ppt-animation.ps1`; validate again, complete the deferred QA checks, and compare the fully revealed layout with the verified static deck. Keep a recoverable working copy during processing and deliver only `NAME_动画版.pptx`.

## Hard Completion Gate

The deck is final only after all applicable [QA checks](references/qa-checklist.md) pass. The non-negotiable decisions are:

- Every PDF/PPT page pair matches in visible text, typography, and placement. A structural pass or “no overflow” result never overrides a visible mismatch. Only an explicitly recorded, user-accepted limitation is exempt; disclosure alone is not acceptance.
- Visible teaching text stays editable and protected artwork stays unchanged. Reconstruct semantic image-baked text or disclose it; ignore harmless illustration-only raster differences.
- Font substitutions and text-box geometry remain stable in the delivery application, including single-line headings, peer groups, and text seated inside its backing. The QA checklist holds the object-level checks.
- Questions and prompts precede answers; the actual timing XML has `duplicateAnimatedShapeCount = 0` and `planMismatchCount = 0`. The fully revealed slide preserves the verified static layout.
- If WPS is the known target or the user supplies WPS evidence, inspect WPS edit mode. If this required check is unavailable, label the deck a candidate, not a verified final.

If a required gate fails without an accepted exception, keep correcting or report a candidate/blocked result; do not claim completion.

## Escalation for Difficult Visual Mismatches

Use [references/visual-matching.md](references/visual-matching.md) only when the final reconciliation reveals an unresolved typography/text-backing mismatch, the font spec is missing or unusable, or the user explicitly requests quantitative high-precision text matching.

Do not build a machine-wide font catalog, run per-text candidate searches, create a region manifest, or require `visual-verification.json` during the ordinary fast path. When escalation is necessary, limit it to the affected font role, slide, or region.

## Style Contract

- Preserve converted text and styling that already match the PDF; correction is not redesign.
- Resolve copy from PDF text/high-confidence OCR, `PPT内容大纲.txt`, and existing PPT text. Use the visible PDF to settle clear conflicts; record unresolved ones instead of guessing.
- Preserve hierarchy and object-specific emphasis, color, effects, and backing. Same-role peers should be consistent unless the PDF intentionally differs.
- Judge text placement by rendered glyphs relative to their backing, not text-box coordinates alone. Use a verified peer for repeated rows and paragraphs; [the SOP](references/correction-sop.md) gives the anchor, inset, and height repair order.
- Keep teaching text editable. Reconstruct locally only when a converted text object cannot be repaired in place; leave unrelated artwork untouched.

## Font Handling

Choose from `字体说明.txt` and its fallbacks first, then a compatible face already in the deck; search other installed fonts only if those choices visibly miss the PDF. If the spec describes an image-generation visual target, its named faces are candidates, not exact-match proof. Judge display titles by rendered strokes and width, not by a label such as “行楷感”. A foreign-sounding family name alone is neither proof of incompatibility nor proof of a match.

After a substitution, treat font slots, size, weight, line spacing, margins, box geometry, wrapping, and autofit as one unit. Check the affected peer group and text-to-backing placement in the render. Required single-line titles and labels use fixed sizing (`autoFit=none`) with at least 15% spare width, or 25% for decorative Chinese faces; a supplied PowerPoint/WPS screenshot overrides a conflicting headless render.

At final verification, inventory the fonts actually used by visible text and run the bundled verifier with `--font-file FAMILY=PATH` for each family and `--require-font-files-for-used-fonts`. Confirm each mapping names the actual local face. The script checks slide-local run, paragraph-default, and list-style assignments by Latin/East-Asian/complex-script slot, using a Unicode script heuristic. For theme/master inheritance, identify the effective font, write it into the affected editable text's explicit slots, then rerun; if that cannot be done safely, deliver a labeled candidate. A `.ttc` file-level coverage result is not proof that its selected face contains a glyph; verify that face separately. Zero unresolved mappings and missing glyphs are required before claiming a verified final deck.

Keep an existing sibling `fonts` package. Add only newly adopted, directly used font files that may be redistributed; do not copy the machine's entire font library or assume an embedded font may be repackaged. A sibling file alone does not install a font: embed it or confirm it is installed in the delivery environment, then allow that unembedded family explicitly in the verifier. Detailed execution belongs in [references/correction-sop.md](references/correction-sop.md).

## Outputs

- Preserve the supplied PDF, editable PPT/PPTX, outline, font spec, and any required `fonts` package. Do not create Word or companion-photo outputs unless requested.
- Keep recoverable working copies and verification evidence while processing. If a gate fails, retain what is needed to resume; any shared PPTX must be labeled as a candidate, not `NAME_动画版.pptx` final.
- After all gates pass, leave one produced deck beside the sources: `NAME_动画版.pptx`. Enumerate exact workflow-generated intermediates before removing them; never delete user-supplied files. Keep a compact ledger and verification report only when they document an explicitly accepted limitation or are needed to reproduce the result, or when the user asks to retain them.

## Verification

Use [references/qa-checklist.md](references/qa-checklist.md) for the object-level evidence. Complete applicable static checks before animation and the deferred answer, animation, and delivery checks afterward. The commands below supplement—not replace—the full-page visual comparison.

From the skill directory, set `$jobDir` to the source folder's absolute path. Repeat `--font-file` for each text-used family, using an absolute font-file path. Repeat `--allow-unembedded-font FAMILY` only for families confirmed installed in the delivery environment:

```powershell
$jobDir = 'C:\absolute\path\to\job'
$finalPptx = Join-Path $jobDir 'NAME_动画版.pptx'
python .\scripts\verify_pptx_fonts_pages_size.py `
  --final $finalPptx `
  --expected-slide-count N `
  --report (Join-Path $jobDir 'verification.json') `
  --font-file "FAMILY=C:\absolute\path\to\font.ttf" `
  --require-font-files-for-used-fonts `
  --fail-on-normal-autofit
```

Use `verify_visual_regions.py` and `--visual-report` only for specific unresolved/high-risk regions that were escalated under `visual-matching.md`; they are not mandatory for the ordinary fast path.

Audit the real animation timeline before delivery:

```powershell
& .\scripts\audit-ppt-animation.ps1 `
  -PptPath $finalPptx `
  -PlanPath (Join-Path $jobDir 'TEMP_ANIMATION_PLAN.json')
```
