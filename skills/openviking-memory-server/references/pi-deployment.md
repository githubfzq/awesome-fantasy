# Live instance — Raspberry Pi (raspberryfzq, Debian 12 aarch64)

## Placement

```
~/disk2/projects/openviking/
├── upstream/              official repo clone (mirror URL, pinned commit)
├── docker-compose.yml     podman-compose orchestration
├── ov.conf.tmpl.json      server config template, ${VAR} placeholders
├── render-conf.sh         template -> ~/.openviking/ov.conf + ovcli.conf
├── .env                   secrets, 0600, gitignored
└── README.md              deployment notes
```

Data: `~/disk4/openviking/data` (large disk)
Keys: `~/.openviking/keys/users.txt` (0600)

## Values that are known to work

- account `fanzuquan`; users `admin`/`shared`/`codex`/`opencode`/`dsh`/`hermes`
- embedding: minimax `embo-01`, dimension 1536
- VLM: LAN gateway, `auto/<model>`
- service port 1933, `network_mode: host`
- health: `GET /health` → `{"status":"ok","healthy":true,"version":"v0.5.3","auth_mode":"api_key"}`

## Commands

```sh
cd ~/disk2/projects/openviking
podman-compose up -d openviking
podman-compose logs -f openviking
```

Boot autostart goes through the host's existing `~/disk2/script/start_containers.sh` (driven by `podman-containers.service`). Add the container name there rather than creating a second boot unit.

## Disk hygiene on this host

- podman `graphroot` = `~/disk1/pods` — the real capacity bottleneck
- podman/buildah scratch space defaults to `/var/tmp` on the **OS disk**; an image pull can fill it. Set `TMPDIR` to the large disk in `~/.bashrc` **and** in the systemd unit that runs containers.
- Reclaim: `podman image prune -f` for dangling images; for `/var/tmp/storage*` leftovers, check each with `lsof +D` before removing.
- Do not add `--memory` / `mem_limit` / `deploy.resources.limits`: this host has no usable cgroup v2 memory controller and the container will not start.

## Changing the embedding model

```sh
podman-compose stop openviking
mv ~/disk4/openviking/data/vectordb ~/disk4/openviking/vectordb.bak-<old>
podman-compose up -d openviking
```

The backup must live outside `data/` — OV scans the data dir and will hit the stale collection again.
