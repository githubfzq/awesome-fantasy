# ADB / Root / su Debugging on Android (Termux)

Session-proven (2026-10-31, MIUI 13 / Android 13 / SDK 33, M2012K11AC) diagnostics for ADB remote debugging and root/su activation from Termux, without a PC.

## Detect ADB state (no extra packages needed)

```bash
getprop | grep -iE 'adb'          # all ADB-related props
getprop init.svc.adbd             # running = USB debugging on (adbd daemon alive)
getprop service.adb.tcp.port      # non-empty = legacy tcpip mode enabled (port 5555-style)
getprop service.adb.tls.port      # non-empty = Android 11+ wireless debugging on
getprop ro.adb.secure             # 1 = connect still requires on-screen RSA approval
ss -tln                           # Termux's ss cannot see adbd's listener (different netns)
nc -zv 127.0.0.1 5555             # reliable listener test: refused = closed
```

Gotcha: `settings get global adb_enabled` fails from Termux (needs INTERACT_ACROSS_USERS permission — SecurityException is normal, not a breakage).

Enable remote debugging (no root path):
- Android 11+: Settings → Developer options → Wireless debugging (random port, pair via code; discover with `adb mdns services` after `pkg install android-tools`).
- Legacy: needs a PC once: `adb tcpip 5555`, then `adb connect <phone-ip>:5555`. Lost on reboot.
- From Termux without root you CANNOT `setprop service.adb.tcp.port` — needs root (below).

## Enable 5555 with root (in Termux, no PC)

```bash
# Temporary (until reboot):
su -c 'setprop service.adb.tcp.port 5555 && stop adbd && start adbd'
# Persistent (survives reboot):
su -c 'setprop persist.adb.tcp.port 5555 && stop adbd && start adbd'
# Verify:
nc -zv 127.0.0.1 5555             # refused → open
# Turn off when done:
su -c 'setprop service.adb.tcp.port -1 && stop adbd && start adbd'
```

Notes: `ro.adb.secure=1` still shows the RSA approval dialog on first connect. 5555 is open to the whole LAN — turn it off after use. `stop/start adbd` may be refused by strict SELinux policies; reboot instead (with persist prop set).

## Is the device rooted? (proven decision tree)

```bash
su -c id                          # asks root manager / "No su program found" = no su reachable
ls -l /system/bin/su /sbin/su /debug_ramdisk/su 2>/dev/null
pm list packages | grep -iE 'magisk|kernelsu|supersu'   # UNRELIABLE on MIUI — see below
```

CRITICAL MIUI gotcha: `pm list packages` output is unstable — it can show ~20 packages one call and be EMPTY the next, and third-party apps may be invisible even when installed. A prior "not installed" conclusion from `pm list packages | grep magisk` was WRONG. Always confirm with `pm path <pkg>` (positive result is trustworthy) and filesystem evidence.

Magisk-active evidence in Termux's mount namespace:
- su wrapper (Termux's `usr/bin/su`) searches, in order: /debug_ramdisk/su /sbin/su /system/sbin/su /system/bin/su /system/xbin/su /su/bin/su /magisk/.core/bin/su
- If Magisk is ACTIVE, one of those resolves. NONE resolving + no magisk entries in /proc/self/mounts + /debug_ramdisk empty = Magisk installed but NOT injected into this app's namespace.

## "Magisk installed but su says not found" — #1 cause: DenyList

Magisk DenyList (Zygisk) unmounts all Magisk traces (su binary, mounts, props) from apps on its list. Termux is a common accidental victim ("check every app to hide root" tutorials). Result: exactly the state observed — APK installed, mounts/su invisible, `su` fails, while other apps get root fine.

Fix sequence:
1. Magisk app → gear (Settings) → Configure DenyList → uncheck Termux (all sub-process entries too). Also check Shamiko enforce list if installed.
2. FULLY kill Termux (swipe away from recents, or from a rooted shell: `am force-stop com.termux`). Mount namespace is injected at process start — NO effect until process restart. Highest-frequency community pitfall.
3. Reopen Termux → run `su` → approve the Magisk superuser dialog (choose persistent grant).
4. Verify: `su -c id` → uid=0.

If still "No su program found": check Magisk app home — "Installed: N/A" means boot image never patched (root not actually active; re-flash patched boot.img). Confirm which manager (Magisk vs KernelSU/APatch) and random-package-name hiding.
