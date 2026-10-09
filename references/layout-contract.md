# Layout Contract Audit

Use this audit whenever a slide has required single-line labels, repeated same-tier text, or an embedded answer/judgment mark split for animation. It converts visual invariants that are easy to skip into a machine-checkable gate.

## Contract shape

Create a temporary JSON file with only the risky objects:

```json
{
  "textConstraints": [
    {
      "slide": 16,
      "shapeId": 10,
      "referenceEvidence": "PDF tab has two horizontal characters; verified at matched resolution.",
      "singleLine": true,
      "sizePtRange": [25, 27],
      "minWidth": "65pt",
      "minHeight": "30pt"
    }
  ],
  "peerGroups": [
    {
      "slide": 7,
      "name": "five scene captions",
      "shapeIds": [17, 19, 21, 23, 25],
      "expectedCount": 5,
      "equal": ["font", "size", "bold", "color", "align", "autoFit"],
      "maxLines": 2
    }
  ],
  "answerOverlays": [
    {
      "slide": 22,
      "stemShapeId": 19,
      "answerShapeId": 9201,
      "answerGlyph": "✔",
      "stemPlaceholder": "（）",
      "requireInsideStem": true
    }
  ]
}
```

`shapeIds` must enumerate every peer visible in the reference, not only the edited objects. Use `expectedCount` to catch an omitted peer. `equal` records properties that the reference shows as shared. Do not require equal color when the reference intentionally uses different semantic colors.

## Stable wrapping and reference size

The numbers above illustrate the schema, not universal typography settings. Derive each target from the PDF and a verified rendered candidate. Declare every required single-line tag/title and each known size mismatch under `textConstraints`; include all affected peers. `singleLine` requires explicit `wrap=false`, `autoFit=none` and `minWidth`. Set `minWidth` to measured glyph width plus SOP §3 spare width **and both horizontal insets**; `minHeight` includes glyph/line height and vertical insets. Check geometry against the intended backing, not just the slide boundary. Disabling wrap prevents folding but cannot prevent horizontal overflow.

`sizePtRange` checks a PDF-verified point-size range, so equally undersized peers cannot pass merely by matching one another. Mixed-size text needs run-level review; shape size is insufficient. Required properties absent from read-back are unresolved, not passing defaults.

`maxLines` counts explicit breaks only. Neither it nor `singleLine` measures actual rendered line count. For multi-line blocks record reference line count and actual rendered line count in object review; inspect first/last baselines, trailing solitary characters and backing clearance in the target application. Use intentional paragraph/soft breaks when the reference requires reproducible line boundaries; do not shrink text to hide a width/spacing error.

For answer overlays, the stem keeps both brackets and the overlay contains only the semantic glyph (`A`–`D`, `✔`, or `×`). Normalize legacy `√` and `✓` marks to `✔`. The overlay box must remain inside the stem box; widen the stem box to cover the complete bracket span before positioning the glyph. Do not use one copied `x` value for several answers.

Run the audit before accepting the static peer-group gate and again after answer splitting:

```powershell
python .\scripts\audit_ppt_layout_contract.py `
  --pptx $workingPptx `
  --contract $layoutContract `
  --report $layoutReport
```

A nonzero exit or `"passed": false` blocks `verified-final`. The audit supplements slide-resolution visual inspection; it does not determine whether glyphs are optically centered inside the brackets.
