---
name: service-decommissioning
description: "Use when retiring services and remote bridge installs."
version: 0.1.0
platforms: [linux]
metadata:
  hermes:
    tags: [uninstall, services, ssh, cleanup, verification]
---

# Service decommissioning

Retire an application, plugin, and its remote helper services using official stop/uninstall controls followed by verified cleanup of application-owned files. Preserve the host application and shared runtimes unless their removal is explicitly in scope. Linux process identity checks below also apply inside WSL.

## When to use

- A user asks to stop using a plugin or service and remove local and remote installation artifacts.
- Uninstall leaves configuration, caches, detached bridges, SSH forwards, or reverse-proxy handlers.
- A multi-host cleanup must preserve existing terminal sessions and unrelated workloads.

For Herdr Web UI/Ovis specifics, read references/herdr-web-ui.md. This is a retirement workflow; use product-specific skills for ordinary application operation.

## Discovery

1. Distinguish research from execution. A request to investigate uninstall procedures authorizes inspection; a subsequent instruction to perform the reviewed cleanup authorizes those concrete actions without another confirmation.
2. Read supplied runbooks and installation scripts with `read_file`. Extract exact application IDs, accounts, SSH aliases, install directories, cache paths, staging directories, sessions, and ingress handlers. Do not execute old installation scripts.
3. Check the installed CLI's help and official docs/source. Separate registration removal, process termination, and data deletion: they may be independent operations. Record source version; if using a local official checkout, identify its remote and commit and label conclusions accordingly.
4. Inventory live processes, listening ports, service units, user startup entries, cron, proxies, application-specific SSH keys, and runtime/config directories. Avoid printing credentials or bridge tokens.
5. Record a baseline of parent service PIDs and process identities. Enumerate every target host and keep per-host results in a structured file. Run independent SSH inspections concurrently with bounded timeouts.

## Execution

1. Stop the controlling local application first to prevent reconnect/update loops from recreating remote helpers. Use the official stop action while the plugin is still registered and its files still exist.
2. Verify asynchronous actions actually finished: an action invocation returning a job/log marked running proves submission only. Confirm target processes have exited and the listener has closed before uninstalling.
3. Unregister the plugin using its installed ID. Re-read the registry; do not infer success from command exit alone.
4. Disable only the inspected ingress handler pointing to this service. Preserve unrelated handlers. When privileged changes are blocked, finish independently authorized cleanup and report the exact outstanding operation. Never mark the whole job complete while an ingress cleanup item remains pending.
5. On each remote host, re-read live bridge descriptors. Require managed ownership and match the PID's command arguments to the expected private runtime and entry point before signaling. If a Linux birth marker exists, compare it against boot ID and `/proc/PID/stat` start ticks. Never reuse PIDs from an earlier report.
6. Send SIGTERM only to verified helper processes. Poll for a bounded interval, treating zombies as no longer running. Verify their listeners close. If a process survives, inspect its identity and ownership again before deciding escalation.
7. Before deleting runtime directories, check that no live process still uses their executable or entry point. Validate exact paths, account ownership, symlinks, and installation-specific staging contents. Delete application-owned files only; include retained prior releases and caches when clean removal is requested.
8. Inspect remote authorized_keys for application-specific markers; remove only entries verified against the app's key/machine identity. Do not alter unrelated keys, SSH config, or the parent application's machine catalog.
9. Reconnect independently over SSH to verify every host after mutations. Aggregate results in code and account for every target, including failed or unreachable ones.

## Pitfalls

- A remote disconnect or removal from a UI may leave a detached bridge running. Neither means uninstall.
- Private bundled Bun/Node/Herdr executables and globally shared installations have different ownership. Preserve shared tools and host-application sessions by default.
- Similar process names do not establish ownership. Never use a broad `pkill` against the host application to remove its web plugin.
- Process searches can match the inspection shell's command text. Parse executable and script arguments; exclude the inspector and ancestor shell, and prefer exact executable/script paths over substring matching of a flattened command line.
- Product renames do not change the ID already installed. Use live registry IDs and actual filesystem paths, not names from a newer README.
- A service may launch via SSH without systemd. Report the startup locations actually checked rather than claiming exhaustive absence of all persistence mechanisms.
- Keep stop, verification, uninstall, and deletion sequential. Avoid semicolon-chained commands whose final exit code can hide an earlier failure.
- Keep audit reports outside directories scheduled for deletion. Record mutation failures as failures, rather than replacing them with success-shaped data.

## Verification and reporting

Require all applicable checks per target:

- No application-owned process or SSH forwarding connection remains.
- Its listener is closed, registration is gone, and private runtime/config/cache paths are absent.
- Corresponding ingress handlers have been removed, or are explicitly listed as unresolved.
- Unrelated parent services retain their original identities and remain available.
- Dedicated SSH keys are removed or their absence is verified.

Report completed changes first, then any blocker with its exact remaining command. Keep blocked checklist items pending. Preserve sanitized structured evidence; do not store session PIDs, host addresses, completed-work logs, or transient permission failures as durable skill facts.
