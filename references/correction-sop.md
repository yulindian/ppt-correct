# PPT Correct SOP

## 1. Intake

Resolve the source PDF, editable PPT/PPTX, optional `PPT内容大纲.txt`, and optional `字体说明.txt`. Confirm page count, page order, slide dimensions, and whether the deck is ordinary, combined, or interleaved.

In combined/interleaved decks, identify editable slides and locked image/PDF reference slides from their content and hidden state. Edit only editable slides unless the user explicitly requests otherwise.

Treat illustrations, decorative images, and unrelated artwork as locked. They are not correction targets and illustration-only raster/compression differences are not defects. The only illustration exceptions are an explicit user request, missing/displaced artwork that changes meaning or obstructs text, or semantic image-baked text that must become editable. Reconstruct semantic text locally; leave decorative lettering inside the protected image.

## 2. Low-Resolution Baseline and Triage

Read `PPT内容大纲.txt` and `字体说明.txt` completely. Extract editable text and key style properties, then render the source PDF and editable PPT once at the same low resolution. This baseline is for page registration and triage, not final acceptance.

Classify every editable slide:

- `pass`: text content and appearance already match closely; freeze the slide;
- `text-content`: wrong/missing/duplicated text, punctuation, or line breaks;
- `text-style/layout`: font, size, weight, color, effects, geometry, wrapping, or anchoring differs;
- `structural/reconstruction`: semantic text is raster-baked, a text-bearing backing layer is missing, or the editable text object cannot be repaired safely.

Ignore illustration-only differences during triage. Use the full-page baseline only to detect text-bearing differences and unintended changes outside editable text.

For copy decisions, combine PDF embedded text or high-confidence OCR, the outline, and existing PPT text. Mark an object high-confidence when the sources agree or the PDF is visually unambiguous. Record a conflict instead of silently changing low-confidence copy.

## 3. Fast Source-Driven Correction

Use OfficeCLI to:

1. inspect the deck and confirm available commands/schema;
2. extract editable text, font family, size, bold/weight, color, effects, geometry, wrapping/autofit, and hidden state;
3. map PDF/outline copy to slides and font-spec roles to objects;
4. apply scoped batch edits;
5. read back edited text/properties;
6. save/close to flush resident changes;
7. run `officecli validate` and `view issues`.

Do not use OfficeCLI validation as proof of visual fidelity; it is the structural checkpoint before the final PDF audit.

Build peer groups for repeated same-template objects. Correct a whole peer group consistently instead of performing isolated font/style changes one text box at a time. Do not expand a text correction into illustration or unrelated shape edits.

Before editing, build a compact peer-group style matrix from the reference for every repeated semantic tier: slide labels, card headings, list items, captions, and repeated process-step text. Record the expected font family, visible size, weight/boldness, color, and alignment for every peer. Apply one shared decision to the full peer group unless the PDF visibly proves an intentional exception. `字体说明.txt` proposes roles; the PDF decides the final visible treatment when they disagree.

Also inventory run-level formatting before replacing OCR text. A mixed-style text shape is any shape whose reference uses more than one visible color, weight, size, or font within the same sentence or paragraph. Preserve its emphasis spans explicitly. Whole-shape `text=`, `font=`, `bold=`, or `color=` edits may collapse runs; after such an edit, recreate the intended spans with run-level, `--find`, or character-range formatting before the shape is accepted.

Apply corrections in this order:

1. text/OCR errors, missing characters, punctuation, duplicated text, and broken line breaks;
2. font family from the font spec or its fallback;
3. peer-group weight/bold and size consistency;
4. object-specific color and intentional emphasis;
5. title effects, backing shapes, highlights, and borders only when clearly wrong;
6. text-box margins, anchors, wrapping, autofit/fontScale, clipping, and overflow;
7. local reconstruction only when an editable object cannot be repaired in place.

Before changing an object, record its text, run boundaries, font slots, size, weight, color, margins, anchor, geometry, wrapping, and autofit/fontScale in the compact correction ledger. After a batch edit, re-render only affected slides or text regions. Keep a change when the corrected copy is authoritative and the rendered text region is at least as close to the PDF. If the visual match worsens, restore the recorded pre-edit properties and escalate the object instead of accumulating compensating edits.

After a font substitution, treat family, size, weight, line spacing, margins, text-box geometry, wrapping, and autofit/fontScale as one correction unit. Do not change only the family name and assume the old metrics remain valid.

Treat the cover as a high-salience typography checkpoint. For its main title, do not accept a font merely because it belongs to the requested category (for example, “行楷感”): render the closest practical candidates and compare stroke mass, glyph structure, total line width, and visual density with the PDF. For cover metadata that is a single line in the reference, use fixed sizing with `autoFit=none`, explicit margins, and horizontal safety headroom inside the intended gap. `autoFit=shape` and a box that barely fits in one renderer are not stable single-line solutions; if WPS evidence exists, verify the line in WPS before acceptance.

For text placed on a brush stroke, card, banner, tab, highlight, or other backing element, compare three things after rendering: the text-box rectangle, the visible glyph/ink bounds inside that rectangle, and the backing region. Font ascenders, descenders, and baseline metrics can move the visible text even when `x`, `y`, width, and height are unchanged.

Correct positional drift in this order:

1. match the PDF's vertical anchor (`top`, `middle`, or `bottom`);
2. match top/bottom internal margins or inset;
3. adjust the text-box `y` and height only if the anchor/inset still cannot reproduce the reference;
4. revisit font size only when the rendered glyph size itself is wrong.

Treat a tall single-line text box using top alignment as a high-risk case. Do not accept it until the rendered text is visually seated in the same part of its backing element as in the PDF. Do not use a smaller font as a substitute for fixing its anchor or inset.

For every text-bearing card, bordered panel, banner, step block, or answer area, identify the visible backing bounds before editing. Define a safe content rectangle by subtracting the reference-matched insets, then keep all rendered glyph bounds inside it. A converted text box may be only a few points high or may carry an old offset; its original `y`/height is evidence about the conversion, not authority for final placement. For any tiny/near-zero box or copy-driven line-count change, normalize paragraph spacing, margins, anchor, and autofit, then derive height from intended lines and reference/peer line spacing before changing `y`—even without a repeated peer.

Treat a repeated icon/number-plus-text row as one component even when it is represented by separate shapes. Select one correct row as the template and record: badge/icon center, text left edge, first visible line top/baseline, line spacing, and row band. Apply the same rule to every peer. For multiline rows, align the first visible line to the template; raw box-center alignment can make the first line drift because the text block height changes.

For repeated statements at the same semantic level, copy the complete paragraph contract from the verified peer: font slots, size, weight, color, line spacing, `spaceBefore`, `spaceAfter`, margins, vertical anchor, width policy, and autofit. Recalculate deterministic box height from line count and line spacing. Do not preserve accidental per-shape paragraph metrics from OCR/conversion, and do not repair a line-spacing problem by inserting arbitrary blank paragraphs.

Do not use application-dependent `normAutofit`/`autoFit=normal` as the final remedy for substituted text. Fix the visible font size and text-box geometry, or use an explicit stable scale, and re-render the affected slide.

Preserve backgrounds, illustrations, connector lines, shapes, fills, z-order, and geometry. Only modify a shape that directly carries or backs corrected text, or an illustration exception identified during intake.

### Regression guards for converted/image-based slides

- Do not add a solid or opaque fill to an editable text shape unless the PDF visibly contains the same backing region. A text-box fill is not a valid way to conceal baked text, duplicate OCR, or spacing errors. First correct line spacing, margins, anchor, autofit, and deterministic height; if source lettering is genuinely baked into artwork, use a scoped clean-plate reconstruction and document it.
- Before replacing a whole text shape, inventory its runs and identify all local color/weight changes. Reapply emphasis with run-level `find`/range formatting, read it back, and render it. Whole-shape aggregate color is never sufficient for a mixed-color sentence.
- Treat bracketed answers as anchored components. Preserve the opening and closing bracket in the stem, derive each answer position from that question's rendered bracket span, and center the independent answer shape inside it. Never assign one shared `x` coordinate to several questions unless their bracket spans were proved identical. Verify the fully revealed state at slide resolution.
- Distinguish true text boxes from image-backed or custom-geometry shapes that merely expose OCR/text metadata. If `image=true`, an image source, or custom geometry is present, do not resize or rewrite its text layer until the rendered effect is understood; prefer the separate editable overlay.
- For the common symptom “a paragraph appears twice or gains a pale rectangle,” first suspect conversion metrics (tiny height, inherited line spacing, autofit, margins, or stale OCR) rather than assuming a new background is required.
- Reuse colors from the reference or a verified peer object. Do not guess RGB values for labels, partial emphasis, answer marks, or card text.
- Structural, font, animation, and overflow checks do not replace visual acceptance. Any issue reported by `view issues`, any clipped bracket, or any mismatched high-risk region blocks completion until repaired or disclosed.
- Required single-line text must pass a cross-application width-budget check. Do not retain `autoFit=shape` on titles or labels that must stay on one line. Set deterministic geometry and reserve at least 15% spare width, or 25% for decorative/display Chinese faces. When OfficeCLI and a supplied Office/WPS screenshot disagree, treat the screenshot as the acceptance reference and audit peer titles for the same risk.
- For answer overlays, verify both axes. Compute the answer box from the visible opening/closing bracket span, keep the answer glyph's rendered ink bounds wholly between the brackets, and vertically align its ink center with the stem baseline. Shrink the answer glyph before allowing it to touch either bracket.

After the batch edit, perform run-level read-back for every mixed-style text shape and for every peer group touched by a weight/color change. Acceptance requires both: the emphasized substrings still have their reference styling, and all same-tier peers have the same reference-supported base style. A shape-level aggregate such as `bold=true` is not sufficient evidence for a sentence that contains partial emphasis.

## 4. Fast Font Policy

1. Before editing and at final delivery, inventory text-bearing font assignments. For each changed family, confirm the local face and its visual fit against the PDF; recheck the peer group's geometry after substitution.
2. Confirm each family-to-file mapping is the actual face, then run `verify_pptx_fonts_pages_size.py` with repeated `--font-file FAMILY=PATH` and `--require-font-files-for-used-fonts`. Inspect `unmapped_used_fonts`, `unresolved_runs`, and `missing_glyphs`; a bare pass without mappings does not establish coverage.
3. For theme/master-inherited text, identify the effective font, make its editable text slots explicit, and rerun. If that changes the render or cannot be done safely, disclose a candidate result. For `.ttc` mappings, verify the selected face separately because the script checks the collection's combined cmap.
4. Add a newly adopted font to the sibling `fonts` package only when it is used and redistribution is allowed. Packaging does not install it: embed the face or confirm it is installed in the delivery environment and pass `--allow-unembedded-font FAMILY` for that family.

Use [visual-matching.md](visual-matching.md) only for an unresolved visible font/effect mismatch, unusable font spec, or a user-requested quantitative comparison, scoped to the affected region.

## 5. Structural Checkpoint

Before the final high-resolution full-deck visual render:

- read back all changed text and key style properties;
- scan for known OCR/conversion leftovers;
- confirm editable text still exists;
- check peer-group consistency;
- check wrapping, clipping, overflow, vertical stacking, and single-character columns;
- check visible glyph position relative to brush strokes, cards, tabs, banners, highlights, and other backing elements, especially tall single-line boxes;
- check that every card/panel text block remains inside its backing-derived safe content rectangle;
- check repeated icon/number rows for a common text left edge and matching icon-to-first-line alignment;
- check same-tier multiline peers for identical paragraph spacing, margins, anchor, and line-spacing policy, not just identical font properties;
- flush the file and review OfficeCLI validation/issues.
- confirm frozen `pass` slides and protected illustrations were not modified.

Fix failures here first. This avoids spending time rendering a deck with known structural defects.

## 6. One Final Text-First PDF/PPT Reconciliation

After batch correction and structural checks stabilize:

1. Render the source PDF and final PPT once at identical pixel dimensions.
2. Compare every page pair one-to-one, in order.
3. Check copy, font appearance, hierarchy, color, boldness, effects, geometry, wrapping, clipping, and the rendered glyph position inside associated backing elements.
4. Confirm that protected illustrations and unrelated artwork were not changed; ignore harmless illustration-only renderer, resampling, and compression differences.
5. Record text mismatches by slide and object/region, including unresolved semantic text baked into images.
6. Fix only affected text slides/regions and re-render only those slides/regions.
7. Re-render the whole deck again only after a global change that could affect multiple slides.
8. Disclose any remaining semantic raster-baked text, tool-limited text mismatch, or intentionally preserved limitation.

The reconciliation is an acceptance gate, not an observation step. Any visible text mismatch blocks a “complete/final/passed” claim until it is corrected or explicitly accepted by the user. Structural validation and no-overflow checks cannot override visible PDF text evidence. Illustration-only differences do not block acceptance when the illustration was protected and remains unchanged from the editable source.

When the known delivery application is WPS, or WPS screenshots reveal a difference, inspect the final candidate in WPS edit mode. If that environment cannot be inspected, stop at a clearly labeled candidate build and disclose the missing verification.

Completion cannot be based on sample pages, but ordinary correction does not require repeated full-deck rendering or a region-verification manifest.

## 7. Handoff to PPT Combine

When `$ppt-combine` is explicitly requested, combine only after correction passes verification. Preserve visible PDF pages, hidden editable pages, expected `2N` page count, and final naming rules from the combine skill.

## 8. Automatic Teaching Animation Phase

After the static correction gate passes, continue automatically without requesting user approval. Keep the verified static state as a recoverable internal working copy, then read [animation-logic.md](animation-logic.md).

1. Read the teaching plan, speech script, guide sheet, or exercise material when present.
2. Inventory stable shape IDs, text, coordinates, and existing animations on every slide.
3. Scan question slides for embedded answer tokens, answer letters, judgment marks, and reference-answer panels. Split semantic answers into independent editable shapes when needed; the fully revealed state must remain visually identical to the verified static state.
4. Write a temporary JSON plan containing the complete ordered shape-ID timeline and a reason for every animated slide.
5. Remove conflicting or duplicate existing animations and rebuild the timeline in exact plan order using restrained entrance effects.
6. Run `scripts/audit-ppt-animation.ps1` against the actual slide timing XML. Require `duplicateAnimatedShapeCount = 0` and `planMismatchCount = 0`.
7. Run final OfficeCLI validation, font/page verification, answer-leakage review, and a full contact-sheet comparison. The fully revealed animated deck must preserve the verified static layout.

If the static gate has a blocking correctness failure, do not animate an invalid deck. If a non-blocking limitation is explicitly recorded, animation may continue and the limitation must be disclosed with the final result.

## 9. Final-Only Cleanup

Save only `NAME_动画版.pptx` as the produced deliverable. Keep user-supplied originals and any required sibling `fonts` package. Remove temporary static decks, animation plans, contact sheets, verification JSON, working copies, and superseded intermediates after successful verification. Never remove user-supplied originals.
