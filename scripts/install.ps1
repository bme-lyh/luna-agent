[CmdletBinding()]
param(
    [string]$CodexHomePath = "",
    [string]$SkillsRootPath = "",
    [switch]$Force,
    [switch]$SkipCapabilityCheck
)

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
    $catalogResult = Invoke-CodexCaptured -Arguments @("debug", "models", "--bundled")
    if ($catalogResult.ExitCode -ne 0) {
        throw "Could not read the bundled Codex model catalog."
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
        throw "This Codex installation does not expose gpt-5.6-luna. Update Codex or check workspace model availability."
    }
    foreach ($effort in @("low", "medium", "high", "xhigh", "max")) {
        if ($luna.supported_reasoning_levels.effort -notcontains $effort) {
            throw "The installed Luna model catalog does not support reasoning effort '$effort'."
        }
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

function Move-LegacySkill {
    param(
        [Parameter(Mandatory = $true)][string]$LegacyPath,
        [Parameter(Mandatory = $true)][string]$DestinationPath
    )

    if (-not (Test-Path -LiteralPath $LegacyPath)) {
        return
    }
    $legacyItem = Get-Item -LiteralPath $LegacyPath
    if (-not $legacyItem.PSIsContainer) {
        throw "Legacy skill path is not a directory: $LegacyPath"
    }
    if (($legacyItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing to migrate a linked legacy skill directory: $LegacyPath"
    }
    if (Test-Path -LiteralPath $DestinationPath) {
        throw "Both legacy and current skill directories exist. Review them manually: $LegacyPath and $DestinationPath"
    }
    if (-not $Force) {
        throw "Legacy skill found at $LegacyPath. Re-run with -Force to rename it to Luna Agent."
    }

    $skillsRootFull = [System.IO.Path]::GetFullPath($SkillsRootPath).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    if ($skillsRootFull -ieq [System.IO.Path]::GetPathRoot($skillsRootFull)) {
        throw "Skills root must not be a filesystem root: $skillsRootFull"
    }
    $legacyFull = [System.IO.Path]::GetFullPath($LegacyPath)
    $destinationFull = [System.IO.Path]::GetFullPath($DestinationPath)
    if (
        [System.IO.Path]::GetDirectoryName($legacyFull) -ine $skillsRootFull -or
        [System.IO.Path]::GetDirectoryName($destinationFull) -ine $skillsRootFull
    ) {
        throw "Skill migration paths must be direct children of $skillsRootFull"
    }

    New-Item -ItemType Directory -Path $skillsRootFull -Force | Out-Null
    Move-Item -LiteralPath $legacyFull -Destination $destinationFull
    Write-Host "Migrated skill: $legacyFull -> $destinationFull"
}

$skillSource = Join-Path $projectRoot ".agents\skills\luna-agent"
$legacySkillDestination = Join-Path $SkillsRootPath "delegate-luna-workers"
$skillDestination = Join-Path $SkillsRootPath "luna-agent"
Move-LegacySkill `
    -LegacyPath $legacySkillDestination `
    -DestinationPath $skillDestination
Install-ManagedFile `
    -Source (Join-Path $skillSource "SKILL.md") `
    -Destination (Join-Path $skillDestination "SKILL.md")
Install-ManagedFile `
    -Source (Join-Path $skillSource "agents\openai.yaml") `
    -Destination (Join-Path $skillDestination "agents\openai.yaml")

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

Write-Host "Luna Agent is installed. Restart Codex or open a new thread."
Write-Host "Launch it from a target repository with: codex -p luna"
Write-Host "Invoke the Skill with: `$luna-agent"
