---
name: deepseek-usage-check
description: 检查 DeepSeek 开放平台账户的剩余额度与余额（总余额、赠送额度、充值余额）。当用户询问 DeepSeek 余额、剩余用量、额度还剩多少、DeepSeek API 余额查询时使用。通过官方 API（GET /user/balance）查询，凭据从环境变量 DEEPSEEK_API_KEY 或运行时参数获取，不落盘。
agent_created: true
---

# DeepSeek 用量与余额查询

通过 DeepSeek 官方 API 查询开放平台账户的剩余额度，无需浏览器登录。

## 使用场景

- "查一下 DeepSeek 还剩多少额度/余额"
- "DeepSeek 账户还能用多久" / "DeepSeek 余额"
- 在脚本、自动化、周报中需要程序化获取 DeepSeek 账户余额

## 凭据获取（按优先级，绝不落盘）

API Key 来源：

1. **KeePass Agent 专用库（推荐，已验证）**：用 `keepass-lookup` 技能从
   `agents.kdbx` 条目 `deepseek` 的**自定义属性「API key」**读取（注意：不是
   Password 字段，Password 存的是网页登录密码；也不是 Notes，Notes 存模型列表）：

   ```bash
   KX=/Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli
   DB="/Users/fanzuquan/Nutstore Files/.symlinks/坚果云/keepass/agents.kdbx"
   KEY=$(cat "/Users/fanzuquan/Nutstore Files/.symlinks/坚果云/keepass/agent_main_pass" \
        | "$KX" show -s -a "API key" "$DB" deepseek 2>/dev/null | tail -1)
   ```

   主密码文件路径与「绝不读取个人库」等规范见用户级技能 `keepass-lookup`。
2. 环境变量 `DEEPSEEK_API_KEY`
3. 运行时由用户直接提供（仅当次会话使用）

若都没有，向用户索要 API Key（DeepSeek 开放平台 → API Keys 页面创建）。不要提示用户把 key 写入配置文件。Key 属于敏感凭据：不写入任何文件、日志或记忆，输出时最多显示前 6 位。

## 查询方式

执行内置脚本（纯 Python 标准库，无第三方依赖）：

```bash
# 方式一：环境变量（推荐）
DEEPSEEK_API_KEY=sk-xxx python3 scripts/check_balance.py

# 方式二：命令行参数（注意 key 会进 shell history，优先用环境变量）
python3 scripts/check_balance.py --api-key sk-xxx

# 输出原始 JSON
python3 scripts/check_balance.py --json
```

输出示例：

```
账户状态: 可用
[CNY] 总余额: 110.00  (赠送额度: 10.00 | 充值余额: 100.00)
```

## 返回字段说明

| 字段 | 含义 |
|------|------|
| `is_available` | 账户是否可用（余额耗尽/欠费时为 false） |
| `balance_infos[].currency` | 币种（CNY / USD） |
| `balance_infos[].total_balance` | 总余额 = 赠送 + 充值 |
| `balance_infos[].granted_balance` | 赠送额度（有有效期，优先消耗） |
| `balance_infos[].topped_up_balance` | 充值余额 |

## 错误处理

- **401 Unauthorized**：API Key 无效或已删除 → 请用户重新生成 Key
- **连接失败**：检查网络；如需代理可设 `HTTPS_PROXY` 环境变量（脚本基于 urllib，自动识别）
- **`is_available: false`**：余额耗尽或账户欠费，提醒用户充值

## 边界说明

- 本技能只查账户余额。按模型/按日的用量明细（usage breakdown）DeepSeek 未开放 API，仅能在 platform.deepseek.com 网页控制台查看；如用户需要用量明细，说明此限制。
- KeePass 条目 `deepseek` 的 Notes 字段记录了账户可用模型（deepseek-chat / deepseek-reasoner 等），可作为参考信息一并读取。
- API Key 属于敏感凭据，输出结果时不要回显完整 Key（最多显示前 6 位）。
