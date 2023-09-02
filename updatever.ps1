Param( $ver)


#version='1.0.0'
#version = "1.0.0"

#filevers=(1, 0, 0, 0),
#prodvers=(1, 0, 0, 0),

#StringStruct('ProductVersion', '1.0.0.0'),
#StringStruct('FileVersion', '1.0.0.0'),


# Specify the file path
$file = "C:\path\to\file.txt"

# Specify the arbitrary version


$global:ver=$ver
function ModifyVer($file)
{
# Read the file content
$content = Get-Content -Path $file

# Loop through each line in the content
for ($i = 0; $i -lt $content.Length; $i++) {
    $src = "#define MyAppVersion "".*"""
    $dst = "#define MyAppVersion ""$ver"""
    $content[$i] = $content[$i] -replace $src, $dst

    $src= '^version = ".*"'
    $dst = 'version = "{0}"' -f $ver
    $content[$i] = $content[$i] -replace $src, $dst
    # Check if the line contains "filevers=(" and "prodvers=("
    $src= 'filevers=\(\d+, \d+, \d+, \d+\)'
# Replace the line with the arbitrary version
    $dst = 'filevers=({0}, {1}, {2}, 0)' -f ($ver -split '\.')
    $content[$i] = $content[$i] -replace $src, $dst

    $src= 'prodvers=\(\d+, \d+, \d+, \d+\)'
# Replace the line with the arbitrary version
    $dst = 'prodvers=({0}, {1}, {2}, 0)' -f ($ver -split '\.')
    $content[$i] = $content[$i] -replace $src, $dst

    $src= "StringStruct\('ProductVersion', '\d+\.\d+\.\d+\'\)"
# Replace the line with the arbitrary version
    $dst = "StringStruct('ProductVersion', '$ver')"
    $content[$i] = $content[$i] -replace $src, $dst

    $src= "StringStruct\('FileVersion', '\d+\.\d+\.\d+\'\)"
# Replace the line with the arbitrary version
    $dst = "StringStruct('FileVersion', '$ver')"
    $content[$i] = $content[$i] -replace $src, $dst
}
$content | Set-Content -Path $file

}
ModifyVer '.\compare-my-stocks.iss'

ModifyVer '.\pyproject.toml'
ModifyVer '.\setup.py'
ModifyVer '.\version.txt'
# Write the modified content back to the file
