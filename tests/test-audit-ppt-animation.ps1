$ErrorActionPreference = 'Stop'

$skillRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$auditScript = Join-Path $skillRoot 'scripts\audit-ppt-animation.ps1'
$fixtureScript = Join-Path $skillRoot 'tests\make_animation_fixture.py'
$testDir = Join-Path ([System.IO.Path]::GetTempPath()) ("ppt-animation-test-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testDir | Out-Null
$ppt = Join-Path $testDir 'animation-fixture.pptx'
$goodPlan = Join-Path $testDir 'good-plan.json'
$badPlan = Join-Path $testDir 'bad-plan.json'

try {
    python $fixtureScript $ppt
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate animation fixture.' }

    @{
        slides = @{
            '1' = @{ orderedShapeIds = @(2, 3, 4) }
        }
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $goodPlan -Encoding utf8

    @{
        slides = @{
            '1' = @{ orderedShapeIds = @(2, 4, 3) }
        }
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $badPlan -Encoding utf8

    $good = & $auditScript -PptPath $ppt -PlanPath $goodPlan | ConvertFrom-Json
    if ($good.planMismatchCount -ne 0) {
        throw "Expected the approved order to pass, got $($good.planMismatchCount) mismatch(es)."
    }
    if ($good.duplicateAnimatedShapeCount -ne 0) {
        throw "Expected no duplicate shape animations."
    }
    if ($good.animatedSlideCount -ne 1) {
        throw "Expected animations on one slide, got $($good.animatedSlideCount)."
    }

    $bad = & $auditScript -PptPath $ppt -PlanPath $badPlan | ConvertFrom-Json
    if ($bad.planMismatchCount -ne 1) {
        throw "Expected the incorrect order to produce one mismatch."
    }

    Write-Output 'PASS: animation audit detects correct and incorrect logical order.'
} finally {
    if (Test-Path -LiteralPath $ppt) { & officecli close $ppt | Out-Null }
    Remove-Item -LiteralPath $testDir -Recurse -Force
}
