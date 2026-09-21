$ErrorActionPreference = 'Stop'

$skillRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$skillPath = Join-Path $skillRoot 'SKILL.md'
$qaPath = Join-Path $skillRoot 'references\qa-checklist.md'
$animationReference = Join-Path $skillRoot 'references\animation-logic.md'
$animationAudit = Join-Path $skillRoot 'scripts\audit-ppt-animation.ps1'

$skill = Get-Content -Raw -LiteralPath $skillPath
$qa = Get-Content -Raw -LiteralPath $qaPath

if ($skill -notmatch 'NAME_动画版\.pptx') {
    throw 'Unified ppt-correct must declare NAME_动画版.pptx as its final deliverable.'
}
if ($skill -match 'explicitly confirms|用户明确确认|Save the corrected deck[^\r\n]+NAME_可编辑版\.pptx|Deliver the verified static[^\r\n]+NAME_可编辑版\.pptx') {
    throw 'Unified ppt-correct must not pause for static approval or deliver a static editable PPTX.'
}
if ($skill -notmatch 'audit-ppt-animation\.ps1') {
    throw 'Unified ppt-correct must require real animation timeline auditing.'
}
if (-not (Test-Path -LiteralPath $animationReference)) {
    throw 'Animation logic reference was not merged into ppt-correct.'
}
if (-not (Test-Path -LiteralPath $animationAudit)) {
    throw 'Animation audit script was not merged into ppt-correct.'
}
if ($qa -notmatch 'duplicateAnimatedShapeCount' -or $qa -notmatch 'planMismatchCount') {
    throw 'QA checklist must require zero duplicate animations and zero timeline mismatches.'
}

Write-Output 'Unified ppt-correct contract passed.'
