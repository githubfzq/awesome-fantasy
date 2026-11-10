# Herdr Web UI / Ovis retirement reference

Verified approach from a Linux/WSL installation with SSH-managed remote helpers. Recheck installed CLI and source before applying to a different release.

## Sources

- https://github.com/devswha/herdr-web-ui/blob/v0.4.12/docs/guide.md#uninstall
- https://github.com/devswha/herdr-web-ui/blob/v0.4.12/docs/remote-pcs.md
- https://github.com/devswha/herdr-web-ui/blob/v0.4.12/server/remote-host.ts
- https://herdr.dev/tui/docs/plugins/

The installed v0.4.12 checkout documented `devswha.herdr-web-ui`; a subsequently fetched v0.4.21 tag used the Ovis name. Discover actual installed IDs rather than assuming either name.

## Local commands

Through `terminal`, inspect `herdr plugin list --json`, `herdr plugin config-dir <id>`, and relevant help. Observe the Herdr skill's environment requirements before issuing control commands.

For the old ID, the official sequence is:

```sh
herdr plugin action invoke devswha.herdr-web-ui.stop
# Verify action completion and process/listener exit before proceeding.
herdr plugin uninstall devswha.herdr-web-ui
```

`herdr plugin action invoke` can return a log status of running. Stop completion must be verified separately. The plugin-managed launcher can run `server/managed.ts`, with an updated `server/supervisor.ts` under the application's updates directory.

Herdr unregisters the plugin while retaining config/state; source directories may also persist according to managed-installation tracking. There is no need to stop the Herdr daemon to delete an unused plugin checkout after its processes have exited.

Potential dedicated paths, to discover and verify rather than blindly delete:

- `~/.config/herdr-web-ui/`: preferences, paired devices, push subscriptions, SSH state, updates, bundle cache, Portal identity.
- `~/.local/state/herdr/plugins/devswha.herdr-web-ui/`: logs, PID files, historical bundle cache.
- `~/.config/herdr/plugins/config/devswha.herdr-web-ui/`: persistent plugin settings.
- `~/.config/herdr/plugins/github/devswha.herdr-web-ui-*/`: installed source checkouts.
- User-provided installation-helper directories and verified temporary bundle/chunk staging.

Preserve the rest of `~/.config/herdr`, existing machines/sessions, shared Bun/Node, and `~/.local/bin/herdr` unless explicitly included in scope.

## Remote bridges

Disconnect/Remove PC retains remote processes. Remote registration may also append an application key marked `herdr-web-ui:<machine-id>`; removing a local registration does not remove that remote authorized_keys entry.

Private runtime: `~/.local/share/herdr-web-ui/remote-v<N>` with checksum-addressed releases beside version links. Registry: `~/.config/herdr-web-ui/bridges/*.json`. Read descriptors without printing tokens.

Descriptors can include `managed_remote`, `pid`, `port`, socket identity, bundle version, and `birth`. Match command arguments to `<private runtime>/server/remote-entry.ts` before SIGTERM. The official POSIX implementation stops the selected bridge using SIGTERM. Remote entry is intentionally detached from the SSH connection; disconnecting does not terminate it.

Linux birth verification:

- Read `/proc/sys/kernel/random/boot_id`.
- Parse `/proc/PID/stat` after its final command-name closing parenthesis; starttime is index 19 of the remaining whitespace fields (overall field 22).
- Compare `<boot-id>:<starttime>` with the descriptor's Linux birth value, when present.
- Prefer pidfd-based signaling where supported to reduce the remaining identity-check/signal race.

After termination verify the descriptor port is closed and no process references any private runtime release. Only then remove the private runtime and dedicated remote config directory. Reconnect over SSH and verify absence independently.

Do not kill `herdr remote-client-bridge`: it is Herdr's native remote connection, distinct from the Bun process executing the web plugin's `remote-entry.ts`. Existing Herdr daemons and terminal workloads must survive Web Bridge retirement.

## Ingress and verification

Read `tailscale serve status --json` if Tailscale was used. Match the proxy's actual destination and inspect other handlers before altering a port. For a dedicated HTTPS port whose only handler serves this app, official uninstall docs use `tailscale serve --https=<port> off`. Verify the resulting Serve configuration. Do not save a particular machine's privilege failure as a permanent tool limitation.

Verify the local plugin registry, listener, processes, private paths, and Serve handler; verify remote bridges, listeners, paths, app-key entries, and surviving Herdr daemon identities for every host. Browser/PWA site data is a separate client-side artifact if the user requests its removal.
