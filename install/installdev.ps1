param([switch][bool]$currentbranch) 

function confirmit ($message, $caption)
{
Add-Type -AssemblyName 'PresentationFramework'
$continue = [System.Windows.MessageBox]::Show($message, $caption, 'YesNo');

return  ($continue -eq 'Yes')
}

if ($currentbranch) 
{
    pip install ..[full] 
}
else 
{
    pip install compare_my_stocks[full]
}
pip install git+https://github.com/csingley/ibflex.git

$path=python -c "import compare_my_stocks;import os;print(os.path.dirname(compare_my_stocks.__file__))" 
if ($path -eq $null) 
{
    echo "Couldnt find package. aborting" 
}
if (Test-Path "$env:USERPROFILE\.compare_my_stocks")
{
$override = confirmit "The directory $env:USERPROFILE\.compare_my_stocks already exists. Should it be deleted?" "Delete directory"
if ($override)
{
rm "$env:USERPROFILE\.compare_my_stocks" -Recurse -Force
}
else 
{
    return 
}
}
cp -Recurse "$path\data" "$env:USERPROFILE\.compare_my_stocks"

