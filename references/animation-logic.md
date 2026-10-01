# Teaching Animation Logic

Use this reference only after the static correction gate passes. Animation is part of the same production run, but it must never begin while text or layout remains unstable.

## Core Ordering Rules

| Page structure | Default order |
|---|---|
| Ordinary explanation | title → evidence or statement → explanation → conclusion |
| Spatial cards | left → right, then next row; within a column, top → bottom |
| Before/after comparison | before → after → reflection question |
| Parallel stories or examples | all examples in reading order → shared question or summary |
| Cause and effect | event → effect → principle |
| Advantage/improvement matrix | advantage → keeping method; weakness → improvement measure |
| Task page | prompt → allowed forms or constraints → concrete task |
| Question page | situation or stem → options/prompts → learner thinking time → answer/explanation |
| Diagram or board summary | center concept → branches in reading order → final synthesis |

Visual proximity defines a group. Text boxes that form one caption or card normally share a click using `withPrevious` or `afterPrevious`; separate teaching ideas receive separate clicks.

## Answer Isolation and Leakage

- Scan every exercise shape for embedded answer tokens such as `(A)`, `（A）`, `答案：`, `正确答案`, judgment marks, or appended explanations.
- If an answer is embedded in a question shape, leave the opening and closing brackets in the stem and split only the semantic glyph into a separate editable shape. The overlay text is exactly the answer glyph (`A`–`D`, `√`, or `×`), never the whole token `（A）` or `（√）`. Preserve the original font slots, size, weight, color, spacing, alignment, and fully revealed glyph position.
- Widen the stem box to cover its own bracket pair, then keep the answer overlay inside that stem box. Compute each overlay from its own bracket gap; copied coordinates across questions are invalid unless the rendered bracket spans are identical.
- Treat the stem and choices as one question context. Reveal the answer label, answer body, answer letter, and judgment icon only on a later click.
- For independent questions, complete each question-and-answer pair before revealing the next question.
- Re-render any slide whose answer was split and confirm its fully revealed state still matches the corrected static slide and PDF.
- Declare every split answer in the [layout contract](layout-contract.md) and require the contract audit to pass before delivery.

## Effect Defaults

- Prefer `appear`, `fade`, or directional `wipe` entrances with roughly 300–600 ms duration.
- Use `onClick` for a new teaching step, `withPrevious` for one visual unit, and `afterPrevious` only for a short supporting sequence.
- Keep most slides to 1–5 meaningful teaching steps when the content permits.
- Do not animate full-slide backgrounds, decorative illustrations, or page furniture.

## Non-Obvious Invariants

- Shape-tree order is storage order, not teaching order.
- Z-order controls overlap, not animation order.
- `query animation` is useful for coverage and properties but may list results by shape; inspect raw slide timing XML to verify sequence.
- A question must be visible before its answer. An answer, model response, judgment symbol, or summary must never be triggered with the question unless immediate reveal is explicitly required.
- A timing audit proves order only; it does not prove answer geometry, bracket preservation, or target-application rendering. These require the layout contract and slide-resolution review.
- A bottom banner often functions as a conclusion or prompt and normally appears after the content above it.
- Avoid one click per line when several lines express one idea; avoid one click for multiple ideas that require discussion between them.
- Leave a teacher pause at each discussion point so the next idea stays hidden until the teacher advances.

## Temporary Plan Format

The plan is an internal audit artifact. Keep it when a gate fails so the candidate can be resumed. After verified delivery, remove it unless the plan itself is essential to reproduce the result or an accepted limitation, or the user asks to retain it; record retained evidence in the compact ledger/report under the [output rules](../SKILL.md#outputs).

```json
{
  "slides": {
    "5": {
      "reason": "before image, after image, then reflection",
      "orderedShapeIds": [8, 21, 22, 14, 17]
    },
    "7": {
      "reason": "three parallel stories, then synthesis question",
      "orderedShapeIds": [7, 11, 15, 19, 27]
    }
  }
}
```

Apply the [QA animation checks](qa-checklist.md#animation-phase) for acceptance; the ordering rules above supply the teaching sequence.
