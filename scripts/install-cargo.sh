#!/usr/bin/env bash

# 版本比较函数：比较两个版本号，如果第一个版本小于第二个返回 0（成功），否则返回 1
version_lt() {
  local version1=$1
  local version2=$2
  if [ "$(printf '%s\n' "$version1" "$version2" | sort -V | head -n1)" != "$version1" ]; then
    return 1  # version1 >= version2
  else
    return 0  # version1 < version2
  fi
}

# 检查 apt 源中 cargo 的可用版本
echo "正在检查 apt 源中 cargo 的版本..."

# 更新包列表
sudo apt-get update -qq

# 获取 apt 源中 cargo 的版本号（提取 Candidate 行的版本号，去掉后缀如 -1ubuntu1）
APT_VERSION=$(apt-cache policy cargo 2>/dev/null | grep -E '^\s+Candidate:' | sed -E 's/.*Candidate:[[:space:]]*([0-9]+\.[0-9]+\.[0-9]+).*/\1/' | head -n1)

if [ -z "$APT_VERSION" ]; then
  echo "⚠ 无法从 apt 源获取 cargo 版本信息，使用 rustup 安装以确保获得最新版本"
  USE_RUSTUP=true
else
  echo "apt 源中的 cargo 版本: $APT_VERSION"
  
  # 检查版本是否低于 1.77.2
  if version_lt "$APT_VERSION" "1.77.2"; then
    echo "⚠ apt 源中的版本 ($APT_VERSION) 低于 1.77.2，使用 rustup 安装以获取更新版本"
    USE_RUSTUP=true
  else
    echo "✓ apt 源中的版本 ($APT_VERSION) 满足要求 (>= 1.77.2)，使用 apt-get 安装"
    USE_RUSTUP=false
  fi
fi

if [ "$USE_RUSTUP" = true ]; then
  echo "正在通过 rustup 安装 cargo..."
  
  # 尝试使用 x-cmd 设置镜像
  if command -v x &> /dev/null; then
    echo "使用 x-cmd 设置 cargo 镜像..."
    x mirror cargo set tuna
  else
    # 如果 x-cmd 不可用，使用环境变量设置镜像
    echo "x-cmd 未安装，使用环境变量设置镜像..."
    export RUSTUP_DIST_SERVER=https://mirrors.tuna.tsinghua.edu.cn/rustup
    export RUSTUP_UPDATE_ROOT=https://mirrors.tuna.tsinghua.edu.cn/rustup/rustup
    echo "使用中国镜像加速: $RUSTUP_DIST_SERVER"
  fi
  
  # 使用 rustup 安装脚本安装
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  
  # 激活 cargo 环境
  if [ -f "$HOME/.cargo/env" ]; then
    echo "正在激活 cargo 环境..."
    source "$HOME/.cargo/env"
    echo "✓ cargo 已激活并可用！"
  else
    echo "⚠ 警告: 未找到 ~/.cargo/env 文件，请手动运行: source ~/.cargo/env"
  fi
else
  echo "正在通过 apt-get 安装 cargo..."
  sudo apt-get install -y cargo
fi

echo "✓ cargo 安装完成！"