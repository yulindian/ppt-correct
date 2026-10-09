param(
    [Parameter(Mandatory = $true)]
    [string]$PptPath,

    [string]$PlanPath,

    [switch]$FailOnMismatch
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $PptPath)) {
    throw "PPTX not found: $PptPath"
}
if (-not (Get-Command officecli -ErrorAction SilentlyContinue)) {
    throw 'officecli is required but was not found on PATH.'
}

$animationQuery = & officecli query $PptPath animation --json | ConvertFrom-Json
if (-not $animationQuery.success) {
    throw 'officecli could not query animations.'
}

$animations = @($animationQuery.data.results)
$parentPaths = @($animations | ForEach-Object {
    $_.path -replace '/animation\[\d+\]$', ''
})
$duplicateGroups = @($parentPaths | Group-Object | Where-Object Count -gt 1)
$animatedSlides = @($animations | ForEach-Object {
    if ($_.path -match '^/slide\[(\d+)\]/') { [int]$matches[1] }
} | Sort-Object -Unique)

$mismatches = @()
$checkedOrders = @()
$groupTriggerMismatches = @()

if ($PlanPath) {
    if (-not (Test-Path -LiteralPath $PlanPath)) {
        throw "Animation plan not found: $PlanPath"
    }
    $plan = Get-Content -Raw -LiteralPath $PlanPath | ConvertFrom-Json
    if (-not $plan.slides) {
        throw 'Plan JSON must contain a slides object.'
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $PptPath).Path)
    try {
        function Read-PackageXml([string]$name) {
            $part = $archive.GetEntry($name)
            if (-not $part) { throw "Package part missing: $name" }
            $stream = [System.IO.StreamReader]::new($part.Open())
            try { return [xml]$stream.ReadToEnd() } finally { $stream.Dispose() }
        }
        $presentation = Read-PackageXml 'ppt/presentation.xml'
        $relationships = Read-PackageXml 'ppt/_rels/presentation.xml.rels'
        $slideParts = @()
        foreach ($slideId in $presentation.SelectNodes("//*[local-name()='sldIdLst']/*[local-name()='sldId']")) {
            $relationId = $slideId.GetAttribute('id', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
            $relation = @($relationships.DocumentElement.ChildNodes | Where-Object { $_.Id -eq $relationId })
            if ($relation.Count -ne 1) { throw "Missing slide relationship: $relationId" }
            $partUri = [uri]::new([uri]'http://package/ppt/presentation.xml', [string]$relation[0].Target)
            $slideParts += $partUri.AbsolutePath.TrimStart('/')
        }
        foreach ($slideProperty in $plan.slides.PSObject.Properties) {
            $slideNumber = [int]$slideProperty.Name
            $expected = @($slideProperty.Value.orderedShapeIds | ForEach-Object { [int]$_ })
            if ($slideNumber -lt 1 -or $slideNumber -gt $slideParts.Count) { throw "Plan slide out of range: $slideNumber" }
            $entryName = $slideParts[$slideNumber - 1]
            $entry = $archive.GetEntry($entryName)
            if (-not $entry) { throw "Slide XML not found in PPTX: $entryName" }
            $reader = [System.IO.StreamReader]::new($entry.Open())
            try { $rawXml = $reader.ReadToEnd() } finally { $reader.Dispose() }
            $allTargets = @([regex]::Matches($rawXml, 'spTgt spid="(\d+)"') | ForEach-Object {
                [int]$_.Groups[1].Value
            })
            $effectEntries = @([regex]::Matches(
                $rawXml,
                'nodeType="(clickEffect|withEffect|afterEffect)"[\s\S]*?<p:spTgt spid="(\d+)"'
            ) | ForEach-Object {
                [ordered]@{ nodeType = $_.Groups[1].Value; shapeId = [int]$_.Groups[2].Value }
            })

        # Each PowerPoint entrance effect can reference its target more than once.
        # Collapse only adjacent duplicates; the remaining sequence is the real timeline order.
        $actual = @()
        foreach ($target in $allTargets) {
            if ($actual.Count -eq 0 -or $actual[-1] -ne $target) {
                $actual += $target
            }
        }

            $matches = (($expected -join ',') -eq ($actual -join ','))
            $checkedOrders += [ordered]@{
                slide = $slideNumber
                expected = $expected
                actual = $actual
                matches = $matches
            }
            if (-not $matches) {
                $mismatches += [ordered]@{
                    slide = $slideNumber
                    expected = $expected
                    actual = $actual
                }
            }

            $plannedGroups = @($slideProperty.Value.groups)
            if ($plannedGroups.Count -gt 0) {
                $expectedEffects = @()
                foreach ($group in $plannedGroups) {
                    $members = @($group | ForEach-Object { [int]$_ })
                    for ($memberIndex = 0; $memberIndex -lt $members.Count; $memberIndex++) {
                        $expectedEffects += [ordered]@{
                            shapeId = $members[$memberIndex]
                            nodeType = if ($memberIndex -eq 0) { 'clickEffect' } else { 'withEffect' }
                        }
                    }
                }
                $actualEffects = @()
                foreach ($entry in $effectEntries) {
                    if ($actualEffects.Count -eq 0 -or
                        $actualEffects[-1].shapeId -ne $entry.shapeId -or
                        $actualEffects[-1].nodeType -ne $entry.nodeType) {
                        $actualEffects += $entry
                    }
                }
                $expectedSignature = @($expectedEffects | ForEach-Object { "$($_.shapeId):$($_.nodeType)" }) -join ','
                $actualSignature = @($actualEffects | ForEach-Object { "$($_.shapeId):$($_.nodeType)" }) -join ','
                if ($expectedSignature -ne $actualSignature) {
                    $groupTriggerMismatches += [ordered]@{
                        slide = $slideNumber
                        expected = $expectedEffects
                        actual = $actualEffects
                    }
                }
            }
        }
    } finally {
        $archive.Dispose()
    }
}

$report = [ordered]@{
    file = (Resolve-Path -LiteralPath $PptPath).Path
    animationCount = $animations.Count
    animatedSlideCount = $animatedSlides.Count
    animatedSlides = $animatedSlides
    duplicateAnimatedShapeCount = $duplicateGroups.Count
    duplicateAnimatedShapes = @($duplicateGroups | ForEach-Object {
        [ordered]@{ path = $_.Name; count = $_.Count }
    })
    checkedOrders = $checkedOrders
    planMismatchCount = $mismatches.Count
    planMismatches = $mismatches
    groupTriggerMismatchCount = $groupTriggerMismatches.Count
    groupTriggerMismatches = $groupTriggerMismatches
}

$report | ConvertTo-Json -Depth 10

if ($FailOnMismatch -and (
    $report.duplicateAnimatedShapeCount -gt 0 -or
    $report.planMismatchCount -gt 0 -or
    $report.groupTriggerMismatchCount -gt 0
)) {
    exit 2
}
