# Terminal bridge update preflight and missing agent identity

Validated against Collie 1.25.1 with a Herdr 0.9.x crew. Recheck installed help and embedded documentation before relying on version-specific state schemas.

## Attribute the error before touching a process

Run `collie doctor --json`, `collie update --check --local --plain`, and `collie update --check --json`. Separate local checks, aggregated runtime findings, and each member's checks. Save and parse full JSON rather than assuming that a warning badge names the failing host.

In the validated case, the lead's `agent-sessions` check inspected the crew snapshot. It reported a pane ID without its host. Identical pane IDs can exist on different machines: a reported `w1:p8` belonged to a remote member, while the local pane with that ID was a shell. Attribute each finding using `/api/snapshot` entries' `host`, `paneId`, `agent`, and `hasSession`, then read Herdr on that exact host and named session.

Distinguish `NO session` from `no session YET`. The observed check treated Hermes without a journal identity as an error, but allowed Codex without an identity before its first prompt. Do not send a fabricated prompt, invent an ID, or restart every agent merely to make counts green.

## Preserve a running agent while restoring identity

1. Check `herdr integration status` on the actual host. A current integration can coexist with a process started before installation.
2. Read the installed hook to identify its supported reporting command and identity format. The validated Hermes hook used `herdr pane report-agent-session` with source `herdr:hermes`.
3. Establish the identity from independent live evidence. Match the process's `/proc/<pid>/environ` values `HERDR_PANE_ID` and `HERDR_SOCKET_PATH`; verify its open session database; match the active terminal's conversation title and content to the session row in that database. Read the database read-only. A newest row or similar title alone is insufficient. Do not infer a session ID from a directory name or invent a UUID.
4. Only when that mapping is unambiguous, report the existing identity using installed syntax:

```sh
herdr --session <actual-herdr-session> pane report-agent-session <pane-id> \
  --source herdr:hermes --agent hermes \
  --agent-session-id <verified-existing-session-id> \
  --session-start-source resume
```

5. Read back `herdr ... agent get <pane-id>`. Confirm `agent_session.value` matches the actual existing session. This reports metadata; it does not restart or resume the agent.
6. Let bridge polling propagate the change. Re-read the lead snapshot until the exact host/pane reports `hasSession: true`, with a bounded deadline. An immediate doctor invocation can still read the previous snapshot; do not stack another fix on that stale result.
7. Re-run doctor and local update preflight. In the validated repair the existing process stayed running and preflight changed from red to green.

If the identity cannot be proven, leave the process alone. Explain that its integration normally activates on a new session; obtain user direction before interrupting ongoing work. Treat hook installation and live-session metadata repair as separate operations.

## Manual enrollment and SSH maintenance routes

A member can be runtime-reachable yet lack the SSH operations record needed by CLI crew updates. This can happen after manual enrollment. Full `collie update --check --json` can report `ops-record: no ssh record`, while the local preflight is green. Runtime crew addresses and SSH installation aliases are different endpoints.

Prefer the installed CLI's supported route-registration flow and follow its printed remedy. Check whether that command also updates software before running it when only diagnosis or configuration repair was requested.

The inspected 1.25.1 implementation stored owner-only `<stateDir>/crew-ops.json` as:

```json
{
  "version": 1,
  "members": {
    "<actual-member-id>": {
      "sshHost": "<verified-ssh-alias>",
      "path": "<remote-install-root>",
      "port": 8787,
      "recordedAt": 0,
      "anchoredGeneration": null,
      "anchoredAt": null
    }
  }
}
```

In the actual repair, `recordedAt` was current Unix epoch milliseconds, not the illustrative zero above. The install root was the versioned install's parent containing `current`, not a guessed checkout. If no configuration-only CLI exists, inspect the current parser and writer before editing, back up and merge existing records, write atomically with mode 600, preserve unrelated members, and do not manufacture trust anchors. This schema is a version-scoped fallback, not a public API guarantee.

Verify by rerunning full preflight: each SSH alias must answer, the remote install must resolve, versions and free space must be read successfully, and no `ops-record` failure may remain. In the validated case all those checks passed after the records were added.

## Report the actual gate

- Red: blocking failure that requires investigation.
- Amber: inspect each reason. The observed warnings explicitly said an update could proceed; do not conflate them with red blockers.
- A remote `agent-sessions: skipped` because a local probe did not answer is not evidence of zero agents or a dead runtime crew link.
- A successful preflight establishes readiness, not a completed upgrade. Do not claim the target version is installed without updating and reading it back.
- Phone update pages can retain an older check timestamp. After fixing the live check, ask the user to rerun it or reopen that page; do not rotate pairing credentials or restart agents to refresh the UI.
