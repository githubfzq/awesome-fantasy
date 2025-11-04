# Function to reload shell configuration
reload_shell_config() {
  if [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc" 2>/dev/null || true
  fi
  if [ -f "$HOME/.zshrc" ]; then
    source "$HOME/.zshrc" 2>/dev/null || true
  fi
  if [ -f "$HOME/.profile" ]; then
    source "$HOME/.profile" 2>/dev/null || true
  fi
}

# Function to check if x-cmd is installed
check_x_cmd() {
  if command -v x &> /dev/null; then
    echo "✓ x-cmd 已成功安装并可用！"
    return 0
  else
    echo "⚠ x-cmd 安装完成，但命令尚未生效"
    echo "正在尝试重新加载 shell 配置..."
    reload_shell_config
    if command -v x &> /dev/null; then
      echo "✓ x-cmd 现在可以使用了！"
      return 0
    else
      echo "提示: 请运行以下命令之一来重新加载 shell 配置："
      echo "  source ~/.bashrc   # 对于 bash"
      echo "  或"
      echo "  source ~/.zshrc    # 对于 zsh"
      echo "  或重新打开终端窗口"
      return 1
    fi
  fi
}

# Try curl first
if command -v curl &> /dev/null; then
  echo "正在使用 curl 安装 x-cmd..."
  if eval "$(curl https://get.x-cmd.com)"; then
    check_x_cmd
    exit 0
  else
    echo "curl 安装失败，尝试使用 wget..."
  fi
fi

# Try wget as fallback
if command -v wget &> /dev/null; then
  echo "正在使用 wget 安装 x-cmd..."
  if eval "$(wget -O- https://get.x-cmd.com)"; then
    check_x_cmd
    exit 0
  else
    echo "wget 安装失败，尝试安装 curl 后重试..."
  fi
else
  echo "wget 未安装，尝试安装 curl 后重试..."
fi

# Install curl and retry
echo "正在安装 curl..."
if command -v apt-get &> /dev/null; then
  sudo apt-get update && sudo apt-get install -y curl
elif command -v yum &> /dev/null; then
  sudo yum install -y curl
elif command -v apk &> /dev/null; then
  sudo apk add curl
else
  echo "错误: 无法自动安装 curl，请手动安装 curl 或 wget 后重试"
  exit 1
fi

# Retry with curl after installation
echo "curl 安装完成，正在使用 curl 重新安装 x-cmd..."
if eval "$(curl https://get.x-cmd.com)"; then
  check_x_cmd
  exit 0
else
  echo "错误: 安装 x-cmd 失败，请检查网络连接或手动安装"
  exit 1
fi