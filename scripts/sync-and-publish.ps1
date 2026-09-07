[CmdletBinding()]
param(
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$publishPaths = @(
    "data/raw/p3_history.csv",
    "data/raw/p5_history.csv",
    "data/processed/benchmarks.json",
    "data/processed/predictions.json",
    "data/processed/summary.json",
    "docs/data/benchmarks.json",
    "docs/data/p3-history.json",
    "docs/data/p5-history.json",
    "docs/data/predictions.json",
    "docs/data/summary.json"
)

function Invoke-Checked {
    param(
        [Parameter(Mandatory)] [string]$Command,
        [Parameter(Mandatory)] [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "Project Python environment not found: $python"
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git is not available on PATH"
}

if ($CheckOnly) {
    Write-Output "Sync prerequisites are ready in $repoRoot"
    exit 0
}

$mutex = [Threading.Mutex]::new($false, "Local\arranged-analys-sync")
if (-not $mutex.WaitOne(0)) {
    Write-Output "Another lottery sync is already running."
    exit 0
}

try {
    Set-Location -LiteralPath $repoRoot
    Invoke-Checked -Command "git" -Arguments @("pull", "--ff-only", "origin", "main")
    Invoke-Checked -Command $python -Arguments @("scripts/build_site.py")
    Invoke-Checked -Command "git" -Arguments (@("add", "--") + $publishPaths)

    & git diff --cached --quiet -- @publishPaths
    if ($LASTEXITCODE -eq 0) {
        Write-Output "No new lottery draw is available."
        exit 0
    }
    if ($LASTEXITCODE -ne 1) {
        throw "Unable to inspect staged lottery data changes."
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Invoke-Checked -Command "git" -Arguments @("commit", "-m", "chore: refresh lottery data ($timestamp)")
    Invoke-Checked -Command "git" -Arguments @("push", "origin", "main")
    Write-Output "Lottery data and strategy were published at $timestamp."
}
finally {
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
