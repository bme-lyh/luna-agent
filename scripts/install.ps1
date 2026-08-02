[CmdletBinding()]
param(
    [string]$CodexHomePath = "",
    [string]$SkillsRootPath = "",
    [switch]$Force,
    [switch]$SkipCapabilityCheck
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($CodexHomePath)) {
    if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
        $CodexHomePath = $env:CODEX_HOME
    }
    else {
        $CodexHomePath = Join-Path $env:USERPROFILE ".codex"
    }
}
if ([string]::IsNullOrWhiteSpace($SkillsRootPath)) {
    $SkillsRootPath = Join-Path $env:USERPROFILE ".agents\skills"
}

if (-not $SkipCapabilityCheck) {
    if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
        throw "codex was not found on PATH. Install or update Codex before installing Luna Agent."
    }
    $catalogJson = & codex debug models --bundled
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read the bundled Codex model catalog."
    }
    $catalog = $catalogJson | ConvertFrom-Json
    $luna = $catalog.models | Where-Object { $_.slug -eq "gpt-5.6-luna" } | Select-Object -First 1
    if (-not $luna) {
        throw "This Codex installation does not expose gpt-5.6-luna. Update Codex or check workspace model availability."
    }
    if ($luna.supported_reasoning_levels.effort -notcontains "max") {
        throw "The installed Luna model catalog does not support reasoning effort max."
    }
    if ($luna.additional_speed_tiers -notcontains "fast") {
        throw "The installed Luna model catalog does not support Fast mode."
    }
}

function Install-ManagedFile {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $destinationDirectory = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null

    if (Test-Path -LiteralPath $Destination) {
        $sourceHash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
        $destinationHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
        if ($sourceHash -eq $destinationHash) {
            Write-Host "Already current: $Destination"
            return
        }
        if (-not $Force) {
            throw "Refusing to overwrite a different file: $Destination. Re-run with -Force after reviewing it."
        }
    }

    Copy-Item -LiteralPath $Source -Destination $Destination -Force:$Force
    Write-Host "Installed: $Destination"
}

$agentFiles = @(
    "luna-worker.toml",
    "luna-low.toml",
    "luna-medium.toml",
    "luna-high.toml",
    "luna-xhigh.toml"
)

Install-ManagedFile `
    -Source (Join-Path $projectRoot ".codex\config.toml") `
    -Destination (Join-Path $CodexHomePath "luna.config.toml")

foreach ($agentFile in $agentFiles) {
    Install-ManagedFile `
        -Source (Join-Path $projectRoot ".codex\agents\$agentFile") `
        -Destination (Join-Path $CodexHomePath "agents\$agentFile")
}

$skillSource = Join-Path $projectRoot ".agents\skills\delegate-luna-workers"
$skillDestination = Join-Path $SkillsRootPath "delegate-luna-workers"
Install-ManagedFile `
    -Source (Join-Path $skillSource "SKILL.md") `
    -Destination (Join-Path $skillDestination "SKILL.md")
Install-ManagedFile `
    -Source (Join-Path $skillSource "agents\openai.yaml") `
    -Destination (Join-Path $skillDestination "agents\openai.yaml")

Write-Host "Luna Agent is installed. Restart Codex or open a new thread."
Write-Host "Launch it from a target repository with: codex -p luna"
