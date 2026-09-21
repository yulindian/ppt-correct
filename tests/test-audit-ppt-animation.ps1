$ErrorActionPreference = 'Stop'

$skillRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$auditScript = Join-Path $skillRoot 'scripts\audit-ppt-animation.ps1'
$ppt = 'D:\小红书\小余教学日记\待制作\政治\四年级上\1.1《热爱班集体——生活在班集体里》课件+教案+素材\热爱班集体_生活在班集体里_动画版.pptx'

if (-not (Test-Path -LiteralPath $ppt)) {
    throw "Regression fixture not found: $ppt"
}

$goodPlan = Join-Path $env:TEMP 'ppt-animation-good-plan.json'
$badPlan = Join-Path $env:TEMP 'ppt-animation-bad-plan.json'

@{
    slides = @{
        '1' = @{ orderedShapeIds = @(6, 8, 10, 12) }
        '5' = @{ orderedShapeIds = @(8, 21, 22, 14, 17) }
        '7' = @{ orderedShapeIds = @(7, 11, 15, 19, 27) }
    }
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $goodPlan -Encoding utf8

@{
    slides = @{
        '5' = @{ orderedShapeIds = @(8, 14, 17, 21, 22) }
    }
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $badPlan -Encoding utf8

$good = & $auditScript -PptPath $ppt -PlanPath $goodPlan | ConvertFrom-Json
if ($good.planMismatchCount -ne 0) {
    throw "Expected the approved order to pass, got $($good.planMismatchCount) mismatch(es)."
}
if ($good.duplicateAnimatedShapeCount -ne 0) {
    throw "Expected no duplicate shape animations."
}
if ($good.animatedSlideCount -ne 29) {
    throw "Expected animations on all 29 slides, got $($good.animatedSlideCount)."
}

$bad = & $auditScript -PptPath $ppt -PlanPath $badPlan | ConvertFrom-Json
if ($bad.planMismatchCount -ne 1) {
    throw "Expected the incorrect order to produce one mismatch."
}

Write-Output 'PASS: animation audit detects correct and incorrect logical order.'
