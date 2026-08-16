# snap_fullscreen.py — 用 PowerShell .NET CopyFromScreen 截取 VM 主显示器真内容
# （绕开 PIL ImageGrab.grab 抓错桌面的问题）
import subprocess
import os

VM_SHOT_DIR = r"C:\rpa\screenshots"
OUT_PATH = os.path.join(VM_SHOT_DIR, "fullscreen.png")


def main(r):
    os.makedirs(VM_SHOT_DIR, exist_ok=True)

    # PowerShell .NET 截全屏（CopyFromScreen 抓主显示器物理像素）
    ps_script = r'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$g.Dispose()
$bmp.Save('%s', [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output ("OK " + $b.Width + "x" + $b.Height)
''' % OUT_PATH

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        r.emit("powershot", detail={
            "path": OUT_PATH,
            "stdout": stdout[:200],
            "stderr": stderr[:200],
            "rc": result.returncode,
        })
        if result.returncode != 0:
            r.emit("error", detail={"stderr": stderr})
            return {"ok": False, "error": stderr}

        # 验证文件存在且有大小
        size = os.path.getsize(OUT_PATH) if os.path.exists(OUT_PATH) else 0
        return {"ok": True, "path": OUT_PATH, "size_bytes": size}
    except Exception as e:
        r.emit("exception", detail={"error": repr(e)})
        return {"ok": False, "error": repr(e)}


if __name__ == "__main__":
    import rpa_core as R
    R.Runner("snap_fullscreen").run(main)
