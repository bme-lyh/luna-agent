[CmdletBinding()]
param(
    [string]$CodexHomePath = "",
    [string]$SkillsRootPath = "",
    [string]$RuntimePath = "",
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
if ([string]::IsNullOrWhiteSpace($RuntimePath)) {
    $RuntimePath = Join-Path $CodexHomePath "luna-agent"
}

$pythonAvailable = $false
$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pythonLauncher) {
    & $pythonLauncher.Source -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
    $pythonAvailable = $LASTEXITCODE -eq 0
}
if (-not $pythonAvailable) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        & $pythonCommand.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
        $pythonAvailable = $LASTEXITCODE -eq 0
    }
}
if (-not $pythonAvailable) {
    throw "Python 3.11 or newer is required for isolated Luna workers."
}

if (-not $SkipCapabilityCheck) {
    if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
        throw "codex was not found on PATH. Install or update Codex before installing Luna Agent."
    }
    $execResult = Invoke-CodexCaptured -Arguments @("exec", "--help")
    if ($execResult.ExitCode -ne 0) {
        throw "Could not inspect codex exec capabilities."
    }
    $execHelp = $execResult.Lines -join "`n"
    foreach ($requiredFlag in @("--ignore-user-config", "--ephemeral", "--json")) {
        if (-not $execHelp.Contains($requiredFlag)) {
            throw "This Codex version is too old for isolated Luna workers. Update Codex first."
        }
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

$runtimeFiles = @(
    "src\luna_agent\__init__.py",
    "src\luna_agent\__main__.py",
    "src\luna_agent\cli.py",
    "src\luna_agent\models.py",
    "src\luna_agent\runner.py",
    "scripts\luna-agent.ps1",
    "scripts\luna-agent.sh"
)
foreach ($runtimeFile in $runtimeFiles) {
    Install-ManagedFile `
        -Source (Join-Path $projectRoot $runtimeFile) `
        -Destination (Join-Path $RuntimePath $runtimeFile)
}

Write-Host "Luna Agent is installed. Restart Codex or open a new thread."
Write-Host "Launch it from a target repository with: codex -p luna"
Write-Host "Check isolated workers with: $RuntimePath\scripts\luna-agent.ps1 doctor"
