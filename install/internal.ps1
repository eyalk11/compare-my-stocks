[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
function confirmit ($message, $caption)
{
Add-Type -AssemblyName 'PresentationFramework'
$continue = [System.Windows.MessageBox]::Show($message, $caption, 'YesNo');

return  ($continue -eq 'Yes')
}
function installpack ()
{
    Push-Location $PSScriptRoot
    $whl= gci -Filter "*.whl" | Select-Object -First 1
     &"$env:USERPROFILE\AppData\Local\Programs\Python\Python39\python.exe" -m pip install "$($whl.FullName)[jupyter]"
    Pop-Location
}
function Installpy 
{
     param($message) 
     if (-not $(confirmit $message "Python 3.9.6"))
     {return $false; } 
     
     Write-Host "Installing Python 3.9.6"
    Push-Location $env:TEMP 
    mkdir -p installtmp
    Push-Location installtmp
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.9.6/python-3.9.6-amd64.exe"  -OutFile "python-3.9.6.exe"
    ./python-3.9.6.exe /quiet InstallAllUsers=0 PrependPath=1
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
        $continue= Installpy "Python is not installed. Should it be installed(version 3.9.6)?" 
    }
    else
    {
        $ver = &"$($cmd.path)" --version 
    if ($ver -notlike "*3.9.6*")
    {
    $continue= Installpy " Python version is not 3.9.6 but $($ver). The compiled version of the app requires python 3.9.6 to work properly. Should it be installed?"
    }

    }
    if ($continue ) { installpack }

}
try 
{
    main } 
finally 
{ cmd /c "pause" } 
