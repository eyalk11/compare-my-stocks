$env:COMPARE_STOCK_PATH = "C:\Users\ekarni\.compare_my_stocks14"
& "$PSScriptRoot\.venv314\Scripts\python.exe" -m commonpy.monitor `
    --include-pkg matplotlib `
    --caller-dir C:\autoproj\compare-my-stocks `
    --with-stack `
    --log-file "$env:TEMP\mpl_user_caused.log" `
    -m compare_my_stocks
