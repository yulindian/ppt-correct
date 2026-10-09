# Correction Ledger Schema

Use one JSON ledger for correction, visual reconciliation, animation exceptions, and delivery state. Keep it while work is active or resumable; after verified delivery retain it only when needed for reproducibility, an accepted exception, or an explicit user request.

```json
{
  "version": 2,
  "project": "NAME",
  "state": "working",
  "sourcePdf": "C:\\absolute\\NAME.pdf",
  "sourcePptx": "C:\\absolute\\NAME.pptx",
  "outputPptx": null,
  "visualReview": null,
  "items": [
    {
      "id": "slide-3-shape-12-title",
      "slide": 3,
      "shapeId": 12,
      "region": "title",
      "category": "text-style/layout",
      "referenceEvidence": "PDF title is single-line and centered on the brush backing",
      "before": {
        "text": "示例标题",
        "font": "Existing Font",
        "sizePt": 36,
        "autofit": "normal"
      },
      "action": "Apply verified title face, fixed size, middle anchor, and stable margins",
      "verification": {
        "method": "slide-resolution PDF/PPT comparison",
        "result": "pass",
        "evidence": "renders/ppt/page-0003.png"
      },
      "status": "closed",
      "exception": null
    }
  ],
  "gates": {
    "staticVisual": "pending",
    "fontPage": "pending",
    "animationTimeline": "pending",
    "deliveryApplication": "not-applicable"
  }
}
```

## Allowed Values

For efficient updates, use [workflow-cli.md](workflow-cli.md). `visualReview` may
also store `renderContext`, page `dependencySha256`/`cacheable`, shared
`styleTargets`, and object `readback`. An object may use `targetRef` plus a matching
`targetSha256` instead of inline `referenceTargets`; per-object checks remain
mandatory. The refresh command preserves checks only for unchanged dependencies
and environment. Do not manually update fingerprints to bypass review.

For `verified-final`, `visualReview` must be populated using [text-review.md](text-review.md). Generate its page/object structure with `python scripts/validate_ledger.py --inventory-pptx ABSOLUTE_PPTX_PATH`; the output is a pending checklist, not a passed report. It contains `pptxSha256`, `sourcePdfSha256`, and `pages`. Each page has `slide`, `referencePage`, two evidence objects (`referenceImage`, `renderImage`, each with absolute `path` and `sha256`), `pageChecks`, and `objects`. Each object has `shapeId`, `checks`, and PDF-supported `referenceTargets` for size/position/color. Both check maps require content/size/position/color. The validator reads the actual output PPTX to enforce exact slide and text-object coverage, including grouped text and tables. Keep referenced evidence files with the ledger.

Version 1 remains readable for unfinished work but cannot become verified-final. Required gates `staticVisual`, `fontPage`, and `animationTimeline` cannot be omitted or marked not-applicable.

- Top-level `state`: `working`, `candidate`, `verified-final`, or `failed`.
- Item `status`: `open`, `closed`, or `accepted-exception`.
- Gate value: `pending`, `pass`, `fail`, `unavailable`, or `not-applicable`.
- `category`: `text-content`, `text-style/layout`, `structural/reconstruction`, `font`, `animation`, or `delivery`.

An accepted exception must replace `exception: null` with an object containing nonempty string fields `limitation`, `attemptedRepairs`, `acceptanceEvidence`, `acceptedBy`, and `acceptedAt`. Every item ID must be nonempty and unique. Disclosure without acceptance keeps the item `open` and the deck at `candidate`.

Before assigning `verified-final`, require every applicable gate to be `pass` and every item to be `closed` or `accepted-exception`. Set `outputPptx` to the exact final path. Candidate output must end in `_动画版_候选.pptx`; verified-final output must end in `_动画版.pptx`.

Validate the ledger before delivery:

```powershell
python .\scripts\validate_ledger.py --ledger (Join-Path $jobDir 'correction-ledger.json')
```
