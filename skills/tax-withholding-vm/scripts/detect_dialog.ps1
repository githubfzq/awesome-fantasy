# detect_dialog.ps1 — 枚举可见顶层窗口，命中错误弹窗关键字就报告
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WDet {
  public delegate bool EW(IntPtr h, IntPtr lp);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EW e, IntPtr p);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
}
"@

$found = @()
[WDet]::EnumWindows({
  param($hwnd, $lp)
  if (-not [WDet]::IsWindowVisible($hwnd)) { return $true }
  $len = [WDet]::GetWindowTextLength($hwnd)
  if ($len -le 0) { return $true }
  $sb = New-Object System.Text.StringBuilder ($len+1)
  [WDet]::GetWindowText($hwnd, $sb, $len+1) | Out-Null
  $t = $sb.ToString()
  if ($t -like '*ProcDataDeal*' -or $t -like '*系统错误*' -or $t -like '*MSVCR*' -or $t -like '*错误*') {
    $script:found += $t
  }
  return $true
}, [IntPtr]::Zero)

if ($script:found.Count -eq 0) { "NO_ERROR_DIALOG_FOUND" }
else { $script:found | ForEach-Object { "FOUND_DIALOG: $_" } }

"--- tax processes ---"
Get-Process | Where-Object {$_.Name -like '*EPPortal*' -or $_.Name -like '*EPEvenue*' -or $_.Name -like '*ProcDataDeal*'} |
  Select-Object Name,Id,Responding | Format-Table -AutoSize | Out-String -Width 200
