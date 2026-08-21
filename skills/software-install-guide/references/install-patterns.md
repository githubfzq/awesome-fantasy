# 安装模式模板库

## 1. systemd 服务单元（Linux，系统级 /etc/systemd/system/<tool>.service）

```ini
[Unit]
Description=<Tool> Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/<tool> -c /etc/<tool>/<tool>.toml
Restart=on-failure
RestartSec=5s
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now <tool>     # 已 enable 的服务此命令非零退出≠失败
systemctl is-active <tool>             # 验证
journalctl -u <tool> -n 10 --no-pager  # 看日志
```

## 2. 用户级 systemd（无 sudo，~/.config/systemd/user/<tool>.service）

```bash
systemctl --user daemon-reload
systemctl --user enable --now <tool>
sudo loginctl enable-linger $USER   # 注销后仍常驻；无 sudo 时用 nohup/tmux 兜底
```

## 3. macOS LaunchAgent（~/Library/LaunchAgents/com.<vendor>.<tool>.plist）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.<vendor>.<tool></string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/<user>/.local/bin/<tool></string>
        <string>-c</string>
        <string>/Users/<user>/.config/<tool>/<tool>.toml</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/<user>/.config/<tool>/<tool>.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/<user>/.config/<tool>/<tool>.log</string>
</dict>
</plist>
```

```bash
launchctl load -w ~/Library/LaunchAgents/com.<vendor>.<tool>.plist
# WorkBuddy 会话内 launchctl 可能报 5: I/O error（用户域不可用），让用户在自己的终端执行
```

## 4. 云服务器中转下载 → scp 分发（Mac 需要 GitHub 大文件时的最快路径）

```bash
# ① 在国内云服务器上经 gh-proxy.com 直连下载
ssh ubuntu@101.43.75.122 'curl -sL --connect-timeout 10 -o /tmp/<file> "https://gh-proxy.com/https://github.com/<owner>/<repo>/releases/download/<tag>/<file>" && tar tzf /tmp/<file> >/dev/null && echo OK'

# ② scp 回本地（或直接 scp 到其他目标机器）
scp ubuntu@101.43.75.122:/tmp/<file> /tmp/<file>
```

## 5. 远程 sudo 执行安装脚本（无免密 sudo 时）

```bash
# 正确：脚本先传过去，密码经 stdin 给 sudo -S
scp setup.sh user@server:/tmp/setup.sh
ssh user@server 'echo "<password>" | sudo -S -p "" bash /tmp/setup.sh'

# 错误：ssh 命令内拼 heredoc 会抢占 stdin，sudo 读不到密码（3 次失败）
```

## 6. 二进制安装布局速查

| 场景 | 二进制 | 配置 | 常驻 |
|---|---|---|---|
| Linux + sudo | `/usr/local/bin/` | `/etc/<tool>/` | systemd 系统级 |
| Linux 无 sudo | `~/.local/bin/` | `~/.config/<tool>/` | systemd 用户级 / nohup |
| macOS | `~/.local/bin/`（或 brew） | `~/.config/<tool>/` | LaunchAgent / brew services |
