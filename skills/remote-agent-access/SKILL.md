---
name: remote-agent-access
description: "Use when deploying mobile access to agent terminals."
---

# Remote access to agent terminals

Use for private mobile dashboards, multi-machine terminal bridges, device pairing, and notifications for persistent AI development sessions. This covers the access service around a multiplexer; load the Herdr skill separately before controlling Herdr sessions. Follow its caller-context and process-preservation rules.

## Workflow

1. Inspect the original product documentation and installed CLI. Discover machines, Unix users, named multiplexer sessions, socket paths, private network routes, service managers, and existing ingress mappings. Keep discovery read-only until deployment is authorized.
2. Model each boundary separately: phone → HTTPS ingress → dashboard lead → member bridge → multiplexer socket → agent. Saved SSH machines are not necessarily dashboard members. SSH installation reachability does not prove runtime bridge reachability.
3. Install verified release artifacts. Check the official manifest's platform, byte count, and SHA256 before extraction. If one machine downloads successfully while another cannot, transfer that same verified artifact over SSH and recheck it on the destination. Preserve the release layout used by the updater. Staging and installation can be on different filesystems; use a cross-filesystem-capable move or stage beside the target.
4. Start the lead with private HTTPS ingress, an explicit trusted operator identity, and device pairing. Preserve unrelated Serve mappings. On Linux check Tailscale operator privileges and user-service lingering. Use an authorized elevation path where available; do not ask for a password until required.
5. Enroll each member, configure its runtime address, restart only the necessary bridge, then read the crew roster back. A member must be reachable at the exact address advertised to the lead. Prefer a private overlay address with pinned mutual TLS, or a loopback service carried over SSH.
6. Verify every named session explicitly, including its rendered UI. Aggregate CLI enumeration, machine counts, and a successful health endpoint are insufficient evidence that the phone displays the desired session. Compare the default dashboard with an explicit machine/session URL and check a known pane label.
7. Generate pairing codes only when the user is ready. For iPhone, add the app to Home Screen first, then pair and enable notifications inside that app. When asked to regenerate a code, run the command immediately and return the fresh code and actual lifetime concisely. Never infer whether an older code was invalidated unless the response confirms it.
8. Verify paired-device and push-subscription lists. Send a test notification only after a subscription exists. Separate provider acceptance from the user's confirmation of lock-screen receipt. Test terminal reading and deliberate harmless input on the correct machine/session before claiming complete remote-control acceptance.

## Diagnosis and reporting

- A named session absent from the current view may already be discovered: check the backend registry, selected host, selected session, and UI filters before changing services.
- A static “Connecting…” boot splash can precede JavaScript execution. Check asset requests and console errors before blaming a healthy multiplexer. Do not save an unresolved loading symptom as a known browser incompatibility.
- A CLI read returning 403 is not proof of missing sessions. Read the error body; distinguish missing proxy identity, missing device credentials, and denied origin. Use documented local read credentials only from the authorized local host; never print secrets or disable authentication to diagnose.
- For systemd SSH tunnels, compare service and interactive authentication environments. Configure the intended SSH agent socket explicitly or use a suitable scoped key. Verify listener creation, end-to-end response, restart behavior, and key availability after reboot. Do not equate an enabled unit with a working tunnel.
- A tunnel unit that cannot authenticate is usually missing the agent, not missing the key. An interactive shell's `SSH_AUTH_SOCK` often points at a per-session temp socket that no service unit can see, so a unit that works by hand fails under systemd. Give the unit a dedicated key pair (add its public key to the far side's `authorized_keys`) and pass it with `IdentityFile` + `IdentitiesOnly=yes`.
- Measure the overlay path before blaming the application: `tailscale status` shows `direct` versus `relay` per peer, and a relay hop costs hundreds of ms plus packet loss. When one client is stuck on a relay, place the hop on a host that has a direct path to BOTH ends so the two legs are direct.
- Agent detection, lifecycle classification, journal access, and terminal rendering are separate capabilities. Installing hooks need not fix already-running agents; explain next-session activation and preserve ongoing work.
- A completion notification may mean the agent became idle, including after interruption; it is not evidence that tests or the requested task succeeded.
- User corrections during a long investigation steer the active task. When the user says the page now works and requests a pairing code, generate it rather than continuing the obsolete browser investigation.
- State precisely what was verified, what changed, and what still needs phone-side confirmation. Avoid reporting installation or a plan checklist as full end-to-end completion.

## References

Read [Collie deployment and named-session verification](references/collie.md) for validated commands, endpoint parameter distinctions, iPhone behavior, and SSH transport patterns. Recheck current upstream documentation before applying version-sensitive details.

Read [Windows-to-WSL SSH agent recovery](references/wsl-ssh-agent.md) when a WSL session cannot authenticate to remote hosts even though the same command worked earlier.
