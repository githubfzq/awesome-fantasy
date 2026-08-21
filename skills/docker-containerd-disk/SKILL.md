---
name: docker-containerd-disk
description: >-
  Docker / containerd 磁盘占用诊断与安全清理技能。用于区分 Docker data-root 与
  /var/lib/containerd、解释 content store 与 overlayfs snapshotter、判断容器
  rootfs 是否依赖系统盘 containerd 数据，并按风险阶梯给出 prune / ctr images rm /
  content prune 方案。当用户提到 /var/lib/containerd、io.containerd.content、
  io.containerd.snapshotter、containerd 占满磁盘、Docker Root Dir 在外盘但系统盘仍很大、
  docker system df、moby-dangling、能否 rm -rf containerd、清理 Docker 镜像缓存时，
  务必使用本技能——即使用户只说「系统盘被 Docker 吃满了」也应触发。
agent_created: true
---

# Docker / containerd 磁盘空间管理

## Overview

现代 Docker 用 **containerd** 做容器运行时。常见误判是：已经把 `data-root` 迁到外盘，
系统盘 `/var/lib/containerd` 仍占数百 GB，以为「Docker 没迁走」。

真相通常是两套存储并存：

| 路径 | 谁写 | 典型内容 |
|------|------|----------|
| Docker `data-root`（如 `/var/lib/docker` 或自定义外盘） | dockerd graph（overlay2） | 镜像层、容器可写层、volume |
| `/var/lib/containerd`（containerd `root`） | containerd | content blob、snapshot、运行时元数据 |

改 `daemon.json` 的 `"data-root"` **不会**自动迁走 containerd root。

## 两个关键子目录（用途）

containerd 管镜像是两段式（见官方 content-flow）：

```text
pull/build → content（压缩 blob）→ unpack → snapshotter（可挂载层）
```

### `io.containerd.content.v1.content`（压缩内容库）

- `blobs/sha256/`：manifest / config / layer tar.gz，按 digest 去重
- `ingest/`：写入中的临时文件
- 不可直接当容器 rootfs；靠 `containerd.io/gc.ref.content.*` 标签保活

### `io.containerd.snapshotter.v1.overlayfs`（解压快照）

- `snapshots/`：layer 解压后的 overlay 目录
- `metadata.db`：父子关系与 Active / Committed 状态
- 体积通常 **大于** content（已解压）

namespace 常为 `moby`（Docker）。`disabled_plugins = ["cri"]` 时一般不是 k8s。

## 诊断 workflow（先证据，后清理）

按顺序执行；详细命令也可跑 `scripts/diagnose.sh`。

### 1. 确认 Docker 与 containerd 拓扑

```bash
docker info | rg -i 'Storage Driver|Docker Root Dir|Runtimes|containerd'
ps -ef | rg '[d]ockerd|[c]ontainerd'
cat /etc/docker/daemon.json 2>/dev/null
rg -n '^\s*root\s*=' /etc/containerd/config.toml 2>/dev/null || true
```

关注：

- `Storage Driver: overlay2` + 外盘 `Docker Root Dir` → 经典图驱动，容器层应在 data-root
- `dockerd ... --containerd=/run/containerd/containerd.sock` → 运行时仍依赖 containerd **进程**
- containerd `root` 未改 → 默认 `/var/lib/containerd`

### 2. 量体积

```bash
sudo du -sh /var/lib/containerd
sudo du -sh /var/lib/containerd/io.containerd.content.v1.content \
            /var/lib/containerd/io.containerd.snapshotter.v1.overlayfs
docker system df
# data-root 可能很大，可后台跑
sudo du -sh "$(docker info -f '{{.DockerRootDir}}')" 2>/dev/null
```

### 3. 判断「容器是否依赖 containerd 目录里的数据」

**运行时依赖**（几乎总是）：在跑容器都有 `containerd-shim`，namespace 多为 `moby`。  
这只说明依赖 containerd **服务**，不等于 rootfs 在 `/var/lib/containerd`。

**磁盘数据依赖**（关键）：

```bash
# 全部容器的 UpperDir 是否都在 Docker Root 下
docker ps -aq | while read id; do
  docker inspect "$id" --format '{{.GraphDriver.Name}} {{index .GraphDriver.Data "UpperDir"}}'
done

# 是否有 mount 引用 containerd snapshotter
mount | rg 'io.containerd.snapshotter' || echo "no snapshotter mounts"

# Active snapshot 是否对得上 docker 容器 ID
sudo ctr -n moby snapshots ls
docker ps -aq
```

判定：

- GraphDriver 全是 `overlay2`，UpperDir 全在 `Docker Root Dir` 下
- `mount` 无 `io.containerd.snapshotter`
- Active snapshot key **对不上**任何容器 ID  

→ `/var/lib/containerd` 的 content/snapshot 主要是 **缓存/残留**，清理一般不拆在跑容器的 rootfs。

### 4. 列出 containerd 侧镜像与来源

```bash
sudo ctr namespaces ls
sudo ctr -n moby images ls
sudo ctr -n moby content ls | head
# 大 blob 常带来源标签，例如 vllm/vllm-openai、paddlepaddle/...
```

`moby-dangling@sha256:...` 是无 tag 残留，优先清理对象。

## 清理阶梯（安全 → 激进）

> 铁律：**不要**在 docker/containerd 运行中 `rm -rf /var/lib/containerd` 或瞎删 `metadata.db`。用引用删除 + GC。

清理前向用户确认档位；默认只做 **A**，除非用户明确要求更激进。

### A. 低风险（推荐默认）

```bash
docker builder prune -af

# 删除 containerd dangling 镜像引用
sudo ctr -n moby images ls -q | grep moby-dangling | xargs -r -n1 sudo ctr -n moby images rm

# 回收无引用 blob
sudo ctr -n moby content prune
```

再量一次 `du -sh` 看回收量。

### B. 中风险（确认 named 镜像不用）

对 **ctr 有、且没有在跑容器依赖、且用户同意** 的 named ref：

```bash
sudo ctr -n moby images rm <ref>
sudo ctr -n moby content prune
```

注意：这只清 **containerd 侧**；外盘 `docker images` 仍在。不要和 `docker rmi` 混为一谈。

若还要腾外盘：

```bash
docker system df
docker image prune -af    # 会删未使用 Docker 镜像，影响面更大，单独确认
```

### C. 高风险（可接受短暂停服）

仅当 A/B 不够、且已确认无 k8s/其他消费方：

```bash
sudo systemctl stop docker containerd
# 更稳妥：备份后清空整个 containerd root，让服务重建元数据
sudo mv /var/lib/containerd /var/lib/containerd.bak.$(date +%Y%m%d)
sudo mkdir -p /var/lib/containerd
sudo systemctl start containerd docker
docker ps   # 确认外盘 overlay2 容器仍可起来
```

失败可回滚 `containerd.bak.*`。不要只删 `snapshots/*` 而留下不一致的 `metadata.db`。

## 输出报告结构

诊断或清理后，用下面结构回复用户：

```markdown
## 结论
（一句话：系统盘 containerd 是缓存还是容器真源）

## 拓扑
- Docker Root Dir / Storage Driver
- containerd root / namespaces

## 占用
- content / snapshotter / docker system df

## 依赖判定
- GraphDriver / UpperDir / snapshotter mounts / Active snapshots

## 建议操作
- 档位 A/B/C + 预期收益与风险

## 已执行（若有）
- 命令与回收前后 du
```

## 代理操作注意点

- 先诊断再清理；默认档 A；破坏性命令需用户确认。
- `du` 大目录可能很慢，对 Docker Root 可后台或只报 `docker system df`。
- 区分三件事：containerd **服务**、containerd **数据目录**、Docker **data-root**。
- 清理后提醒：下次 `pull`/`build` 可能重新写入 containerd。
- 长期方案：把 containerd `root` 也迁到外盘（改 `/etc/containerd/config.toml` 的 `root`，停服迁移），与 `data-root` 对齐。

## 延伸阅读

- 命令清单与判定表：`references/playbook.md`
- 一键诊断：`scripts/diagnose.sh`
