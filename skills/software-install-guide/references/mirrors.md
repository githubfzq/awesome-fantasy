# ghproxy 镜像对照表（2026-08-21 实测）

## 链接格式（前缀代理，release 与 archive 通用）

```
原始：https://github.com/<owner>/<repo>/releases/download/<tag>/<file>
加速：https://<镜像域名>/https://github.com/<owner>/<repo>/releases/download/<tag>/<file>
```

克隆仓库（git 通道，与 release 通道格式相同的前缀写法）：

```
git clone https://gh-proxy.com/https://github.com/<owner>/<repo>.git
```

## 镜像优先级

| 优先级 | 域名 | 状态（2026-08-21） | 备注 |
|---|---|---|---|
| 1 | `gh-proxy.com` | ✅ 可用 | 国内云服务器直连极快（秒级下载 13MB）；返回节点常在香港 |
| 2 | `ghproxy.net` | ✅ 备用 | ghproxy 系替代域名 |
| 3 | `ghfast.top` | ✅ 备用 | |
| 4 | `gh.llkk.cc` | 未实测 | 社区推荐 |
| 4 | `github.akams.cn` | 未实测 | 社区推荐 |
| - | `ghproxy.com` | ⚠️ 不稳 | 主域名经本机代理常返回 502；ghproxy 官方主推 gh-proxy.com |

## 环境事实（用户机器）

- **国内云服务器**（腾讯云 Lighthouse 101.43.75.122 等）：直连 gh-proxy.com 秒下，是**全链路最快路径**；大文件下载后可 `scp` 分发到其他机器
- **用户 Mac 本机**：存在环境代理（127.0.0.1:64318 / 系统代理 7890），经该代理访问 ghproxy 系镜像**极慢、易中断（curl 56）/502**；绕过代理直连会被沙箱拦截。结论：**Mac 上要 GitHub 大文件 → 云服务器中转 + scp 回来**
- `api.github.com` 查最新版本号：Mac 本机走环境代理通常可达；国内服务器直连常超时

## 镜像可用性探测方法

```bash
# 用 range 请求只拉 1KB 探测，避免整包下载
curl -s -o /dev/null -w "%{http_code}" -m 15 -r 0-1024 \
  "https://gh-proxy.com/https://github.com/<owner>/<repo>/releases/download/<tag>/<file>"
# 200/206 = 可用
```

## 已验证的典型下载（frp v0.71.0）

```
https://gh-proxy.com/https://github.com/fatedier/frp/releases/download/v0.71.0/frp_0.71.0_linux_amd64.tar.gz
https://gh-proxy.com/https://github.com/fatedier/frp/releases/download/v0.71.0/frp_0.71.0_darwin_arm64.tar.gz
```
