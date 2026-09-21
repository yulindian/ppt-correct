# PDF-to-PPT Visual Matching

Use this procedure when a corrected text object, title, text-bearing badge, brush swash, or keyword highlight must visually match a PDF reference. It is a text and text-backing escalation path, not a general illustration-matching workflow. Stored PowerPoint properties are inputs; the rendered result is the acceptance target.

## Required pipeline

1. Render the PDF and corrected PPT pages at the same pixel dimensions. Do not compare screenshots captured at different zoom levels.
2. Map every editable text shape from slide coordinates into render pixels. Use its original conversion-layer RGB and geometry as the first crop/color estimate.
3. Classify each mapped item as `text`, `text-backing`, or `highlight`. Associate overlapping behind-text shapes with the text object using overlap, containment, and z-order. A missing text-bearing backing layer is a defect; an illustration-only layer is outside this procedure.
4. Build or reuse the machine-level font catalog. Cluster text whose PDF-visible font appearance is similar; semantic role alone does not define a cluster. For each cluster, reject candidates that lack any character in the union of visible cluster text.
5. Render the exact text with eligible faces over a bounded size range. Rank candidates by rendered ink width, height, density, and normalized contour similarity. Font-spec entries are candidate hints and tie-breakers, not permission to accept a visibly worse render.
6. Apply the selected family, face/weight, size, spacing, line spacing, and geometry. Set Latin/East Asian/complex-script slots together and use `zh-CN` for Chinese runs.
7. Re-render, then verify every corrected/high-risk text region. High-risk regions include cover/page titles, text-bearing badges, question prompts, multi-color text, text-backing swashes, and keyword highlights.
8. Record failed regions in the exception ledger. A failed region must be corrected and re-rendered or explicitly disclosed as tool-limited; it cannot silently pass.

## Standard thresholds

At a 1920×1080 render or an equivalent same-scale render:

| Metric | Default limit |
|---|---:|
| Rendered ink/block width error | ≤ 5% |
| Rendered ink/block height error | ≤ 5% |
| Region centroid offset | ≤ 4 px |
| Ink/fill density error | ≤ 0.12 |
| CIE76 color difference (Delta E) | ≤ 6 |
| Normalized text contour similarity | ≥ 0.55 |
| Required layer area retained | ≥ 70% |

Scale the centroid threshold proportionally for other render sizes. Tighten thresholds for repeated peer groups when the source is crisp. If watercolor texture makes exact color segmentation unstable, record a region-specific tolerance in the manifest; do not weaken the global threshold for the whole deck.

## Font catalog

Build once per machine or after fonts change:

```powershell
python C:\Users\yulin\.codex\skills\ppt-correct\scripts\build_font_catalog.py `
  --font-dir C:\Windows\Fonts `
  --font-dir "$env:LOCALAPPDATA\Microsoft\Windows\Fonts" `
  --output "$env:LOCALAPPDATA\Codex\ppt-correct\font-catalog.json"
```

The catalog records TTC face indices, family/subfamily names, weight class, italic state, coverage size, and CJK presence. Candidate selection must still load the exact face cmap for the exact run; `supports_cjk` is only a search accelerator.

## Text-style matching

Use a tight PDF crop or pass the mapped crop directly with `--reference-bbox`. When a swash or image is behind the text, pass the text RGB so the matcher isolates letters rather than the backing artwork.

```powershell
python C:\Users\yulin\.codex\skills\ppt-correct\scripts\match_text_style.py `
  --reference page-0003.png `
  --reference-bbox 76,88,612,224 `
  --foreground-color D95018 `
  --text "个人离不开集体" `
  --font-catalog "$env:LOCALAPPDATA\Codex\ppt-correct\font-catalog.json" `
  --min-size 28 --max-size 96 `
  --top 12 `
  --output title-match.json
```

Review the top candidates in score order for one representative high-information sample per visual cluster. Prefer a font-spec family when its score is effectively tied; otherwise use the better visual match after the cluster-wide glyph-coverage gate. Reuse the selected family across visually similar text while preserving each object's size, weight, color, spacing, effects, and geometry. Treat `size_px` as a calibration result for the representative render scale, then convert it to the editor's size and confirm representative/high-risk members by re-rendering. Split a cluster only when an actual member is a clear visual outlier.

## Region manifest

`verify_visual_regions.py` consumes a manifest whose paths are relative to the manifest file:

```json
{
  "thresholds": {
    "width_error": 0.05,
    "height_error": 0.05,
    "centroid_distance_px": 4,
    "density_error": 0.12,
    "color_delta": 6,
    "contour_similarity": 0.55,
    "minimum_presence_ratio": 0.70
  },
  "pages": [
    {
      "page": 3,
      "reference_image": "pdf/page-0003.png",
      "candidate_image": "ppt/page-0003.png",
      "regions": [
        {
          "id": "slide3-title",
          "kind": "text",
          "reference_bbox": [76, 88, 612, 224],
          "candidate_bbox": [76, 88, 612, 224],
          "target_rgb": "D95018",
          "color_tolerance": 24
        },
        {
          "id": "slide3-keyword-highlight",
          "kind": "highlight",
          "reference_bbox": [300, 244, 544, 306],
          "candidate_bbox": [300, 244, 544, 306],
          "target_rgb": "E5EDC1",
          "color_tolerance": 24
        }
      ]
    }
  ]
}
```

Run:

```powershell
python C:\Users\yulin\.codex\skills\ppt-correct\scripts\verify_visual_regions.py `
  --manifest visual-regions.json `
  --report visual-verification.json
```

The report contains `passed`, per-region metrics and failures, plus `exception_ledger`. The final deck verifier can enforce it:

```powershell
python C:\Users\yulin\.codex\skills\ppt-correct\scripts\verify_pptx_fonts_pages_size.py `
  --final corrected.pptx `
  --expected-slide-count 29 `
  --report verification.json `
  --visual-report visual-verification.json `
  --require-visual-report
```

## Text-backing and highlight reconstruction

- If the PDF contains a text-bearing badge, brush swash, or highlight but the editable PPT does not, create an editable shape behind the text rather than ignoring it. Do not reconstruct illustration-only artwork through this workflow.
- Sample its dominant RGB, preserve transparency and z-order, and match its rendered bbox. For irregular watercolor swashes, reuse an existing editable peer shape when available; otherwise approximate with an editable freeform or a cropped local decorative asset while keeping the text editable.
- Bind the text and backing shape in the correction ledger with a shared `peer_group`/`visual_group` identifier. Recalculate horizontal and vertical padding after any font or size change.
- Validate the backing layer separately from its text. A good text score cannot compensate for a missing or incorrectly sized highlight.

## Machine-readable ledger fields

For every corrected or high-risk region record: `page`, `shape_id`, `role`, `peer_group`, `visual_group`, `text`, `reference_bbox`, `candidate_bbox`, `reference_rgb`, `font_candidates`, `selected_font_path`, `face_index`, `missing_characters`, `selected_size`, `weight_class`, `spacing`, `line_spacing`, `effects`, `backing_shape_id`, `metrics`, `passed`, `failures`, and `remaining_reason`.
