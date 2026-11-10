# Overlay relays and mobile ingress: research checklist

This is a source-backed design reference, not a record of a tested OpenP2P/Tailscale deployment. Recheck upstream requirements before configuring services.

## Diagnose the right boundary

Separate phone → ingress, ingress/lead → member, overlay control plane, and Web Push delivery. A working machine-to-machine tunnel proves only that segment. `tailscale netcheck` on a desktop does not identify the phone's path; an offline phone record does not establish a cause. Choose relay location from actual latency/loss measurements across relevant operators rather than geographic distance.

## Tailscale Peer Relay

Official reference: https://tailscale.com/docs/features/peer-relay

- A relay belongs to the same tailnet as its clients and requires a `tailscale.com/cap/relay` capability grant. A public UDP address alone is insufficient. Ordinary business access policies still apply to communication through the relay; the relay itself needs no additional overlay network grant solely for relay allocation.
- Relay and participating clients require Tailscale 1.86+ per the reviewed docs. iOS can use a relay but cannot host one. Verify current versions/platform support.
- Example enable command: `sudo tailscale set --relay-server-port=40000`. Match the chosen UDP port in cloud security groups, host firewall, and upstream NAT mappings.
- Both participating endpoints must reach the advertised UDP endpoint. On the public interface, source addresses are clients' real public/NAT addresses, not their Tailscale 100.x addresses. Mobile source addresses change; source allowlists must account for this.
- Permit replies from the relay UDP socket to clients' actual source ports. Stateful firewalls commonly handle replies; stateless ACLs need explicit return rules.
- Port forwarding is supported; `--relay-server-static-endpoints=<reachable-IP>:<port>` advertises additional endpoints. Advertising an endpoint does not create reachability. Do not publish loopback or private addresses as universally reachable endpoints.
- The configured relay UDP listener is distinct from the usual UDP 41641 Tailscale socket. Do not copy DERP's inbound HTTP/HTTPS/STUN requirements onto Peer Relay. Preserve the normal Tailscale outbound access needed for coordination, DERP, STUN, DNS, and peer traffic.
- Peer Relay complements DERP; it does not replace all connection negotiation or the coordination service. Total UDP blocking prevents use of this UDP path.
- Verify actual traffic with `tailscale status` / `tailscale ping`: `peer-relay` proves relay selection, `direct` means direct connectivity, and `relay` indicates DERP. A listening socket or online relay node is insufficient.

Firewall source: https://tailscale.com/kb/1082/firewall-ports
Coordination-service limits: https://tailscale.com/docs/reference/coordination-server-down

## OpenP2P and other port-mapping transports

Official project: https://github.com/openp2p-cn/openp2p

The reviewed README documents local port mappings and application-layer UDP support. These capabilities alone do not prove transparent compatibility with Tailscale Peer Relay. Test bidirectional datagrams, concurrent client mappings, return paths, and successful Tailscale relay negotiation before recommending a composed UDP transport.

A mapping on machine A's 127.0.0.1 is accessible only on A. A LAN mapping does not automatically become accessible to a roaming phone. A design that requires a failing Tailscale route to reach its own replacement relay has a circular dependency.

For a user's already-working OpenP2P link, first inventory the actual endpoints, protocol, bind address, mapped ports, and Windows/WSL boundary. Consider carrying SSH or application traffic between fixed hosts directly rather than stacking an unverified relay protocol. Keep this a proposed design until exercised. Do not infer a usable iPhone client from Go's `ios` build target or a roadmap entry; verify an actual supported app and mobile behavior.

## Collie alternative ingress

Official reference: https://colliepwa.dev/zh/docs/deployment

Collie documents reverse-proxy-only ingress and other meshes/tunnels. Common settings include `COLLIE_SKIP_SERVE=1`, exact `COLLIE_PUBLIC_HOSTS`, and `COLLIE_ALLOWED_ORIGINS`. Preserve proxy authentication, pairing, Host/Origin gates, and trusted HTTPS. Changing phone ingress does not change lead/member transport. A WSL lead still depends on Windows/WSL availability. Revalidate PWA installation, pairing, and push when moving origin.

## Researching hosted relay providers

Classify each offering before comparison:

1. Actual hosted Tailscale Peer Relay node joining the customer's tailnet.
2. Configuration manager that sets policy on existing nodes.
3. Paid assistance deploying on the customer's NAS/router/server.
4. Hosted DERP service.
5. A different product's peer service, such as EasyTier.

Do not call categories 2–5 hosted Tailscale Peer Relay. Ask whether an offering requires customer-owned hardware, migration to another control plane, custom clients, or a service-managed node in the customer's existing tailnet. For the last option, evaluate scoped enrollment and network permissions rather than supplying unrestricted admin/API credentials.

Provider pages and social search snippets are leads, not performance evidence. Verify current product pages, actual mainland regions/operators, official-client/iPhone compatibility, bandwidth/traffic limits, TLS validation, trial/refund terms, and delivery timing. Report conflicting marketing claims and mark snippet-only details. Avoid persisting vendor prices, inventories, and unverified uptime guarantees as durable facts. If multiple searches find only deployment services or DERP, say no hosted Peer Relay was verified; do not claim none exists.
