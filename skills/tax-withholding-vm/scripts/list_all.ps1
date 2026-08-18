# list_all.ps1 — 列出全部进程（含路径）
Get-Process | Sort-Object ProcessName |
  Select-Object ProcessName,Id,Responding,Path |
  Format-Table -AutoSize | Out-String -Width 300
