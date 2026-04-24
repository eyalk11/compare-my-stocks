# Launch compare_my_stocks in nogui mode from venv11, capture logs, kill after timeout.
Set-Location C:\autoproj\compare-my-stocks
$p = Start-Process -FilePath .\.venv11\Scripts\python.exe `
    -ArgumentList "-m","compare_my_stocks","--console","--nogui","--noprompt" `
    -WorkingDirectory C:\autoproj\compare-my-stocks `
    -RedirectStandardOutput nogui_out.log `
    -RedirectStandardError nogui_err.log `
    -PassThru -NoNewWindow
Start-Sleep 50
if (-not $p.HasExited) {
    Write-Output "STILL RUNNING - killing"
    Stop-Process -Id $p.Id -Force
} else {
    Write-Output "EXITED code=$($p.ExitCode)"
}
