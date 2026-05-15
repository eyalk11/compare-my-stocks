<#
.SYNOPSIS
    Test runner for compare-my-stocks. Works two ways:

    1) One-shot: .\run_tests.ps1 all
    2) Dot-sourced (Jupyter PS notebook style):
           . .\run_tests.ps1
           Run-Tests all
           Run-Tests file -Target src\compare_my_stocks\tests\test_graph_handler.py
           Get-LastFailures
           Get-LastLog
           Run-Matrix .\test_configs.json

.DESCRIPTION
    Wraps pytest with sensible defaults, tees output to a per-run log file,
    AND appends to a rolling testlog.txt with "Run N" markers so multiple
    interactive invocations can be sliced apart later (Get-FromLog).

    Inspired by chess_analyzer/init_cell_dotests.ps1 + dotests3.ipynb.
#>

param(
    [Parameter(Position=0)]
    [ValidateSet('file','test','all','allplus','intg','sanity','lf','ff','cov','xfail','collect','none')]
    [string]$Mode = 'none',

    [Parameter(Position=1)]
    [string]$Target = 'src/compare_my_stocks/tests',

    [string]$Extra  = '',
    [string]$Python = '',
    [switch]$NoLog,
    [switch]$Venv11,
    [switch]$Venv11b,
    [switch]$Venv314,
    [switch]$Pyenv311
)
rm Env:\COMPARE_STOCK_PATH
if ($Python) {
    # explicit override, use as-is
} elseif ($Venv11b) {
    $Python = Join-Path $PSScriptRoot '.venv11b\Scripts\python.exe'
        $envCOMPARE_STOCK_PATH = 'C:\Users\ekarni\.compare_my_stocks11'
} elseif ($Venv11) {
    $Python = Join-Path $PSScriptRoot '.venv11\Scripts\python.exe'
        $envCOMPARE_STOCK_PATH = 'C:\Users\ekarni\.compare_my_stocks11'
} elseif ($Pyenv311) {
    $Python = 'C:\Users\ekarni\.pyenv\pyenv-win\versions\3.11\python.exe'
    $envCOMPARE_STOCK_PATH = 'C:\Users\ekarni\.compare_my_stocks11'
} else {
    # default: .venv314
    $Python = Join-Path $PSScriptRoot '.venv314\Scripts\python.exe'
}

# --- Paths --------------------------------------------------------------------
$global:CMS_ROOT    = $PSScriptRoot
$global:CMS_LOGDIR  = Join-Path $CMS_ROOT 'test_logs'
$global:CMS_ROLLLOG = Join-Path $CMS_LOGDIR 'testlog.txt'
$global:CMS_LATEST  = Join-Path $CMS_LOGDIR 'latest.log'
$global:CMS_PYTHON  = $Python

if (-not (Test-Path $CMS_LOGDIR)) { New-Item -ItemType Directory -Path $CMS_LOGDIR | Out-Null }

# --- Pretty printing ----------------------------------------------------------
function Write-Banner {
    param([string]$Text, [string]$Color = 'Cyan')
    Write-Host ''
    Write-Host ('=' * 78) -ForegroundColor $Color
    Write-Host $Text       -ForegroundColor $Color
    Write-Host ('=' * 78) -ForegroundColor $Color
}

# --- Build pytest args from a Mode --------------------------------------------
function Get-PytestArgs {
    param([string]$Mode, [string]$Target, [string]$Extra)

    $args = @('-m', 'pytest')
    switch ($Mode) {
        'file'    { $args += $Target }
        'test'    { $args += $Target }
        'all'     { $args += 'src/compare_my_stocks/tests' }
        'allplus' { $args += @('-o', 'addopts=', 'src/compare_my_stocks/tests') }
        'intg'    { $args += @('-o', 'addopts=', '-m', 'integration', 'src/compare_my_stocks/tests') }
        'sanity'  {
            # Curated quick-confidence set: a representative slice of unit tests
            # across the core layers (parameters, common helpers, symbols,
            # serialization, currency, composition) plus the stockprices file
            # which contributes 1-2 RapidAPI integration tests (auto-skip if
            # the key isn't configured) and two test_synthetic_engine variants
            # that exercise the full CompareEngine path against a synthetic
            # IBSource (one with USEDATADIR to assert the in-tree data dir
            # is never mutated). `-o addopts=` clears the default
            # `-m 'not integration'` filter so the integration ones can run.
            $args += @(
                '-o', 'addopts=',
                'src/compare_my_stocks/tests/test_parameters.py',
                'src/compare_my_stocks/tests/test_simpleexception.py',
                'src/compare_my_stocks/tests/test_common.py',
                'src/compare_my_stocks/tests/test_serialization.py',
                'src/compare_my_stocks/tests/test_symbols.py',
                'src/compare_my_stocks/tests/test_composition_extended.py',
                'src/compare_my_stocks/tests/test_currency_adjust.py',
                'src/compare_my_stocks/tests/test_stockprices.py',
                'src/compare_my_stocks/tests/test_jupytertools.py',
                'src/compare_my_stocks/tests/test_inputprocessor_unit.py',
                'src/compare_my_stocks/tests/test_call_graph_generator.py',
                'src/compare_my_stocks/tests/test_default_notebook.py',
                'src/compare_my_stocks/tests/test_engine.py::test_synthetic_engine[price-line-UseInput.WITHINPUT|LOADDEFAULTCONFIG]',
                'src/compare_my_stocks/tests/test_engine.py::test_synthetic_engine[value-scatter-UseInput.WITHINPUT|LOADDEFAULTCONFIG|USEDATADIR]',
                'src/compare_my_stocks/tests/test_tries.py::test_local_config_loads_histfile'
            )
        }
        'lf'      { $args += @('--lf', 'src/compare_my_stocks/tests') }
        'ff'      { $args += @('-x', 'src/compare_my_stocks/tests') }
        'cov'     {
            $args += @(
                '--cov=src/compare_my_stocks',
                '--cov-report=term-missing',
                "--cov-report=html:$CMS_LOGDIR/htmlcov",
                'src/compare_my_stocks/tests'
            )
        }
        'xfail'   { $args += @('-rx', '--runxfail', 'src/compare_my_stocks/tests') }
        'collect' { $args += @('--collect-only', '-q', 'src/compare_my_stocks/tests') }
    }
    $args += @('-v', '--tb=short', '--no-header')

    if ($Extra) {
        $tokens = $null
        $parsed = [System.Management.Automation.PSParser]::Tokenize($Extra, [ref]$tokens) |
                  Where-Object { $_.Type -in 'CommandArgument','String','Number' } |
                  ForEach-Object { $_.Content }
        $args += $parsed
    }
    return $args
}

# --- Next "Run N" number from rolling log -------------------------------------
function Get-NextRunNumber {
    if (-not (Test-Path $CMS_ROLLLOG)) { return 1 }
    $matches = Select-String -Path $CMS_ROLLLOG -Pattern '^=== Run (\d+)' -AllMatches
    if (-not $matches) { return 1 }
    $maxN = ($matches | ForEach-Object { [int]$_.Matches.Groups[1].Value } | Measure-Object -Maximum).Maximum
    return $maxN + 1
}

# --- Main entrypoint (callable from notebooks) --------------------------------
function Run-Tests {
    [CmdletBinding()]
    param(
        [Parameter(Position=0)]
        [ValidateSet('file','test','all','allplus','intg','sanity','lf','ff','cov','xfail','collect')]
        [string]$Mode = 'all',

        [Parameter(Position=1)]
        [string]$Target = 'src/compare_my_stocks/tests',

        [string]$Extra  = '',
        [switch]$NoLog
    )

    $runN      = Get-NextRunNumber
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $perRunLog = Join-Path $CMS_LOGDIR ("run{0:D4}_{1}_{2}.log" -f [int]$runN, [string]$Mode, [string]$timestamp)

    $args = Get-PytestArgs -Mode $Mode -Target $Target -Extra $Extra

    # Resolve project + Python versions for the run header.
    $projVer = $null
    $verFile = Join-Path $CMS_ROOT 'version.txt'
    if (Test-Path $verFile) {
        $projVer = (Get-Content $verFile -Raw).Trim()
    } else {
        $pyproj = Join-Path $CMS_ROOT 'pyproject.toml'
        if (Test-Path $pyproj) {
            $line = Select-String -Path $pyproj -Pattern '^version\s*=\s*"([^"]+)"' | Select-Object -First 1
            if ($line) { $projVer = $line.Matches.Groups[1].Value }
        }
    }
    if (-not $projVer) { $projVer = '<unknown>' }
    $pyVer = (& $CMS_PYTHON -c "import sys,platform;print(platform.python_version()+' ('+sys.executable+')')" 2>&1) -join ' '

    Write-Banner ("Run #{0} | mode={1} | target={2}" -f $runN, $Mode, $Target)
    Write-Host "Version: $projVer"
    Write-Host "PyVer  : $pyVer"
    Write-Host "Python : $CMS_PYTHON"
    Write-Host "Cmd    : $CMS_PYTHON $($args -join ' ')"
    Write-Host "Log    : $perRunLog"
    Write-Host ''

    # Header captured into both per-run and rolling log.
    $header = @(
        ''
        "=== Run $runN @ $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
        "Version: $projVer"
        "PyVer: $pyVer"
        "Mode: $Mode"
        "Target: $Target"
        "Extra: $Extra"
        "Cmd: $CMS_PYTHON $($args -join ' ')"
        "GitHead: $(git -C $CMS_ROOT log -1 --pretty=format:'%h %s' 2>$null)"
        "Status:`n$((git -C $CMS_ROOT status --short 2>$null) -join "`n")"
        "--- output ---"
    )

    if (-not $NoLog) {
        Set-Content -Path $perRunLog -Value $header
        Add-Content -Path $CMS_ROLLLOG -Value $header
    }

    $start = Get-Date
    if ($NoLog) {
        & $CMS_PYTHON @args
        $exit = $LASTEXITCODE
    } else {
        & $CMS_PYTHON @args 2>&1 |
            Tee-Object -FilePath $perRunLog -Append |
            Tee-Object -FilePath $CMS_ROLLLOG -Append
        $exit = $LASTEXITCODE
        Copy-Item $perRunLog $CMS_LATEST -Force
    }
    $duration = (Get-Date) - $start

    $color  = if ($exit -eq 0) { 'Green' } else { 'Red' }
    $status = if ($exit -eq 0) { 'PASSED' } else { "FAILED (exit=$exit)" }

    $footer = "=== Run $runN END | $status | duration=$([Math]::Round($duration.TotalSeconds,1))s ==="
    if (-not $NoLog) { Add-Content -Path $CMS_ROLLLOG -Value $footer }

    Write-Banner $footer $color
    if (-not $NoLog) {
        Write-Host "Per-run log : $perRunLog"
        Write-Host "Rolling log : $CMS_ROLLLOG"
    }

    return [PSCustomObject]@{
        Run      = $runN
        Mode     = $Mode
        Target   = $Target
        ExitCode = $exit
        Passed   = ($exit -eq 0)
        Duration = $duration
        Log      = $perRunLog
    }
}

# --- Slice run N out of the rolling log ---------------------------------------
function Get-LastLog {
    [CmdletBinding()]
    param([int]$Run)

    if (-not (Test-Path $CMS_ROLLLOG)) {
        Write-Warning "No rolling log at $CMS_ROLLLOG"
        return @()
    }
    $lines = Get-Content $CMS_ROLLLOG
    if (-not $Run) {
        $hits  = $lines | Select-String -Pattern '^=== Run (\d+) @'
        if (-not $hits) { return @() }
        $Run   = [int]($hits[-1].Matches.Groups[1].Value)
    }
    $startHit = $lines | Select-String -Pattern "^=== Run $Run @"
    if (-not $startHit) {
        Write-Warning "Run $Run not found in $CMS_ROLLLOG"
        return @()
    }
    $startIdx = $startHit[0].LineNumber - 1

    $endHit = $lines[$startIdx..($lines.Length-1)] | Select-String -Pattern "^=== Run $Run END"
    if ($endHit) {
        $endIdx = $startIdx + $endHit[0].LineNumber - 1
    } else {
        $endIdx = $lines.Length - 1
    }
    return $lines[$startIdx..$endIdx]
}

function Get-LastFailures {
    [CmdletBinding()]
    param([int]$Run)
    $log = Get-LastLog -Run $Run
    if (-not $log) { return }
    # pytest summary: lines like "FAILED tests/...::test_x - AssertionError"
    $log | Select-String -Pattern '^(FAILED|ERROR)\s' |
        ForEach-Object { Write-Host $_.Line -ForegroundColor Red }
    # Also capture the short-test-summary section.
    $start = ($log | Select-String -Pattern 'short test summary info').LineNumber | Select-Object -First 1
    if ($start) {
        Write-Host ''
        Write-Host '--- short test summary ---' -ForegroundColor Yellow
        $log[($start-1)..([Math]::Min($start+50,$log.Length-1))] | ForEach-Object { Write-Host $_ }
    }
}

# --- Matrix runner: read JSON {flag: [v1,v2,...], ...} and run all combos -----
function Run-Matrix {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$ConfigJson,
        [string]$Mode   = 'all',
        [string]$Target = 'src/compare_my_stocks/tests'
    )
    if (-not (Test-Path $ConfigJson)) {
        throw "Config file not found: $ConfigJson"
    }
    $cfg     = Get-Content $ConfigJson -Raw | ConvertFrom-Json
    $envKeys = $cfg.PSObject.Properties.Name
    $axes    = @()
    foreach ($k in $envKeys) { $axes += ,@($cfg.$k) }

    # cartesian product
    $combos = @(@())
    foreach ($axis in $axes) {
        $next = @()
        foreach ($combo in $combos) {
            foreach ($v in $axis) { $next += ,($combo + @($v)) }
        }
        $combos = $next
    }

    Write-Banner "Matrix: $($combos.Count) combinations across $($envKeys.Count) axes"

    $results = @()
    $i = 0
    foreach ($combo in $combos) {
        $i++
        $envSet = @{}
        for ($j = 0; $j -lt $envKeys.Count; $j++) { $envSet[$envKeys[$j]] = $combo[$j] }
        $tag = ($envSet.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ', '
        Write-Host "`n[$i/$($combos.Count)] $tag" -ForegroundColor Cyan

        # Apply env vars for the duration of this run.
        $saved = @{}
        foreach ($k in $envSet.Keys) {
            $saved[$k] = [Environment]::GetEnvironmentVariable($k, 'Process')
            [Environment]::SetEnvironmentVariable($k, $envSet[$k], 'Process')
        }
        try {
            $r = Run-Tests $Mode $Target
            $results += [PSCustomObject]@{
                Index    = $i
                Config   = $tag
                Passed   = $r.Passed
                Duration = $r.Duration.TotalSeconds
                Log      = $r.Log
            }
        } finally {
            foreach ($k in $saved.Keys) {
                [Environment]::SetEnvironmentVariable($k, $saved[$k], 'Process')
            }
        }
    }

    Write-Banner "Matrix done | passed=$(($results|?{$_.Passed}).Count) failed=$(($results|?{-not $_.Passed}).Count)"
    return $results
}

function Show-Help {
    Write-Host ''
    Write-Host 'compare-my-stocks test runner' -ForegroundColor Cyan
    Write-Host '-----------------------------'
    Write-Host '  Run-Tests <mode> [-Target <path/nodeid>] [-Extra "<args>"]'
    Write-Host '    modes: all | allplus | intg | sanity | file | test | lf | ff | cov | xfail | collect'
    Write-Host '      allplus = all + integration (overrides addopts)'
    Write-Host '      intg    = integration-only'
    Write-Host '      sanity  = curated representative subset (incl. a couple of integration tests)'
    Write-Host '  Get-LastLog [-Run N]        — slice run N (or last) from rolling log'
    Write-Host '  Get-LastFailures [-Run N]   — show FAILED lines + summary'
    Write-Host '  Run-Matrix <config.json>    — env-var matrix (cartesian product)'
    Write-Host ''
    Write-Host 'Examples:'
    Write-Host '  Run-Tests all'
    Write-Host '  Run-Tests file -Target src\compare_my_stocks\tests\test_graph_handler.py'
    Write-Host '  Run-Tests test -Target "src/compare_my_stocks/tests/test_engine.py::TestRequiredSyms"'
    Write-Host '  Run-Tests all  -Extra "-k currency"'
    Write-Host '  Run-Tests cov'
    Write-Host '  Get-LastFailures'
    Write-Host ''
}

# --- Dispatch when invoked directly (not dot-sourced) -------------------------
# $MyInvocation.InvocationName is "." when dot-sourced, else the script path.
if ($MyInvocation.InvocationName -ne '.') {
    if ($Mode -eq 'none') {
        Show-Help
        return
    }
    Run-Tests $Mode $Target -Extra $Extra -NoLog:$NoLog | Out-Null
    exit $LASTEXITCODE
} else {
    Show-Help
}
