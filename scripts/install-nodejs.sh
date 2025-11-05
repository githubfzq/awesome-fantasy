#!/usr/bin/env bash

echo "正在安装/升级 Node.js..."

# 设置 npm 全局安装路径到 home 目录，避免权限问题
NPM_GLOBAL_DIR="$HOME/.npm-global"

# 设置 n 的安装路径到 home 目录，避免权限问题
N_PREFIX="$HOME/.n"
export N_PREFIX

# 检查是否已安装 nodejs/npm
if ! command -v node &> /dev/null && ! command -v npm &> /dev/null; then
  echo "未检测到 nodejs/npm，正在安装基础版本..."
  sudo apt-get update -qq
  sudo apt-get install -y nodejs npm
fi

# 设置 npm 配置（可选，加速下载）
if command -v npm &> /dev/null; then
  echo "设置 npm 配置..."
  if [ ! -d "$NPM_GLOBAL_DIR" ]; then
    mkdir -p "$NPM_GLOBAL_DIR"
  fi
  npm config set prefix "$NPM_GLOBAL_DIR"
  echo "✓ npm 全局安装路径设置为: $NPM_GLOBAL_DIR"
  
  # 将 npm 全局 bin 目录添加到 PATH
  if [[ ":$PATH:" != *":$NPM_GLOBAL_DIR/bin:"* ]]; then
    export PATH="$NPM_GLOBAL_DIR/bin:$PATH"
    echo "✓ 已添加 $NPM_GLOBAL_DIR/bin 到 PATH"
  fi
  
  # 将 n 的 bin 目录添加到 PATH（如果存在）
  if [[ ":$PATH:" != *":$N_PREFIX/bin:"* ]]; then
    export PATH="$N_PREFIX/bin:$PATH"
    echo "✓ 已添加 $N_PREFIX/bin 到 PATH"
  fi
  
  # 设置 npm 镜像加速
  echo "设置 npm 镜像加速..."
  # 尝试使用 x-cmd 设置镜像
  # x 是一个 shell 函数，需要先加载 x-cmd 的初始化文件
  if [ -f "$HOME/.x-cmd.root/X" ]; then
    # shellcheck source=/dev/null
    source "$HOME/.x-cmd.root/X"
  fi
  
  # 检查 x 函数或 x-cmd 可执行文件是否可用
  X_CMD_AVAILABLE=false
  if type x &> /dev/null 2>&1; then
    X_CMD_AVAILABLE=true
    X_CMD_CMD="x"
  elif command -v x-cmd &> /dev/null; then
    X_CMD_AVAILABLE=true
    X_CMD_CMD="x-cmd"
  fi
  
  if [ "$X_CMD_AVAILABLE" = true ]; then
    echo "使用 x-cmd 设置 npm 镜像..."
    $X_CMD_CMD mirror npm set npmmirror
  else
    # 如果 x-cmd 不可用，使用 npm config 设置镜像
    echo "x-cmd 未安装，使用 npm config 设置镜像..."
    npm config set registry https://registry.npmmirror.com
  fi
  
  # 设置 Node.js 下载镜像（如果使用 n）
  if [ -z "$NODE_MIRROR" ]; then
    export NODE_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/nodejs-release/
    echo "设置 Node.js 镜像: $NODE_MIRROR"
  fi
fi

# 检查是否已安装 n
if ! command -v n &> /dev/null; then
  echo "正在安装 n (Node.js 版本管理器)..."
  npm install -g n
  # 安装后确保 n 在 PATH 中
  if [[ ":$PATH:" != *":$N_PREFIX/bin:"* ]]; then
    export PATH="$N_PREFIX/bin:$PATH"
  fi
else
  echo "✓ n 已安装"
fi

# 使用 n 安装 LTS 版本
echo "正在使用 n 安装 Node.js LTS 版本..."
echo "n 安装路径: $N_PREFIX"
n lts

# 验证安装
if command -v node &> /dev/null; then
  NODE_VERSION=$(node --version)
  NPM_VERSION=$(npm --version)
  echo "✓ Node.js 安装成功！"
  echo "  Node.js 版本: $NODE_VERSION"
  echo "  npm 版本: $NPM_VERSION"
  
  # 提示用户永久配置 PATH
  echo ""
  echo "提示: 为了在后续 shell 会话中也能使用全局安装的 npm 包和 n 管理的 Node.js，"
  echo "      请将以下内容添加到您的 shell 配置文件中 (~/.bashrc 或 ~/.zshrc):"
  echo ""
  echo "      export N_PREFIX=\"\$HOME/.n\""
  echo "      export PATH=\"\$HOME/.npm-global/bin:\$N_PREFIX/bin:\$PATH\""
  
  # 尝试自动添加到 shell 配置文件
  SHELL_CONFIG=""
  if [ -f "$HOME/.bashrc" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
  elif [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
  fi
  
  if [ -n "$SHELL_CONFIG" ]; then
    # 检查是否已包含配置
    if ! grep -q "N_PREFIX" "$SHELL_CONFIG" 2>/dev/null; then
      {
        echo ""
        echo "# Node.js and npm configuration"
        echo "export N_PREFIX=\"\$HOME/.n\""
        echo "export PATH=\"\$HOME/.npm-global/bin:\$N_PREFIX/bin:\$PATH\""
      } >> "$SHELL_CONFIG"
      echo "✓ 已自动添加到 $SHELL_CONFIG"
    else
      echo "✓ 配置已存在于 $SHELL_CONFIG"
    fi
  fi
else
  echo "⚠ 警告: Node.js 安装可能未完成，请检查错误信息"
  exit 1
fi

