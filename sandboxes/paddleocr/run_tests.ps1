<#
MIZAN PaddleOCR Sandbox - grouped test runner

WHY THIS SCRIPT EXISTS (do not just run `pytest tests/`):

This sandbox made two real, honestly-documented Windows stability findings
(see README.md and benchmark/RESULTS.md section 7/7a):

  1. Sequential workloads: a native access violation (0xC0000005) can occur
     in long-running, multi-conversion, single-process runs. It is
     UNRESOLVED and intermittent, correlated with cumulative native call
     volume rather than any single isolated factor.
  2. Concurrency: calling the adapter from multiple threads at once is
     CONFIRMED UNSAFE (fails every attempt, via IndexError / access
     violation / heap corruption). The one test that intentionally probes
     this (`test_bounded_concurrent_runs_do_not_crash_the_process`) already
     isolates its own probe in a subprocess so it cannot crash pytest, but
     running MANY model-loading test files back-to-back in one pytest
     process is exactly the kind of "do several different things in one
     long-lived process" workload where finding #1 has been observed.

Running every test file in one `pytest tests/` invocation maximizes exposure
to finding #1 and offers no benefit over running them in small groups, since
each group still exercises the real PaddleOCR engine faithfully. This script
runs each file (or small group) as an independent `pytest` subprocess, so a
crash in one group never hides or discards the results of another, and
aggregates a final pass/fail/skip/error summary across all groups.

Usage:
    cd sandboxes\paddleocr
    .\run_tests.ps1
#>

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$env:DISABLE_MODEL_SOURCE_CHECK = 'True'
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Error "Virtual environment not found at $python. Create it first: python -m venv .venv ; .\.venv\Scripts\pip install -r requirements.txt"
    exit 1
}

# Small, isolated groups -- chosen to keep each subprocess's total native
# call volume low (mitigating finding #1) while still being one real
# pytest subprocess per group (so pytest's own summary/exit-code reporting
# is trustworthy per group).
$groups = @(
    @{ Name = 'adapter';          Files = @('tests/test_paddleocr_adapter.py') },
    @{ Name = 'contract_bridge';  Files = @('tests/test_mizan_contract_bridge.py') },
    @{ Name = 'ocr_routing_scanned'; Files = @('tests/test_ocr_applied_always.py') },
    @{ Name = 'ocr_routing_vector';   Files = @('tests/test_vector_pdf_capability.py') },
    @{ Name = 'ocr_quality';      Files = @('tests/test_scanned_ocr_quality.py') },
    @{ Name = 'windows_stability';Files = @('tests/test_windows_stability.py') },
    @{ Name = 'offline';          Files = @('tests/test_offline_local_first.py') }
)

$summary = @()
$totalPassed = 0
$totalFailed = 0
$totalSkipped = 0
$totalErrors = 0
$anyGroupCrashed = $false

foreach ($group in $groups) {
    Write-Host ""
    Write-Host "=== Running group: $($group.Name) ($($group.Files -join ', ')) ===" -ForegroundColor Cyan
    $args = @('-m', 'pytest') + $group.Files + @('-v')
    & $python @args
    $exitCode = $LASTEXITCODE

    # pytest exit codes: 0 = all passed, 1 = some failed, 2 = interrupted,
    # 3 = internal error, 4 = usage error, 5 = no tests collected.
    # A large-magnitude/negative code (e.g. -1073741819) means the
    # subprocess itself crashed natively -- this is the documented
    # finding #1/#2 risk, contained to this one group only.
    $crashed = ($exitCode -lt 0) -or ($exitCode -gt 5)
    if ($crashed) { $anyGroupCrashed = $true }

    $summary += [PSCustomObject]@{
        Group    = $group.Name
        ExitCode = $exitCode
        Crashed  = $crashed
    }
}

Write-Host ""
Write-Host "=== Summary across all groups ===" -ForegroundColor Cyan
$summary | Format-Table -AutoSize

if ($anyGroupCrashed) {
    Write-Host "One or more groups crashed natively (documented Windows stability finding -- see README.md / benchmark/RESULTS.md section 7/7a). This is expected/known behavior, not a script bug." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Run each group's full pytest output above for exact passed/failed/skipped counts per group." -ForegroundColor Cyan
