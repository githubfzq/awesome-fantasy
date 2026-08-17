# close_popup.ps1
# 读取并（可选）关闭一个 Win32 对话框（#32770）。
# 参数（由 cua_ps.py 注入为 $arg1/$arg2）：
#   $arg1 = 标题关键字（如 "ProcDataDeal"、"系统错误"、"MSVCR"）；为空则匹配所有对话框
#   $arg2 = 要点击的按钮文字（如 "确定"、"是"）；为空则只读取不点击
# 输出：找到的窗口标题、控件清单；若点击则输出 CLICKED=hwnd
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class W32 {
  public delegate bool EnumWin(IntPtr h, IntPtr lp);
  [DllImport("user32.dll")] public static extern IntPtr FindWindow(string cls, string title);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWin e, IntPtr p);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumWin e, IntPtr lp);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
}
"@

$titleKw = if ($arg1) { $arg1 } else { "" }
$btnKw   = if ($arg2) { $arg2 } else { "" }

# 找匹配的顶层对话框
$target = $null
[W32]::EnumWindows({
  param($hwnd, $lp)
  if (-not [W32]::IsWindowVisible($hwnd)) { return $true }
  $cls = New-Object System.Text.StringBuilder 256
  [W32]::GetClassName($hwnd, $cls, 256) | Out-Null
  if ($cls.ToString() -ne '#32770') { return $true }
  $len = [W32]::GetWindowTextLength($hwnd)
  if ($len -le 0) { return $true }
  $sb = New-Object System.Text.StringBuilder ($len+1)
  [W32]::GetWindowText($hwnd, $sb, $len+1) | Out-Null
  $title = $sb.ToString()
  if ($titleKw -eq '' -or $title -like "*$titleKw*") {
    $script:target = $hwnd
    $script:targetTitle = $title
    return $false
  }
  return $true
}, [IntPtr]::Zero)

if ($null -eq $target) {
  "NO_DIALOG_FOUND titleKw='$titleKw'"
  exit 0
}

"DIALOG: $targetTitle [hwnd=$target]"
"--- controls ---"
[W32]::EnumChildWindows($target, {
  param($ch, $lp)
  $len = [W32]::GetWindowTextLength($ch)
  $cls = New-Object System.Text.StringBuilder 256
  [W32]::GetClassName($ch, $cls, 256) | Out-Null
  $text = ""
  if ($len -gt 0) {
    $sb = New-Object System.Text.StringBuilder ($len+1)
    [W32]::GetWindowText($ch, $sb, $len+1) | Out-Null
    $text = $sb.ToString()
  }
  "$($cls) | $text [hwnd=$ch]"
  return $true
}, [IntPtr]::Zero)

if ($btnKw -ne '') {
  $clicked = $null
  [W32]::EnumChildWindows($target, {
    param($ch, $lp)
    $cls = New-Object System.Text.StringBuilder 256
    [W32]::GetClassName($ch, $cls, 256) | Out-Null
    if ($cls.ToString() -ne 'Button') { return $true }
    $len = [W32]::GetWindowTextLength($ch)
    if ($len -le 0) { return $true }
    $sb = New-Object System.Text.StringBuilder ($len+1)
    [W32]::GetWindowText($ch, $sb, $len+1) | Out-Null
    if ($sb.ToString() -like "*$btnKw*") {
      [W32]::SendMessage($ch, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)  # BM_CLICK
      $script:clicked = $ch
      return $false
    }
    return $true
  }, [IntPtr]::Zero)
  if ($clicked) { "CLICKED hwnd=$clicked ($btnKw)" } else { "BUTTON_NOT_FOUND: $btnKw" }
}
