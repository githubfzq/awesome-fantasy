#!/bin/bash

# 启动SSH Agent
eval $(ssh-agent -s) > /dev/null

# 添加GitHub私钥
if [ -f /workspace/id_github ]; then
    ssh-add /workspace/id_github
    echo "SSH key added successfully."
else
    echo "Error: /workspace/id_github not found."
    exit 1
fi

# 打印SSH Agent信息
echo "SSH Agent started with PID: $SSH_AGENT_PID"