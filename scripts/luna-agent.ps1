[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $projectRoot "src"

$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $env:PYTHONPATH = $sourceRoot
    & $pythonCommand.Source -3 -m luna_agent @RemainingArgs
    exit $LASTEXITCODE
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw "Python 3.11 or newer was not found."
}

$version = & $pythonCommand.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or [version]$version -lt [version]"3.11") {
    throw "Python 3.11 or newer is required."
}

$env:PYTHONPATH = $sourceRoot
& $pythonCommand.Source -m luna_agent @RemainingArgs
exit $LASTEXITCODE
