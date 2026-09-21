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

Use [the SOP](correction-sop.md) for repair order; these are the observable acceptance checks.

- Corrected copy matches PDF text/high-confidence OCR, outline, and visible PDF evidence; OCR leftovers are absent and unresolved conflicts are recorded rather than guessed.
- `字体说明.txt` roles/fallbacks are applied where present. Every text-used family has a verified face/file mapping; the font report has no unmapped family, unresolved run, or missing glyph. Theme/master-inherited slots are explicit and re-rendered, and `.ttc` face coverage is checked separately.
- Newly packaged fonts are directly used and redistributable; unembedded fonts are confirmed installed in the delivery environment and explicitly allowed in the verifier.
- Same-template peers match the PDF-supported family, size, weight, color, alignment, and hierarchy unless the PDF shows an intentional exception. Same-tier multiline peers also share line/paragraph spacing, margins, anchor, width policy, and autofit; changed line counts have stable box heights.
- Object-specific colors, effects, highlights, backing shapes, borders, and z-order match the PDF. No opaque text-box fill conceals duplicate or baked text unless the reference visibly contains that backing.
- Each mixed-style shape has run-level read-back and a matching render: emphasized substrings retain their PDF-supported style and surrounding text retains its base style.
- No clipping, overflow, vertical stacking, single-character columns, or unintended wrapping remains. Longer peer items wrap at the common size rather than shrinking independently where practical.
- Cover/display titles match the PDF's stroke mass, glyph structure, width, and visual density, not merely its font category.
- Every required single-line title or label stays on one line in the known delivery application with `autoFit=none`, explicit margins, and at least 15% spare width (25% for decorative Chinese faces); supplied PowerPoint/WPS screenshots override conflicting headless renders.
- Substituted text has jointly verified font slots, visible size, weight, spacing, margins, geometry, wrapping, and scaling; it does not rely on `normAutofit`/`autoFit=normal`.
- Rendered glyphs sit in the PDF-matched position within brush strokes, cards, tabs, banners, and highlights, including tall single-line boxes; card/panel text stays inside its backing-derived safe content rectangle. Matching box coordinates alone is insufficient.
- Repeated icon/number-plus-text rows share the reference-supported text edge and icon-to-first-visible-line alignment, including multiline rows.
- Semantic image-baked text is editable or disclosed; decorative lettering stays protected. Image-backed/custom-geometry shapes with OCR metadata were not treated as ordinary text boxes.

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
