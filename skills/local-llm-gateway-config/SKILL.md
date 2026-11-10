---
name: local-llm-gateway-config
description: 当需要把项目模型配置指向本机 LLM 网关（Magpie 等 OpenAI 兼容端点）时使用。
agent_created: true
---

# 本地 LLM 网关接入（local-llm-gateway-config）

规范"把一个项目/应用的模型配置指向本机 LLM 网关"的完整流程：发现网关 → 探测能力 → 写入项目配置 → 端到端验证。适用 Magpie、Ollama、LM Studio、cliproxyapi 等任何 OpenAI 兼容端点。

## 一、发现与探测

1. **找监听端口**：`lsof -nP -iTCP -sTCP:LISTEN | grep -i <app>`；常见：Magpie 3425、Ollama 11434、cliproxyapi 8317。
2. **列模型**：`curl -s http://127.0.0.1:<port>/v1/models`（老网关可能是 `/models`）。记录 model id 清单，网关的模型名与上游官方名可能不同（如 `auto/auto`、`auto/glm-5.3-flashx`、`workbuddy/glm-5.3-flash`）。
3. **连通性预检**：直接 curl 一次 `/v1/chat/completions`，确认鉴权要求——很多本地网关（如 Magpie）**不校验 Bearer key**，任意值都返回 200。
4. **列出 ≠ 可用**：`/v1/models` 返回的 id 只代表网关认识它，不代表上游授权可用。选定模型后必须用目标 id 真实 curl 一次（2026-11-01 实测 Magpie：`auto/gemini-3.8-flash` → "Copilot: The requested model is not supported"；`auto/gemini-3.5-flash` → "WorkBuddy AI: model not allowed for user type personal_free_user"；`auto/glm-5.3-flashx` 可用但 reasoning 吃 token，见 4.5）。错误消息会指明是哪个上游拒的，按提示换 id。

## 二、写入项目配置（以 OpenBiliClaw 类 TOML 项目为例）

```toml
[llm.instances."magpie"]
name = "Magpie 本机网关"
provider_type = "openai_compatible"
enabled = true
api_key = "sk-local-placeholder"   # 见下方坑 1
model = "auto/auto"                # 用 /v1/models 里确认存在的 id
base_url = "http://127.0.0.1:3425/v1"
```
再把 `default_chain` 指向该实例（或按用户选择追加为备选）。

## 三、坑（Pitfalls）

1. **api_key 不能留空，即使网关不要 key**。多数项目配置校验（如 OpenBiliClaw `config.py` 的 blocking issue：`启用的 openai_compatible 实例缺少 API Key`）只查非空字符串。填一个占位值即可，如 `sk-local-placeholder`。
2. **禁止写 `{{SECRET_...}}` 形式的占位符**——Hermes 安全层会在 patch/write_file 落盘时把疑似 secret 的模式改写成字面 `***`，且 diff 里看不到真实结果，容易陷入反复改占位符的死循环。教训：**不要制造看起来像 secret 的内容**；需要非空 api_key 时直接写普通明文占位值。
3. **改完必须 `config-show`（或项目等价命令）验证实例注册成功**，再用项目自身的 provider 代码真实调用一次（不只是 curl）——config 加载成功 ≠ SDK 调用链路通。
4. 配置文件若是 gitignore 的本地配置（如 `config.toml`），改动不进版本库，无需走 worktree 流程；但要检查顺手 `uv sync`/安装依赖有没有污染 lockfile（uv 会把 uv.lock 重写为镜像源，验证后 `git checkout uv.lock` 还原）。
5. 默认链替换是用户决策点：替换 / 优先+备选 / 仅新增不动链，先问再改。
6. 项目要求的 api_key 校验有时只看非空，但安全层会把疑似 secret 的占位符改写成 `***`——落盘后用 grep/sed 直接读文件确认最终值，不要信 patch diff 里的回显（diff 可能显示改写后的假值）。

## 四、验证清单

- [ ] `lsof` 确认网关进程在跑、端口正确
- [ ] `/v1/models` 返回且目标 model id 在清单里
- [ ] 项目 `config-show` 显示实例已注册、无 blocking issue
- [ ] 通过项目 provider 层真实发起一次对话，拿到非空回复与实际 model 名
- [ ] 服务跑一段时间后复查日志：reasoning 模型可能导致延迟暴露的失败（见 4.5）

## 四点五、reasoning 模型吃光 max_tokens（2026-10-29 OpenBiliClaw 实测）

**现象**：配置加载成功、curl 直连也正常，但项目跑一段时间后报
`openai_compatible returned reasoning but no final content (finish_reason=length)`
→ `All providers failed (<网关实例>)`。根因：网关路由到 thinking/reasoning 模型（Magpie `auto/*` 路由组尤其如此，实际可能路由到 hy4-preview 等），推理 token 计入 max_tokens 预算；项目侧结构化任务（keyword planner 等）给的 max_tokens 较小，推理未结束预算就耗尽，最终答案被截断。

**修复选项**（按优先级）：
1. 实例配置里把 `reasoning_effort` 降为 `low`（或项目支持的关闭项）；
2. 调大该调用链路的 max_tokens / num_ctx；
3. **给链上补一个 fallback 实例**（如把原直连 provider 加回 chain 尾部）——单一网关实例 = 无 fallback，一次截断就是整链失败；
4. 换用网关清单里的非 reasoning 模型 id。

**Magpie CLI 修复路径（2026-10-29 实测，最优解）**：Magpie GUI 自带 CLI（`/Applications/magpie.app/Contents/MacOS/magpie`），支持 routing groups，可为一个调用方建专属组而不影响其他 agent：
```bash
M=/Applications/magpie.app/Contents/MacOS/magpie
$M group add "OpenBiliClaw" models="workbuddy/auto,copilot/auto" routing=smart levels=none
# levels 关键：none = 网关不再向该组模型发送 reasoning 字段；
#            low/medium/high = 只提供这些档位（模型没有的发给最近的档位）
# 然后项目侧 model 改为 group/openbiliclaw
```
注意：某些模型（如 workbuddy 系的 hy4-preview）**忽略 reasoning_effort 参数**，即使在请求里显式带 `reasoning_effort=low` 也照样烧 token——`levels=none`（网关侧不发 reasoning 字段）才是有效手段。levels=none 后模型可能仍返回 `reasoning_content`（模型固有行为），但项目报错检测的是「有 reasoning 且无 content」，content 有值即通过。常用命令：`magpie groups`（列表）、`magpie group <id>`（详情）、`magpie group set <id> k=v`（修改）、`magpie model efforts <provider/model>`（单模型的 reasoning 档位）。

**排查入口**：项目日志 grep `finish_reason=` 与 `All providers failed`；错误消息本身即带修复提示（disable thinking/reasoning or increase max_tokens）。区分容忍度：偶发一两次且系统有降级路径（falling back to interest names 之类）属可容忍噪音；持续出现才必须改配置。

## 五、网关侧多厂商容错（routing group）

单一模型/厂商 = 额度耗尽即整链失败。Magpie 支持 routing group，组内**内建故障转移**：一个组员超额/宕机自动换下一个。为某个调用方建专属组，不影响其他 agent：

```bash
M=/Applications/magpie.app/Contents/MacOS/magpie   # GUI app 自带 CLI，非独立二进制
$M group add "OpenBiliClaw" models="workbuddy/auto,copilot/auto" routing=smart levels=none
$M group set group/openbiliclaw models+=<provider/model>   # 追加厂商提高容错
$M group group/openbiliclaw                                 # 查看组状态
```

- **组员选择看额度体系多样性**：订阅制（workbuddy/copilot/zcode）与余额付费制（minimax-cn/tencent-cloud）混搭，避免同时耗尽。`magpie accounts` 看各家余量与重置周期，`magpie providers` 看全部可用厂商。
- `routing` 选项：smart（分类器分流难度）、order（按列表顺序）、rotate/weight/pace 等；故障转移内建于所有模式，无需特殊配置。
- 组员改动后调用方零改动的前提是 model id 引用 `group/<id>`（组 id 不变，组员增减对调用方透明）。
- 验证：改组后 curl 一次 `/v1/chat/completions` 看实际路由到的 `"model"` 字段，确认新组员可用且 levels=none 仍生效（content 非空）。

## 本机已知网关（环境事实）

- **Magpie**：`http://127.0.0.1:3425/v1`，不校验 key，模型约 170 个（auto/* 路由组、workbuddy/*、tencent-cloud/*、copilot/* 等），`auto/auto` 为全自动路由。
- **Ollama**：`http://localhost:11434`（embedding 用 bge-m3）。
- **cliproxyapi**：端口 8317。

## 六点五、局域网其他机器接入 Magpie（2026-10-31 实测 raspberry + XiaoMi/Termux）

- **回环免 key ≠ 局域网免 key**：从局域网其他机器访问 `http://<mac>.local:3425` 必须带 gateway key（`Authorization: Bearer sk-mag...`），否则 401 "no API key was sent"。
- **发 key**：`magpie gateway-key add <name>`（CLI 与 caller-keys.json 都只回掩码，完整值在创建时显示一次，需让用户从 UI 提供）；`gateway-key list` 看 ID/状态。存放在 `~/.config/magpie/caller-keys.json`，secret 字段是 Keychain 引用。
- **消费方 Hermes 配置形态**（远端机器走 custom provider，与直连厂商同构）：
  ```
  # ~/.hermes/.env
  HERMES_MAGPIE_GATEWAY_KEY=<sk-mag...>
  # config.yaml（hermes config set 写入）
  model.provider: custom
  model.base_url: http://<mac>.local:3425/v1
  model.api_key: ${HERMES_MAGPIE_GATEWAY_KEY}
  ```
  改完重启 gateway：Linux systemd `systemctl --user restart hermes-gateway`；Termux runsv `sv restart $PREFIX/var/service/hermes-gateway`。
- **.local 跨机解析可用**：raspberry(avahi) 与 XiaoMi(Android/Termux) 都能把 `fantasymac-2.local` 解析到 192.168.1.7，mDNS 在同网段 192.168.1.x 工作正常。局限：跨子网/VLAN 或 mDNS 被路由器隔离时失效，届时换静态 DHCP 绑定 IP。注意 Mac 本机 hosts 若手工加过 `<名>.local → 127.0.0.1`，本机 ping 会回环，但其他机器不受影响。
- **macOS TCC 本地网络权限拦 Homebrew Python**：Hermes 运行时是 Homebrew python3.11，未获"本地网络"隐私授权时连接任何局域网 IP 均 `[Errno 65] No route to host`，而 curl/nc/系统 python 正常——看起来像服务挂了其实是客户端权限。识别与修复见技能 hermes-memory-provider 坑 2。验证远端网关连通时先用 curl 对照，别只信 Hermes 内部报错。
- **端到端验证**：curl `/v1/models` 过鉴权 → `hermes chat -q` 拿到非空回复才算通；config 写入成功 ≠ 调用链路通。
- XiaoMi 是 Android Termux（`~/.hermes` 在 com.termux home 下，scp 不能直接写 /tmp，先传 home 再执行）。

## 七、坑：Magpie「点图标打不开」（2026-10-31 实测）

**现象**：点启动台/Finder 的 Magpie 图标没反应，疑似没启动。实际：进程在跑、3425 正常监听、`/v1/models` 正常返回。

**根因**：Magpie 是 LSUIElement 应用（无 Dock 图标），窗口关闭/最小化后被 orderOut 收进托盘——窗口对象还在（CG 层可见，AX 层不可见），但不在任何 Space 上。此时 `open -a`、activate、点托盘图标都弹不回窗口，只能看到"没反应"。

**诊断顺序**：
1. `ps aux | grep magpie` + `lsof -nP -iTCP:3425 -sTCP:LISTEN` → 进程和端口在不在
2. `curl -s http://127.0.0.1:3425/v1/models` → 网关是否正常（正常就只是窗口问题，不用动服务）
3. `computer_use list_windows`（app='magpie'）→ 窗口在不在屏幕上

**修复**：优雅重启是唯一可靠路径（秒级，网关自动恢复）：
```bash
osascript -e 'quit app "magpie"'; 等端口释放; open -a magpie; 等端口就绪
```
**警告**：Hermes 会话的模型请求可能正走 Magpie 网关——重启必须"退出→等端口释放→重启→等 HTTP 200"放在同一条命令里一气呵成，别分步执行留下断窗。`magpie` CLI 也有 `tui`/`web` 模式可当备用入口。

## 参考资料

- `references/openbiliclaw-magpie-2026-10.md` — OpenBiliClaw 接入 Magpie 的完整会话实录（最终配置、pytest 判定、uv 环境坑）。
- `references/openbiliclaw-runtime-2026-10.md` — OpenBiliClaw 生产服务运行时快照（服务形态、测试与运行时相互作用、上游更新状态）。
