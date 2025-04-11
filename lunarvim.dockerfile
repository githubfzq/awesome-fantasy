FROM ubuntu:22.04

# use tsinghua mirror for ubuntu arm64
RUN sed -i 's|ports.ubuntu.com|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y ca-certificates && \
    sed -i 's|http://|https://|g' /etc/apt/sources.list && \
    apt-get update
RUN apt-get install -y openssh-client
COPY bin/*.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/*.sh && setup-ssh-config.sh

WORKDIR /root
# `apt-get install -y neovim` not get v0.9.0+ on arm64 ubuntu, 
# install from unstable PPA (stable PPA not contain v0.9.0+)

RUN apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:neovim-ppa/unstable && \
    sed -i 's/ppa.launchpadcontent.net/launchpad.proxy.ustclug.org/g' /etc/apt/sources.list.d/* && \
    apt-get update && apt-get install -y neovim

# install lvim essentials
RUN apt-get install -y git make python3-pip nodejs npm cargo ripgrep curl

# install optional
# RUN yes | add-apt-repository ppa:lazygit-team/release && \
#     apt-get update && apt-get install -y lazygit
# PPA not have a release for ubuntu jammy, 
# install from tar release according to lazygit README and use github proxy

RUN curl -O https://gh.llkk.cc/https://github.com/jesseduffield/lazygit/releases/download/v0.48.0/lazygit_0.48.0_Linux_arm64.tar.gz && \
    tar xf lazygit_0.48.0_Linux_arm64.tar.gz lazygit && install lazygit -D -t /usr/local/bin

# update nodejs
ENV NODE_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/nodejs-release/
RUN npm config set registry https://registry.npmmirror.com && \
    npm install -g n && n stable

# RUN LV_BRANCH='release-1.4/neovim-0.9' bash <(curl -s https://gh.llkk.cc/https://raw.githubusercontent.com/LunarVim/LunarVim/release-1.4/neovim-0.9/utils/installer/install.sh)