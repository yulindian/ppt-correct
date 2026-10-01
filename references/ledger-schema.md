# Correction Ledger Schema

Use one JSON ledger for correction, visual reconciliation, animation exceptions, and delivery state. Keep it while work is active or resumable; after verified delivery retain it only when needed for reproducibility, an accepted exception, or an explicit user request.

```json
{
  "version": 1,
  "project": "NAME",
  "state": "working",
  "sourcePdf": "C:\\absolute\\NAME.pdf",
  "sourcePptx": "C:\\absolute\\NAME.pptx",
  "outputPptx": null,
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

- Top-level `state`: `working`, `candidate`, `verified-final`, or `failed`.
- Item `status`: `open`, `closed`, or `accepted-exception`.
- Gate value: `pending`, `pass`, `fail`, `unavailable`, or `not-applicable`.
- `category`: `text-content`, `text-style/layout`, `structural/reconstruction`, `font`, `animation`, or `delivery`.

An accepted exception must replace `exception: null` with the limitation, attempted repairs, acceptance evidence, and accepting user/date. Disclosure without acceptance keeps the item `open` and the deck at `candidate`.

Before assigning `verified-final`, require every applicable gate to be `pass` and every item to be `closed` or `accepted-exception`. Set `outputPptx` to the exact final path. Candidate output must end in `_动画版_候选.pptx`; verified-final output must end in `_动画版.pptx`.

Validate the ledger before delivery:

```powershell
python .\scripts\validate_ledger.py --ledger (Join-Path $jobDir 'correction-ledger.json')
```
