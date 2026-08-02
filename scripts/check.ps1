[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

function Invoke-CodexCaptured {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $captured = @(& codex @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    $lines = @($captured | ForEach-Object { $_.ToString() })
    return [PSCustomObject]@{
        ExitCode = $exitCode
        Lines = $lines
    }
}

if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
    throw "codex was not found on PATH."
}

$catalogResult = Invoke-CodexCaptured -Arguments @("-C", $projectRoot, "debug", "models", "--bundled")
if ($catalogResult.ExitCode -ne 0) {
    throw "Codex could not load the project or read its bundled model catalog."
}
$catalogJson = $catalogResult.Lines |
    Where-Object { $_.TrimStart().StartsWith("{") } |
    Select-Object -Last 1
if ([string]::IsNullOrWhiteSpace($catalogJson)) {
    throw "Codex did not return a valid bundled model catalog."
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

& (Join-Path $PSScriptRoot "luna-agent.ps1") doctor --skip-login
if ($LASTEXITCODE -ne 0) {
    throw "The isolated Luna runner failed its local capability check."
}

Write-Host "The isolated runner loaded successfully."
Write-Host "No model request was made."
