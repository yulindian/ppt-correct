# PDF-to-PPT Visual Matching

Use this procedure when a corrected text object, title, text-bearing badge, brush swash, or keyword highlight must visually match a PDF reference. It is a text and text-backing escalation path, not a general illustration-matching workflow. Stored PowerPoint properties are inputs; the rendered result is the acceptance target.

## Scoped pipeline

1. Render only the affected PDF/PPT pages at the same pixel dimensions. Map the mismatched text and associated backing/highlight into render pixels; use conversion-layer geometry and RGB as crop/color estimates, not final authority.
2. Identify whether the mismatch is in text appearance, text-bearing backing/highlight, or both. Associate a backing with its text by overlap, containment, and z-order. Leave illustration-only layers outside this procedure.
3. For a font mismatch, try the font spec/fallback and faces already in the deck first. Compare the exact text's glyph coverage and rendered ink width, height, density, and contour. If those candidates still miss, use the [font catalog and matcher](#font-catalog) for the affected visual group; reject faces missing any of its characters. Apply family, face/weight, size, spacing, line spacing, and geometry together, setting Latin/East Asian/complex-script slots and `zh-CN` for Chinese runs.
4. For a backing/highlight mismatch with correct text, repair or reconstruct only the affected layer's fill/texture, transparency, rendered bounds, and z-order; do not run font search. Reuse an editable peer backing where practical.
5. Re-render changed regions and affected peers at slide resolution, then complete the ordinary full-page visual acceptance gate. Record any remaining mismatch and obtain explicit user acceptance before treating it as an exception; disclosure alone is not acceptance.

## Optional quantitative thresholds

When `verify_visual_regions.py` is useful for a hard-to-judge region, its defaults at a 1920×1080 render or equivalent scale are:

| Metric | Default limit |
|---|---:|
| Rendered ink/block width error | ≤ 5% |
| Rendered ink/block height error | ≤ 5% |
| Region centroid offset | ≤ 4 px |
| Ink/fill density error | ≤ 0.12 |
| CIE76 color difference (Delta E) | ≤ 6 |
| Normalized text contour similarity | ≥ 0.55 |
| Required layer area retained | ≥ 70% |

Scale the centroid threshold proportionally for other render sizes. Tighten thresholds for repeated peer groups when the source is crisp. If watercolor texture makes color segmentation unstable, use a region-specific tolerance rather than weakening every region.

## Font catalog

Use the catalog only when the affected font cannot be matched from the spec, fallbacks, or deck faces and quantitative candidate ranking is needed. Run these examples from the cloned `ppt-correct` skill directory; replace sample paths and values with the job's values:

```powershell
$skillDir = (Get-Location).Path
$jobDir = 'C:\absolute\path\to\job'
$fontCatalog = Join-Path $env:LOCALAPPDATA 'Codex\ppt-correct\font-catalog.json'
```

Build or refresh the catalog only when font search is needed:

```powershell
python (Join-Path $skillDir 'scripts\build_font_catalog.py') `
  --font-dir (Join-Path $env:WINDIR 'Fonts') `
  --font-dir "$env:LOCALAPPDATA\Microsoft\Windows\Fonts" `
  --output $fontCatalog
```

The catalog records TTC face indices, family/subfamily names, weight class, italic state, coverage size, and CJK presence. Candidate selection must still load the exact face cmap for the exact run; `supports_cjk` is only a search accelerator.

## Text-style matching

Use a tight PDF crop or pass the mapped crop directly with `--reference-bbox`. When a swash or image is behind the text, pass the text RGB so the matcher isolates letters rather than the backing artwork.

```powershell
python (Join-Path $skillDir 'scripts\match_text_style.py') `
  --reference (Join-Path $jobDir 'pdf\page-0003.png') `
  --reference-bbox 76,88,612,224 `
  --foreground-color D95018 `
  --text "个人离不开集体" `
  --font-catalog $fontCatalog `
  --min-size 28 --max-size 96 `
  --top 12 `
  --output (Join-Path $jobDir 'title-match.json')
```

Review the top candidates in score order for one representative high-information sample per visual cluster. Prefer a font-spec family when its score is effectively tied; otherwise use the better visual match after the cluster-wide glyph-coverage gate. Reuse the selected family across visually similar text while preserving each object's size, weight, color, spacing, effects, and geometry. Treat `size_px` as a calibration result for the representative render scale, then convert it to the editor's size and confirm representative/high-risk members by re-rendering. Split a cluster only when an actual member is a clear visual outlier.

## Optional region manifest

For quantitative verification of an unresolved/high-risk region, `verify_visual_regions.py` consumes a manifest whose paths are relative to the manifest file. Omit thresholds to use the script defaults; scope entries to affected regions:

```json
{
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
        }
      ]
    }
  ]
}
```

Run:

```powershell
python (Join-Path $skillDir 'scripts\verify_visual_regions.py') `
  --manifest (Join-Path $jobDir 'visual-regions.json') `
  --report (Join-Path $jobDir 'visual-verification.json')
```

The report contains `passed`, per-region metrics and failures, plus `exception_ledger`. When this optional quantitative check is part of acceptance, use the complete final-deck verifier command in [SKILL.md](../SKILL.md#verification) and add `--visual-report (Join-Path $jobDir 'visual-verification.json') --require-visual-report`; keep its font checks and scoped autofit review.

## Text-backing and highlight reconstruction

- If the PDF contains a text-bearing badge, brush swash, or highlight but the editable PPT does not, create an editable shape behind the text rather than ignoring it. Do not reconstruct illustration-only artwork through this workflow.
- Sample its dominant RGB, preserve transparency and z-order, and match its rendered bbox. For irregular watercolor swashes, reuse an existing editable peer shape when available; otherwise approximate with an editable freeform or a cropped local decorative asset while keeping the text editable.
- Bind the text and backing shape in the correction ledger with a shared `peer_group`/`visual_group` identifier. Recalculate horizontal and vertical padding after any font or size change.
- Validate the backing layer separately from its text. A good text score cannot compensate for a missing or incorrectly sized highlight.

## Exception evidence

For a remaining mismatch, record its page/shape or region, the reference evidence, attempted correction, local verification result, and reason it remains. Keep machine metrics in the tool report when quantitative verification was used; retain other fields only when needed to reproduce the decision.
