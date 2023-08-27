[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
function Installpy 
{
     [CmdletBinding(SupportsShouldProcess)]
     param() 
     if($PSCmdlet.ShouldProcess("Python 3.9.6"))
     {
         Write-Host "Installing Python 3.9.6"
     }
     else{ return ; } 

    mkdir -p installtmp
    Push-Location installtmp
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.9.6/python-3.9.6-amd64.exe"  -OutFile "python-3.9.6.exe"
    ./python-3.9.6.exe /quiet InstallAllUsers=0 PrependPath=1
    rm ./python-3.9.6.exe
    Pop-Location
    &"~\AppData\Local\Programs\Python\Python39\python.exe" -m pip install voila
    &"~\AppData\Local\Programs\Python\Python39\python.exe" -m pip install ipykernel
    &"~\AppData\Local\Programs\Python\Python39\python.exe" -m pip install compare_my_stocks-0.1.0-py3-none-any.whl[jupyter]
}


function main 
{
    $cmd=get-command python.exe -ErrorVariable err -ErrorAction SilentlyContinue 

    if ($err)
    {
        Write-Host "Python is not installed, installing.."
        Installpy -Confirm:$false 
    }
    else
    {
        $ver = &"$($cmd.path)" --version 
    if ($ver -notlike "*3.9.6*")
    {
    Write-Host "Python version is not 3.9.6 but $($ver)." 
    Write-Host "The compiled version of the app requires python 3.9.6 to work properly. Should it be installed?" 
    Installpy -Confirm:$true
    }
    else { 
    &"$($cmd.path)" -m pip install voila
    &"$($cmd.path)" -m pip install ipykernel
    &"$($cmd.path)" -m pip install compare_my_stocks-0.1.0-py3-none-any.whl[jupyter]
    }
    }
}
try 
{main } 
finally 
{ cmd /c "pause" } 
