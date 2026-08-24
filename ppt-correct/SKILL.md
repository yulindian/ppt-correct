---
name: ppt-correct
description: Use when correcting an editable PPT/PPTX against an image-based PDF source, including OCR text fixes, layout/font matching, mixed-font cleanup, and final font embedding.
---

# PPT Correct

## Overview

Use the image-based PDF as the source of truth and repair the editable PPT/PPTX copy without redesigning it. The goal is a corrected, editable `.pptx` that visually matches the PDF as closely as practical and embeds fonts so recipients can open it without installing fonts.

## Required Inputs

- Source PDF: page images or scanned/image-based pages.
- Editable PPT/PPTX: converted from the PDF, with editable text and illustration objects.
- User preference: preserve the original design unless they explicitly ask for redesign.

If either the PDF or PPT/PPTX is missing, ask for the missing file before starting file work.

## Correction Principles

- Treat the PDF as the authoritative reference for text, page order, page count, visual style, font appearance, placement, and sizing.
- Preserve the PPT design, page structure, colors, illustrations, and object layout unless a change is needed to match the PDF.
- Correct text by comparing PDF OCR/text recognition against PPT editable text.
- Fix obvious conversion issues: wrong characters, missing text, duplicated text, punctuation errors, broken line breaks, text overflow, inconsistent spacing, and visibly mismatched text size.
- Do not globally replace fonts. Keep existing PPT fonts when they already match the PDF and render correctly.
- When one sentence or paragraph has mixed fonts because conversion/font coverage failed, normalize only that affected text range.
- If a font is missing, incompatible, or cannot be embedded, choose a visually close embeddable replacement and report the substitution.

## Workflow

1. Inspect both files and confirm page mapping: page count, order, aspect ratio, and any missing/extra pages.
2. Render the PDF pages to images and use OCR when the PDF has no extractable text.
3. Extract editable PPT text, font names, font sizes, text boxes, and slide structure.
4. Compare PDF text against PPT text page by page; build a correction list before editing.
5. Apply targeted PPT edits: text fixes first, then font normalization, then size/position adjustments only where needed.
6. Render or inspect the corrected PPT and compare against the PDF reference for visible regressions.
7. Embed fonts in the final PPTX when licensing/format allows. Also produce a font manifest or note listing embedded, substituted, and non-embeddable fonts when relevant.

## Font Handling

Preferred behavior:

- Keep the original font if it visually matches the PDF and can be embedded.
- For Chinese fallback, prefer common embeddable or widely compatible fonts that visually fit the source, such as Microsoft YaHei or Noto/Source Han Sans variants, only when replacement is needed.
- For mixed Chinese/Latin text, avoid creating artificial style differences inside the same sentence unless the PDF clearly does so.
- After font changes, re-check text wrapping and object bounds because Chinese font metrics can shift line breaks.

Embedding caveat:

- Some commercial fonts restrict embedding. When PowerPoint or the PPTX package cannot embed a font legally or technically, replace it with a close embeddable font if visual fidelity remains acceptable; otherwise report the limitation clearly.

## QA Checklist

Before delivery, verify:

- PDF and PPT page counts/order match, or differences are explained.
- Corrected PPT remains editable.
- Text content matches the PDF after OCR review.
- No unintended font mixing remains within a sentence or paragraph.
- Title/body font sizes and line breaks are visually close to the PDF.
- Text boxes do not overflow or clip.
- Illustrations, icons, and background elements were not unnecessarily altered.
- Final PPTX opens successfully.
- Fonts are embedded where possible, and any substitutions or embedding failures are documented.

## Deliverable

Return the corrected `.pptx` path and a concise summary of:

- Text corrections applied.
- Font normalization or substitutions.
- Font embedding result.
- Any residual risks caused by OCR uncertainty, non-embeddable fonts, or unclear PDF source quality.
