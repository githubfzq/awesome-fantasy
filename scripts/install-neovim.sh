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

# 检查 apt 源中 neovim 的可用版本
echo "正在检查 apt 源中 neovim 的版本..."

# 更新包列表
sudo apt-get update -qq

# 获取 apt 源中 neovim 的版本号（提取 Candidate 行的版本号，去掉后缀如 -1ubuntu1）
APT_VERSION=$(apt-cache policy neovim 2>/dev/null | grep -E '^\s+Candidate:' | sed -E 's/.*Candidate:[[:space:]]*([0-9]+\.[0-9]+\.[0-9]+).*/\1/' | head -n1)

if [ -z "$APT_VERSION" ]; then
  echo "⚠ 无法从 apt 源获取 neovim 版本信息，使用 PPA 安装以确保获得最新版本"
  USE_PPA=true
else
  echo "apt 源中的 neovim 版本: $APT_VERSION"
  
  # 检查版本是否低于 0.9.0
  if version_lt "$APT_VERSION" "0.9.0"; then
    echo "⚠ apt 源中的版本 ($APT_VERSION) 低于 0.9.0，使用 PPA 安装以获取更新版本"
    USE_PPA=true
  else
    echo "✓ apt 源中的版本 ($APT_VERSION) 满足要求 (>= 0.9.0)，使用 apt-get 安装"
    USE_PPA=false
  fi
fi

if [ "$USE_PPA" = true ]; then
  echo "正在通过 PPA 安装 neovim..."
  sudo apt-get install -y software-properties-common
  sudo add-apt-repository -y ppa:neovim-ppa/unstable
  # 使用中国镜像加速
  sudo sed -i 's/ppa.launchpadcontent.net/launchpad.proxy.ustclug.org/g' /etc/apt/sources.list.d/* 2>/dev/null || true
  sudo apt-get update
  sudo apt-get install -y neovim
else
  echo "正在通过 apt-get 安装 neovim..."
  sudo apt-get install -y neovim
fi

echo "✓ neovim 安装完成！"