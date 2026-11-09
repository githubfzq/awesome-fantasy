# Hermes 本地经验技能

这六个技能来自个人 Hermes 环境，完整保留 SKILL.md、references/ 与 scripts/，用于跨机器复用。

| 技能 | 用途 |
| --- | --- |
| [astronvim-install-cn](astronvim-install-cn/SKILL.md) | 国内网络环境安装 AstroNvim、依赖兼容与 Mason 配置 |
| [docker-compose-service-ops](docker-compose-service-ops/SKILL.md) | Compose 变量、profiles 和服务生命周期排错 |
| [python-env-bootstrap](python-env-bootstrap/SKILL.md) | 项目内 Python ML/RL 环境与 torch/CUDA 版本约束 |
| [repo-dev-server-bootstrap](repo-dev-server-bootstrap/SKILL.md) | 克隆仓库、Herdr 分屏运行开发服务与局域网验证 |
| [docjev-local](docjev-local/SKILL.md) | docjev、OCR 与 Magpie/Jev 接入 |
| [openmaic-magpie-deployment](openmaic-magpie-deployment/SKILL.md) | OpenMAIC、Magpie、TTS 与课堂交互排错 |

## 在其他机器使用

将所需技能的整个目录复制到目标 Hermes profile 的 skills/ 目录。默认是 ~/.hermes/skills/；设置了 HERMES_HOME 时使用该目录下的 skills/。已有同名技能时先比较内容，避免覆盖目标机器的经验。

例如，在仓库根目录执行以下命令，仅在目标技能尚不存在时复制：

```bash
skills_home="${HERMES_HOME:-$HOME/.hermes}/skills"
mkdir -p "$skills_home"
for name in astronvim-install-cn docker-compose-service-ops python-env-bootstrap repo-dev-server-bootstrap docjev-local openmaic-magpie-deployment; do
  if [ -e "$skills_home/$name" ]; then
    printf '跳过已有技能：%s\n' "$name"
  else
    cp -R "skills/$name" "$skills_home/$name"
  fi
done
```

复制后在新的 Hermes 会话中检查技能列表。技能之间提到的 herdr、github、systematic-debugging、blocked-page-recovery 等依赖不在本次同步范围内，需要另行提供。

## 环境差异

- 文档中的 /home/data、/data/workspace/reese、项目目录、端口、GPU 和版本信息描述原机器，使用时先检查目标环境。
- Magpie 地址、模型 ID 和账户路由限制需要在目标网关重新验证；示例中的本地开发凭据不能当作生产配置。
- OpenMAIC 扫描脚本支持 OPENMAIC_REPO 环境变量和输出目录参数。
- capture_systemone.py 是本地请求检查用的模拟服务器，返回固定规则构造的答案，不是实际模型推理结果。只使用 dummy 凭据和测试数据，因为它会打印请求头与部分正文。
- 镜像可用性、上游 API 和软件版本会变化，安装前阅读目标项目的当前文档。

## 本仓库的同步方式

优先通过 SSH 同步 GitHub：

```bash
git clone --branch feat/share-hermes-local-skills git@github.com:githubfzq/awesome-fantasy.git
```

SSH 下载失败时可通过 gh-proxy.com 获取公开仓库内容：

```bash
git -c credential.helper= -c http.extraHeader= clone --depth 1 --branch feat/share-hermes-local-skills https://gh-proxy.com/https://github.com/githubfzq/awesome-fantasy.git
```

代理下载后将 origin 改为 SSH，再向 GitHub 推送；不要向第三方下载代理发送 GitHub 凭据：

```bash
git remote set-url origin git@github.com:githubfzq/awesome-fantasy.git
git push origin HEAD:feat/share-hermes-local-skills
```
