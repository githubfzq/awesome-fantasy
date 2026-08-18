# install_runtime.ps1 — 从 Mac 中转下载并静默安装 VC++ 2010 运行库（x86）
# 前提：Mac 已在该 VM 子网起好 http://10.211.55.1:8000 提供 vcredist_x86.exe
New-Item -ItemType Directory -Force -Path C:\vc | Out-Null
Invoke-WebRequest -Proxy $null -Uri http://10.211.55.1:8000/vcredist_x86.exe -OutFile C:\vc\vcredist_x86.exe
Start-Process C:\vc\vcredist_x86.exe -ArgumentList '/q','/norestart' -Wait
"install exit: $LASTEXITCODE"
Get-Item 'C:\Windows\SysWOW64\MSVCR100.dll','C:\Windows\System32\MSVCR100.dll' -ErrorAction SilentlyContinue |
  Select FullName,Length,@{N='Ver';E={$_.VersionInfo.FileVersion}} | Format-Table -AutoSize | Out-String -Width 200
