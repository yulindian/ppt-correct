# Complete text review

Read this during baseline triage and again before final delivery. Use the existing
correction ledger; `items` records defects, while `visualReview` records coverage.
An initially correct deck can have zero defects but cannot have zero review coverage.

## Build the checklist from the deck

Prefer the [workflow refresh command](workflow-cli.md) to update the ledger on disk.
Alternatively, run `scripts/validate_ledger.py --inventory-pptx ABSOLUTE_PPTX_PATH --output INVENTORY_JSON` to save a
pending review template. Merge it into `correction-ledger.json` as `visualReview`;
do not replace the ledger or automatically convert pending values to pass.
Set ledger `version` to 2. The inventory follows presentation order and includes
text shapes inside groups and text-bearing table frames. Review all paragraphs,
runs and cells within each listed object. Hidden editable slides are included.

The inventory cannot enumerate image-baked, chart, SmartArt or inherited
master/layout text. The full-page review must also account for these, missing
reference text, and image-only reference slides in combined decks. Do not infer
that an empty object list means the page was visually checked.

## Establish targets before editing

For every listed object record PDF-supported `referenceTargets`, or reference a
shared target as described in [workflow-cli.md](workflow-cli.md#shared-targets):

- `size`: reference glyph height or line width at matched render dimensions,
  chosen font/point size and expected line count; a raster PDF does not establish
  an exact point size. If using a peer, identify the PDF-verified peer.
- `position`: reference text region, visible first-line baseline/edge and backing
  insets. Record page pixel dimensions when using pixels. Textbox coordinates
  alone do not establish rendered glyph position.
- `color`: base text color and every emphasized substring/run or table cell with
  a different treatment. Prefer PDF fill information or interior glyph samples;
  avoid antialiased edge pixels and guessed RGB values.

Record actual style read-back and the visual comparison in these descriptions or
the associated correction item. Nonempty descriptions are checked mechanically;
their visual accuracy still requires inspecting the reference and render.
Never populate targets from the converted PPT alone or use generic 'looks fine'
text. Equal peer sizes/colors can all be wrong. Do not impose a universal minimum
font size or flatten intentional reference differences.

## Three focused visual passes

Compare every page at identical dimensions and readable slide resolution:

Load a page pair once and make the following separate judgments from that same
view. Do not resend the same image for each dimension. Reload only after a change
or when finer detail is needed.

1. Size and hierarchy: compare actual glyph size, stroke weight, wrapping and
   title/body/answer proportions. Answer text occupying only a small fraction of
   a large panel triggers a closer reference comparison, not automatic enlargement.
2. Position: compare first baseline, text edge, icon alignment and backing insets;
   check clipping and overlap. Include apparently unchanged objects.
3. Color: compare base colors and local emphasis at run level, including table
   cells. Shape-level color and peer equality are insufficient.

Also check content and missing/duplicate text. Set `pageChecks` and each object's
`checks` individually for `content`, `size`, `position`, `color` only after the
corresponding comparison. A contact sheet is navigation, not acceptance evidence.
Repair failures and rerender affected pages; do not fill pass from CLI validation.

For reported size/wrapping defects, store concrete observations per affected object: reference and rendered line count, glyph-height/line-width estimate at stated image dimensions, verified size range and geometry correction. Do not mass-fill pass or generate identical generic targets for all objects. Contact sheets cannot establish small-label fit or body-size acceptance; load the affected slide/region at readable resolution. If supplied editor evidence conflicts with a saved review, reopen those checks and their peers; a prior hash-valid render remains insufficient.

## Bind the evidence to the delivered file

Each page records `slide`, the actual PDF `referencePage`, `referenceImage` and
`renderImage`. Both image fields contain an absolute `path` and its `sha256`.
Use actual matched-size reference and fully revealed PPT renders, not placeholder
files. The checker confirms file identity/existence, not image fidelity.

`visualReview.pptxSha256` is the SHA-256 of the saved final PPTX, and
`sourcePdfSha256` is that of the reference PDF. Compute hashes from files, e.g.
`(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()`.
Generate inventory again after answer splitting creates new shapes.

Any saved PPTX change makes the review binding stale. For local changes, recheck
changed pages and affected peers, confirm the remaining slides/dependencies are
unchanged, then update the binding. A global font/theme/master change requires
rechecking all affected pages. Do not just refresh a hash to silence the checker.
Animation must preserve the static layout; final evidence describes its fully
revealed state. Byte-level changes conservatively invalidate the binding even
when an unchanged visual result can be established without rerendering everything.

The three required gates `staticVisual`, `fontPage`, `animationTimeline` must be
`pass`. `deliveryApplication` must be `pass` or explicitly `not-applicable` under
the existing WPS rule. Legacy version-1 ledgers can remain working/candidate but
need this coverage before becoming verified-final.

For a user-accepted visual exception, a check can be
`{"exceptionItem": "existing-ledger-item-id"}` pointing to an
`accepted-exception` item with acceptance evidence. Never mark that mismatch pass.
Keep the ledger and its referenced review images in an internal evidence folder
for reproducibility; they are not additional user-facing PPT deliverables.
