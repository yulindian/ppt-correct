param(
    [Parameter(Mandatory = $true)]
    [string]$PptPath,

    [string]$PlanPath
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
        foreach ($slideProperty in $plan.slides.PSObject.Properties) {
            $slideNumber = [int]$slideProperty.Name
            $expected = @($slideProperty.Value.orderedShapeIds | ForEach-Object { [int]$_ })
            $entryName = "ppt/slides/slide$slideNumber.xml"
            $entry = $archive.GetEntry($entryName)
            if (-not $entry) { throw "Slide XML not found in PPTX: $entryName" }
            $reader = [System.IO.StreamReader]::new($entry.Open())
            try { $rawXml = $reader.ReadToEnd() } finally { $reader.Dispose() }
            $allTargets = @([regex]::Matches($rawXml, 'spTgt spid="(\d+)"') | ForEach-Object {
                [int]$_.Groups[1].Value
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
        }
    } finally {
        $archive.Dispose()
    }
}

[ordered]@{
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
} | ConvertTo-Json -Depth 10
