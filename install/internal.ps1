[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$VenvRoot = Join-Path $env:LOCALAPPDATA 'compare-my-stocks\venv'
$VenvPython = Join-Path $VenvRoot 'Scripts\python.exe'

function confirmit ($message, $caption)
{
    Add-Type -AssemblyName 'PresentationFramework'
    $continue = [System.Windows.MessageBox]::Show($message, $caption, 'YesNo')
    return ($continue -eq 'Yes')
}

function Ensure-Uv
{
    $cmd = Get-Command uv.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    if (-not (confirmit "uv is not installed. Install it now (recommended)?" "uv"))
    {
        throw "uv is required to continue."
    }

    Write-Host "Installing uv..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression

    $uvLocal = Join-Path $env:USERPROFILE '.local\bin\uv.exe'
    if (Test-Path $uvLocal) { return $uvLocal }

    $cmd = Get-Command uv.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    throw "uv install completed but uv.exe was not found on PATH."
}

function Ensure-Venv ($uv)
{
    if (Test-Path $VenvPython)
    {
        if (confirmit "venv already exists at $VenvRoot. Remove and recreate it?" "venv exists")
        {
            Write-Host "Removing existing venv at $VenvRoot..."
            Remove-Item -Recurse -Force $VenvRoot
        }
        else
        {
            Write-Host "Reusing existing venv at $VenvRoot"
            return
        }
    }

    Write-Host "Creating venv at $VenvRoot (Python 3.11)..."
    New-Item -ItemType Directory -Force -Path (Split-Path $VenvRoot) | Out-Null
    & $uv venv --python 3.11 $VenvRoot
    if ($LASTEXITCODE -ne 0) { throw "uv venv failed." }
}

function Install-Wheel ($uv)
{
    Push-Location $PSScriptRoot
    try
    {
        $whl = Get-ChildItem -Filter "*.whl" | Select-Object -First 1
        if (-not $whl) { throw "No wheel (*.whl) found next to this script." }
        Write-Host "Installing $($whl.Name)[jupyter] into venv..."
        & $uv pip install --python  $VenvPython --force-reinstall "$($whl.FullName)[jupyter]"
        if ($LASTEXITCODE -ne 0) { throw "uv pip install failed." }
    }
    finally { Pop-Location }
}

function main
{
    $uv = Ensure-Uv
    Ensure-Venv $uv
    Install-Wheel $uv
    Write-Host ""
    Write-Host "Done. Venv python: $VenvPython"
}

try { main }
finally { cmd /c "pause" }
