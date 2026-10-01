# Layout Contract Audit

Use this audit whenever a slide has repeated same-tier text or an embedded answer/judgment mark is split for animation. It converts visual invariants that are easy to skip into a machine-checkable gate.

## Contract shape

Create a temporary JSON file with only the risky objects:

```json
{
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
      "answerGlyph": "√",
      "stemPlaceholder": "（）",
      "requireInsideStem": true
    }
  ]
}
```

`shapeIds` must enumerate every peer visible in the reference, not only the edited objects. Use `expectedCount` to catch an omitted peer. `equal` records properties that the reference shows as shared. Do not require equal color when the reference intentionally uses different semantic colors.

For answer overlays, the stem keeps both brackets and the overlay contains only the semantic glyph (`A`–`D`, `√`, or `×`). The overlay box must remain inside the stem box; widen the stem box to cover the complete bracket span before positioning the glyph. Do not use one copied `x` value for several answers.

Run the audit before accepting the static peer-group gate and again after answer splitting:

```powershell
python .\scripts\audit_ppt_layout_contract.py `
  --pptx $workingPptx `
  --contract $layoutContract `
  --report $layoutReport
```

A nonzero exit or `"passed": false` blocks `verified-final`. The audit supplements slide-resolution visual inspection; it does not determine whether glyphs are optically centered inside the brackets.
