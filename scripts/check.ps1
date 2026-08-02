[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
    throw "codex was not found on PATH."
}

$catalogJson = & codex -C $projectRoot debug models --bundled
if ($LASTEXITCODE -ne 0) {
    throw "Codex could not load the project or read its bundled model catalog."
}
$catalog = $catalogJson | ConvertFrom-Json
$luna = $catalog.models | Where-Object { $_.slug -eq "gpt-5.6-luna" } | Select-Object -First 1
if (-not $luna) {
    throw "gpt-5.6-luna is missing from the bundled model catalog."
}

$expectedEfforts = @("low", "medium", "high", "xhigh", "max")
foreach ($effort in $expectedEfforts) {
    if ($luna.supported_reasoning_levels.effort -notcontains $effort) {
        throw "gpt-5.6-luna does not advertise reasoning effort '$effort'."
    }
}
if ($luna.additional_speed_tiers -notcontains "fast") {
    throw "gpt-5.6-luna does not advertise Fast mode."
}

Write-Host "Project configuration loaded by Codex."
Write-Host "gpt-5.6-luna supports low, medium, high, xhigh, max, and fast."
Write-Host "No model request was made."
