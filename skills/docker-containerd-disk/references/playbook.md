# Docker / containerd 磁盘清理 Playbook

## 判定表

| 观察 | 含义 | 建议 |
|------|------|------|
| `Docker Root Dir` 在外盘，`/var/lib/containerd` 仍很大 | data-root 未带走 containerd root | 按阶梯清 containerd 缓存，或迁 containerd root |
| 全部容器 `GraphDriver=overlay2` 且 UpperDir ⊆ Docker Root | 容器层不在 containerd 目录 | A/B 清系统盘通常安全 |
| `mount` 含 `io.containerd.snapshotter` | 有容器/任务在用 snapshotter | **勿**激进删 snapshot；先停相关任务 |
| Active snapshot ID ≈ docker 容器 ID | snapshot 可能是真 rootfs | 禁止 C；慎 B |
| Active snapshot 对不上任何容器 | 孤儿 Active | 可纳入 GC 候选 |
| 大量 `moby-dangling@...` | 无 tag 残留 manifest | 优先 `ctr images rm` |
| `ctr namespaces` 有 `k8s.io` 且 CRI 启用 | 可能是 kubelet | 本技能默认流程不适用，改走 k8s 镜像 GC |
| 仅 `moby` / `moby_history` | Docker 专用 | 按本 playbook |

## content vs snapshotter

```text
content:   不可变压缩件（blob）     → 体积相对小
snapshot:  解压后的可挂载层         → 体积往往更大
GC:        删 image 引用 → content prune → 无引用 snapshot 可回收
```

官方结构（ops.md）：

```text
/var/lib/containerd/
├── io.containerd.content.v1.content/{blobs,ingest}
├── io.containerd.metadata.v1.bolt/
├── io.containerd.snapshotter.v1.overlayfs/{metadata.db,snapshots}
└── ...
```

## 命令速查

```bash
# 拓扑
docker info -f '{{.Driver}} {{.DockerRootDir}}'
sudo ctr namespaces ls
sudo ctr -n moby images ls
sudo ctr -n moby snapshots ls
sudo ctr -n moby content ls | wc -l

# 体积
sudo du -sh /var/lib/containerd \
  /var/lib/containerd/io.containerd.content.v1.content \
  /var/lib/containerd/io.containerd.snapshotter.v1.overlayfs
docker system df

# 依赖
docker ps -aq | xargs -r docker inspect -f '{{.Id}} {{.Name}} {{.GraphDriver.Name}} {{index .GraphDriver.Data "UpperDir"}}'
mount | rg 'io.containerd.snapshotter' || true

# 清理 A
docker builder prune -af
sudo ctr -n moby images ls -q | grep moby-dangling | xargs -r -n1 sudo ctr -n moby images rm
sudo ctr -n moby content prune
```

## 迁 containerd root（可选长期方案）

1. 选外盘路径，例如 `/workspace/data-32T/containerd-root`
2. `systemctl stop docker containerd`
3. `rsync -aHAX /var/lib/containerd/ <new-root>/`
4. 在 `/etc/containerd/config.toml` 设置 `root = "<new-root>"`
5. `systemctl start containerd docker`
6. 确认容器正常后，再删旧目录

## 禁止事项

- 运行中 `rm -rf /var/lib/containerd`
- 只删 `snapshots/*` 留下陈旧 `metadata.db`
- 把 `docker rmi` 与 `ctr images rm` 当成同一操作
- 未确认 GraphDriver 就告诉用户「清了容器就没了」或「绝对安全」
