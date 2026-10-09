# Compact workflow commands

Use `scripts/ppt_correct.py` to refresh coverage and run fixed auditors. It does
not repair PPT content, render images, approve visual checks, run OfficeCLI
structural validation, or inspect WPS for you. Continue the SOP for those steps.
All commands below run from the skill directory; use absolute job/config paths.

## Refresh after saving a change

```powershell
python -X utf8 .\scripts\ppt_correct.py refresh `
  --ledger C:\job\correction-ledger.json `
  --pptx C:\job\working.pptx `
  --render-context 'WPS-version; renderer-settings; font-environment-revision'
```

Create the ordinary ledger first, with `sourcePdf`, `items`, and `gates`.
Refresh writes inventory directly into it, retains one `.previous.json` backup,
and returns only pages needing review plus a next action. Run at baseline and
after saved modifications, including answer splitting. It never sets visual
checks to pass. Finish actual review before running final checks.

Reuse requires unchanged PDF, renderer context and each page's package dependency
fingerprint. Dependencies include related layouts, masters, themes, media, charts
and embedded fonts. Cycles are handled; external relationships conservatively
disable reuse. Broad master dependencies may recheck more pages than necessary.
Legacy review records without fingerprints are reviewed once before reuse.

The render-context string is an explicit environment identity, not automatic
font discovery. Record renderer/version, settings and font environment revision;
change it whenever installed fonts, renderer settings or application changes.
If stability is unknown, use a new identity and recheck all pages. A source PDF
change also invalidates all pages. Page reorder/change invalidates affected slots.

## Shared targets

Store a PDF-verified size/position/color target once under
`visualReview.styleTargets.GROUP_ID`. Each member may replace its inline
`referenceTargets` with `targetRef: GROUP_ID` and `targetSha256` from
`validate_ledger.target_digest(target)`. Target descriptions must be meaningful
for every member (e.g. first-line position relative to its own panel, not one
shared absolute y coordinate). Split groups for reference-intended differences.

Binding to a shared target saves repeated descriptions, not per-object review.
Changing a target invalidates its members until they are rechecked; never merely
refresh their target hashes. Inventory records explicit geometry, paragraph and
run formatting in `readback`; inherited effective values still need OfficeCLI
and rendered comparison. Compare complete peers and apply only differing
properties through scoped OfficeCLI edits; do not overwrite an entire group.

## Run fixed checks

Use a JSON config with `expectedSlideCount`, `fontFiles` (family-to-absolute-path
map), `allowUnembeddedFonts` (only confirmed installed families), and
`layoutApplicable` (boolean). If true, supply absolute `layoutContract`; final
phase also requires absolute `animationPlan`. Omitted applicability is an error.

```powershell
python -X utf8 .\scripts\ppt_correct.py check `
  --ledger C:\job\correction-ledger.json `
  --config C:\job\check-config.json --phase static `
  --report-dir C:\job\evidence
```

Use `--phase final` after animation. The wrapper runs visual coverage validation,
font/page verification, applicable layout auditing, and final animation auditing;
it updates machine gates but keeps lifecycle `working`. It logs complete tool
output and returns concise status. Resolve failures rather than editing gates to
pass. It does not replace the scoped autofit, glyph-face, WPS or visual checks in
the SOP. Set the final lifecycle/path only after all conditions pass, then run
`validate_ledger.py --ledger ... --output ...` for the final report.

Individual auditors remain available. Font/page, layout, visual-region and font
matcher scripts default to a compact stdout summary; use `--verbose` only for
diagnosis. Complete JSON remains at `--report`/`--output`. For standalone inventory,
use `validate_ledger.py --inventory-pptx ... --output inventory.json` to avoid
printing every object. PowerShell animation JSON should be redirected to a file
or captured by the wrapper, then summarized.
