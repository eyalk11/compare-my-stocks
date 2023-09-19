[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
function confirmit ($message, $caption)
{
Add-Type -AssemblyName 'PresentationFramework'
$continue = [System.Windows.MessageBox]::Show($message, $caption, 'YesNo');

return  ($continue -eq 'Yes')
}
function installpack ($path)
{
    if ($path -eq $null) { $path = "C:\Users\User\AppData\Local\Programs\Python\Python310\python.exe" }
    Push-Location $PSScriptRoot
    $whl= gci -Filter "*.whl" | Select-Object -First 1
    &$path -m pip install "$($whl.FullName)[jupyter]"
    Pop-Location
}
function Installpy 
{
     param($message) 
     if (-not $(confirmit $message "Python 3.10"))
     {return $false; } 
     
     Write-Host "Installing Python 3.10"
    Push-Location $env:TEMP 
    mkdir -p installtmp
    Push-Location installtmp
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.10.0/python-3.10.0rc2-amd64.exe"  -OutFile "pythonsetup.exe"
    ./pythonsetup.exe /quiet InstallAllUsers=0 PrependPath=1
    Pop-Location
    rm installtmp -Recurse -Force
    Pop-Location
    return $true 
}


function main 
{
    Write-Host "Installing voila and python(if needed)"
    $cmd=get-command python.exe -ErrorVariable err -ErrorAction SilentlyContinue 
    $continue = $true 

    if ($err)
    {
        $continue= Installpy "Python is not installed. Should it be installed(version 3.10)?" 
    }
    else
    {
        $ver = &"$($cmd.path)" --version 
    if ($ver -notlike "*3.10*")
    {
    $continue= Installpy " Python version is not 3.10 but $($ver). The compiled version of the app requires python 3.10 to work properly. Should it be installed?"
    }
    else 
    {
        $path=$cmd.Source
    }

    }
    if ($continue ) { installpack $path }

}
try 
{
    main } 
finally 
{ cmd /c "pause" } 
