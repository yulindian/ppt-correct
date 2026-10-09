# PPT Correct QA Checklist

Acceptance results belong in the shared correction ledger. Use [the SOP](correction-sop.md) for methods and commands, [text-review](text-review.md) for coverage/evidence, and [layout-contract](layout-contract.md) for peer/answer audits. These checks describe outcomes; do not duplicate repair instructions or full reports in the ledger.

## Structure

- PDF/PPT counts, order, dimensions and editable/reference mapping are verified. The deck parses/opens, visible teaching text remains editable, and OfficeCLI read-back, save/close, validation/issues pass where supported.
- No full-page image shortcut; reference slides, frozen correct objects and protected artwork remain unchanged except documented SOP §1 exceptions.

## Text and Style

- Copy and intentional line breaks match visible PDF evidence; OCR leftovers are absent, uncertain copy is recorded rather than guessed.
- All reference-visible peers are covered by their PDF-supported contract and expected count. Same-role consistency alone is insufficient. Font, size, weight, color, alignment and complete paragraph metrics match, including intentional exceptions. Only differing properties were changed.
- Mixed-style runs retain local emphasis in both read-back and render. Colors, effects, backings, borders and z-order match. No invented opaque fill hides duplicated/baked text.
- No clipping, overflow, vertical stacking, single-character columns or unintended wrapping remains. Required single-line titles/labels satisfy SOP §3 fixed sizing and spare-width requirements in the delivery application; screenshots override conflicting headless renders.
- Required single-line tags and known size misses pass reference-derived `textConstraints`, including explicit wrap/autofit policy, width/height allowance and verified size range. Explicit newline counts do not establish rendered line count; equally sized peers do not establish correct size. Compare small tags and reported body regions at readable slide/region resolution after save/reopen.
- Glyph bounds match the reference relative to backings and safe content rectangles; repeated icon/text rows align to their first visible line. Changed line counts have stable heights. Box-coordinate equality is insufficient.
- Font substitution passed the coupled typography/geometry checks in SOP §§3–4. Display titles match strokes, width and visual density. Substituted text does not rely on normal autofit.
- Actual font-file mappings cover all text-used families with zero unmapped families, unresolved runs or missing glyphs. Inherited slots are explicit; TTC selected-face coverage is checked. Fonts are embedded or confirmed installed, and newly packaged files are used and redistributable.
- Semantic raster text is reconstructed as editable text or explicitly recorded as an unresolved limitation; decorative lettering remains protected. OCR/image/custom-geometry objects received rendered inspection before repair.

## Static Visual Gate

- Every PDF/PPT page pair was compared at matching dimensions; every actual text object, grouped text and table cell has separate content/size/position/color checks and PDF-supported targets per [text-review](text-review.md). Page review covers missing text too. Frozen pages are included; sampling cannot pass.
- Local emphasis, same-tier groups and text-to-backing placement were inspected at slide resolution. Reusing one loaded page pair for several checks does not omit a dimension or object.
- Each mismatch has corrective rendered verification or explicit user acceptance. Disclosure alone fails; structural/no-overflow results never override a visible mismatch. Protected artwork is checked for unintended change, not harmless raster differences.
- Edits invalidate affected review. Dependent/global changes expand the recheck scope under SOP §6. Cached evidence is not refreshed by simply replacing hashes.
- Static acceptance passed before animation. Unresolved quantitative/font escalation uses [visual-matching](visual-matching.md) only for its stated triggers.

## Animation Phase

- Recoverable verified static state exists. Questions/prompts precede answers without leakage; effects follow teaching order and exclude decorative clutter.
- Each split answer follows SOP §3: bracket pair remains in stem, overlay is glyph-only, correct marks are exactly `✔` and incorrect marks `×`. Every glyph is inspected at slide resolution in its own bracket gap with matching baseline, clearance and containment.
- Every repeated card, step, comparison side, option, signal, or rule is reviewed as a semantic visual unit. Its heading/number, instructional illustration, and explanatory copy appear on the same click unless a documented teaching reason stages them. No sequence reveals all peer headings first and their bodies later merely because they share a row or style.
- All declared peer groups and split answers pass `audit_ppt_layout_contract.py`; actual timing XML has `duplicateAnimatedShapeCount = 0` and `planMismatchCount = 0`.
- Animation plans with `groups` also pass trigger grouping: `groupTriggerMismatchCount = 0`, with one `clickEffect` followed by same-click effects inside each group.
- Fully revealed output matches the verified static layout and PDF. Full contact-sheet review plus slide-resolution inspection covers every split answer/judgment and animation-changed text region.
- Final OfficeCLI animation read-back and OpenXML validation pass. Any unavailable optional slideshow check is disclosed.

## Final Delivery

- Saved animated PPTX, including new answer objects, passes version-2 visualReview coverage, current PDF/PPTX binding and retained evidence hashes. No pending checks or unreviewed changes remain.
- Font/page verification and `validate_ledger.py` pass; applicable gates are `pass` and items are `closed` or `accepted-exception`. Check normal-autofit findings under SOP §10 rather than treating a generic pass as sufficient.
- If WPS is the known target or WPS evidence exists, final WPS edit-mode inspection passes. An unavailable required check means candidate; an unspecified WPS environment is not a new gate.
- Naming, lifecycle, preservation and cleanup follow [SKILL Outputs](../SKILL.md#outputs). Only verified output is `NAME_动画版.pptx`; no unrequested Word/photo deliverables. Retain evidence needed for reproducibility, and do not clean candidate work as final.
