---
name: ppt-correct
description: Use when producing a corrected, editable, teaching-animated PPT/PPTX from an image-based PDF reference and editable deck, especially with OCR, typography, layout, question-answer reveal, or classroom sequence requirements.
---

# PPT Correct

Repair the editable deck against the source PDF, pass static visual acceptance, then add verified teaching animation automatically. This is correction, not redesign. Keep teaching text editable and artwork protected; never cover a slide with a full-page PDF image to simulate correction. Produce one final `NAME_动画版.pptx`. Do not invoke `ppt-lesson-writer` or `ppt-photo` unless requested or owned by an external package controller.

## Inputs

Find the source PDF, editable PPT/PPTX, and optional `PPT内容大纲.txt` / `字体说明.txt`. Prefer `NAME.pdf` with `NAME.pdf.pptx`, then `NAME.pptx`; ignore `_PDF原图页_隐藏可编辑页` outputs unless requested. Ask only if pairing is genuinely ambiguous. Identify editable/reference slides by content and hidden state, never assume odd/even mapping. Preserve reference slides.

## Read by Stage

Load each reference once when its stage starts; do not preload every reference or repeat full reports in chat. The SOP owns repair methods, text-review owns coverage/evidence, QA owns acceptance, and the ledger schema owns stored fields.

| Stage | Required reading and action |
|---|---|
| 1. Register / triage | [SOP §§1–2](references/correction-sop.md#1-intake), [text review](references/text-review.md), [ledger schema](references/ledger-schema.md). Confirm mapping/dimensions, read supplied outline/font spec, generate actual-object coverage and a matching-size baseline. Freeze already-correct edits, not their review. |
| 2. Repair | [SOP §§3–5](references/correction-sop.md#3-fast-source-driven-correction). Read the installed `officecli` skill/schema before use. Check complete peer groups; modify only differing properties, preserve run-level emphasis, read back and locally rerender. |
| 3. Static acceptance | [SOP §6](references/correction-sop.md#6-one-final-text-first-pdfppt-reconciliation), [QA static checks](references/qa-checklist.md#static-visual-gate). Review every page and actual text object against the PDF, including unchanged objects. Reuse each page image for separate size/position/color judgments. Repair and recheck every unaccepted mismatch. |
| 4. Teaching animation | [SOP §§7–8](references/correction-sop.md#7-handoff-to-ppt-combine), [animation logic](references/animation-logic.md), [layout contract](references/layout-contract.md) for repeated peers/split answers. Preserve static layout; questions precede answers. Plan complete semantic visual units: a card heading/number, instructional image, and its explanation share one click instead of being separated by row, style, or shape order. Combine only if requested and after static acceptance. |
| 5. Final acceptance | [QA](references/qa-checklist.md), [SOP §§9–10](references/correction-sop.md#9-final-only-cleanup). Review saved animated output, bind evidence to current files, run font/page, layout, animation and ledger validators. |

Use [visual matching](references/visual-matching.md) only for unresolved typography/backing mismatch, an unusable font spec, or requested quantitative matching. Scope it to affected regions; ordinary correction needs no machine-wide font catalog, per-text font search, region manifest, or `visual-verification.json`. Read [workbench integration](references/workbench-integration.md) only with a workbench command, batch ID, product key, or configured entry point.

## Lifecycle and Naming

Use `working` → `candidate` → `verified-final`; use `failed` when processing cannot safely continue. Track all gates, mismatches and exceptions in one `correction-ledger.json`.

- `working`: recoverable internal files.
- `candidate`: usable but unverified; any shared copy is `NAME_动画版_候选.pptx` with affected pages/objects, attempted repairs and the unavailable/failed gate stated.
- `verified-final`: every applicable QA gate passes and no stale/pending object review remains. Only this state uses `NAME_动画版.pptx` or a completion claim.
- `failed`: preserve minimal evidence needed to resume.

A visible mismatch overrides structural/no-overflow passes. Disclosure is not user acceptance. Keep repairing while a meaningful fix remains; do not stop after one comparison or seek acceptance for a routinely fixable defect. A required WPS edit-mode check that is unavailable leaves a candidate. Font coverage, full-page review, answer isolation and actual timing-XML audit are mandatory under their QA conditions.

## Verification

Required single-line labels and reported size misses need reference-derived `textConstraints` in the [layout contract](references/layout-contract.md), read during repair. Equal peer sizes and explicit-newline counts cannot prove correct glyph scale or stable wrapping. Supplied editor screenshots invalidate conflicting acceptance on affected objects and peers.

Use the [compact workflow commands](references/workflow-cli.md) for direct-to-file coverage refresh, dependency-aware reuse, shared targets and fixed auditor orchestration. Reports stay on disk; console output is a summary. This automates bookkeeping, not visual acceptance or PPT editing.

For executable final-deck verifier commands and scoped autofit review, see [SOP §10](references/correction-sop.md#10-verification-commands). These supplement the full-page visual gate.

## Outputs

Preserve all supplied originals and required `fonts`. During work retain recoverable copies; after verification leave one produced deck beside the sources. Retain the compact version-2 ledger and its referenced evidence internally. Enumerate exact workflow-created intermediates before cleanup; never remove supplied files or evidence needed by the ledger. Candidate/failed work retains what is needed to resume. No automatic Word or companion-photo deliverables.
