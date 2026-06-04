param(
    [string]$CaseQuery = "",
    [int]$Display = 5,
    [int]$Timeout = 20
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ScriptPath = Join-Path $RepoRoot "scripts\law_api_probe.py"

$Candidates = @(
    "C:\Users\minso\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
    "python",
    "py"
)

$Python = $null
foreach ($Candidate in $Candidates) {
    try {
        if ($Candidate -like "*\*") {
            if (Test-Path $Candidate) {
                $Python = $Candidate
                break
            }
        } else {
            $Command = Get-Command $Candidate -ErrorAction SilentlyContinue
            if ($Command) {
                $Python = $Command.Source
                break
            }
        }
    } catch {
        continue
    }
}

if (-not $Python) {
    Write-Error "Python executable was not found. Install Python or update scripts\run_law_api_probe.ps1 with a local Python path."
}

if ($CaseQuery) {
    & $Python $ScriptPath --case-query $CaseQuery --display $Display --timeout $Timeout
} else {
    & $Python $ScriptPath --display $Display --timeout $Timeout
}
exit $LASTEXITCODE
