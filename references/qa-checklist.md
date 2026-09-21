# PPT Correct QA Checklist

## Structure

- OfficeCLI was used for inspection, scoped batch edits, read-back, save/close, `validate`, and `view issues` where supported.
- PDF/PPT page counts, order, slide dimensions, and editable-slide mapping are correct or explained.
- A matching-size low-resolution baseline was used to register pages and triage editable slides before correction.
- Slides classified as `pass` were frozen and were not unnecessarily modified.
- The final PPTX opens/parses and editable text remains editable.
- No full-page PDF/image overlay was added as a correction shortcut.
- Image/PDF reference slides remain unchanged in combined/interleaved mode.
- Illustrations, decorative images, and unrelated artwork remained locked unless they met a documented illustration exception.

## Text and Style

- All known OCR/conversion leftovers were scanned after correction.
- Copy decisions were based on converging PDF text/OCR, outline, and PPT evidence; unresolved source conflicts were recorded instead of guessed.
- Text matches the authoritative evidence and the visible PDF.
- `字体说明.txt` roles/fallbacks are applied where present.
- The final font report uses verified family-to-file mappings for every text-used family and has no unmapped family, unresolved slide-local run, or missing glyph. Theme/master-inherited text was given explicit verified slots and re-rendered; `.ttc` face selection was checked separately. A bare pass without mappings is not coverage evidence.
- Newly adopted packaged fonts are directly used and redistributable; any unembedded font was confirmed installed in the delivery environment and explicitly allowed in the verifier.
- Same-template peers use consistent font family, base size, weight/bold, and color unless the reference intentionally differs.
- A peer-group style matrix was checked against the PDF for repeated labels, card headings, list items, captions, and process-step text; no one-off bold/color setting remains inside an otherwise uniform tier.
- Titles, subtitles, body, labels, numbers, captions, and notes preserve their hierarchy.
- Object-specific colors, partial emphasis, outlines, shadows, highlights, backing shapes, borders, and z-order are preserved or corrected from evidence.
- No paragraph received an opaque text-box fill unless the reference visibly contains that backing; fills were not used to hide duplicate/baked text.
- Every mixed-style text shape has run-level read-back confirming that emphasized substrings retain the PDF-supported color/weight and surrounding text retains its base style; OCR replacement did not flatten the sentence into one run/style.
- No clipping, overflow, vertical stacking, single-character columns, or unintended wrapping remains.
- High-salience cover/display titles match the PDF's stroke mass, glyph structure, width, and visual density; a merely category-compatible font was not accepted when its rendered form visibly differed.
- Every cover line that is single-line in the reference uses deterministic geometry (`autoFit=none`, explicit margins, and horizontal safety headroom) and remains single-line in the known delivery application; `autoFit=shape` was not used as the final fix.
- Every required single-line heading/card title/scene title—not only the cover—uses deterministic geometry and 15%–25% horizontal safety headroom; supplied PowerPoint/WPS screenshots override a conflicting headless render.
- Longer peer items wrap at the common size instead of shrinking independently where practical.
- Substituted text does not rely on application-dependent `normAutofit`/`autoFit=normal`.
- Font substitution was followed by joint verification of font slots, visible size, weight, line spacing, margins, text-box geometry, wrapping, and scaling.
- For every title, label, question, or emphasized line associated with a brush stroke, card, tab, banner, or highlight, the rendered glyph bounds occupy the same relative area of the backing element as in the PDF; matching text-box coordinates alone is not accepted.
- Tall single-line text boxes were checked for incorrect top anchoring. Vertical anchor and internal margins were corrected before changing box coordinates or font size.
- Text inside cards, borders, step blocks, and answer panels stays inside a backing-derived safe content rectangle; no placement decision relies only on the converter's original text-box geometry.
- Repeated icon/number-plus-text rows use a common text left edge and the same icon-to-first-visible-line alignment rule, including multiline rows.
- Same-tier multiline peers share font, size, line spacing, paragraph spacing, margins, vertical anchor, width policy, and autofit; deterministic heights were recalculated after line-count changes.
- Changed text regions were re-rendered incrementally; changes that worsened the visual match were restored or escalated.
- Semantic image-baked text was reconstructed as editable text or disclosed; decorative lettering remained in the protected illustration.
- Image-backed/custom-geometry shapes with OCR metadata were identified before editing and were not handled as ordinary text boxes.

## Final Visual Audit

- The full source PDF and final PPT were rendered once at matching dimensions after batch correction stabilized.
- Every page pair was compared one-to-one and in order; acceptance is not based on samples.
- Text content, font appearance, size, weight, color, effects, geometry, wrapping, clipping, and visible text-to-backing placement were checked.
- Protected illustrations were checked only for unintended modification; harmless illustration-only renderer, resampling, and compression differences were not treated as correction failures.
- The visual audit explicitly compared local emphasis inside sentences and same-tier peers as groups; it did not rely only on whole-textbox aggregate properties.
- Every bracketed answer and judgment mark was inspected in the fully revealed state and is centered inside its own opening/closing brackets.
- Bracketed answers were checked on both axes: glyph ink stays fully between the brackets and its vertical center follows the question baseline.
- Paragraph-on-illustration, mixed-color title, bracketed-answer, and color-coded-label regions received slide-resolution review rather than contact-sheet-only review.
- Exceptions were corrected with slide/region-local rerenders where possible.
- A second full-deck render was used only when a global change could affect multiple slides.
- Any remaining text or semantic image-baked-text mismatch is recorded with its reason and explicitly accepted by the user; otherwise the deck is a candidate.
- Visible text mismatches take precedence over structural validation or no-overflow results.
- When WPS is the known target or WPS evidence exists, the final candidate was checked in WPS edit mode; if that required WPS check was unavailable, the result is labeled as a candidate rather than complete. WPS does not block acceptance when it is not the requested or known delivery environment.
- `visual-matching.md`, font candidate ranking, and `verify_visual_regions.py` were used only for explicitly escalated unresolved/high-risk regions.

## Final Delivery

- `verify_pptx_fonts_pages_size.py` passes; unresolved failures make the deck a candidate even when disclosed.
- Directly used fonts are embedded or confirmed installed in the delivery environment.
- A verified delivery contains one produced `NAME_动画版.pptx` beside preserved originals and any required `fonts` package; an unverified shared PPTX is labeled a candidate.
- No automatic `ppt-lesson-writer` Word files or `ppt-photo` type images were created.
- Static correction passed its internal acceptance gate before animation was added; no user confirmation was requested between phases.
- After successful verification, exact workflow-generated temporary files are enumerated and cleaned; evidence for accepted limitations or reproducibility is retained. Candidate work is not cleaned as though final.

## Animation Phase

- Animation began automatically after the internal static correction gate passed.
- A recoverable internal static working copy was preserved during processing but was not retained as a second deliverable.
- Question/answer slides reveal the answer only after the question is visible.
- Embedded answer tokens were split into independently animated editable shapes where required; answer letters and judgment icons do not leak on entry.
- Effects are restrained, ordered by teaching logic, and do not animate backgrounds or decorative clutter.
- The final animation state still matches the internally verified static slide and source PDF.
- `duplicateAnimatedShapeCount = 0` and `planMismatchCount = 0` in the real timing-XML audit.
- OfficeCLI animation read-back and OpenXML validation pass. Disclose an unavailable optional slideshow check; WPS edit-mode remains required when WPS is the known delivery target.
