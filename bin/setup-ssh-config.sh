#!/bin/bash

if [ ! -d ~/.ssh ]; then
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
fi

cat << EOF >> ~/.ssh/config
Host github.com
    Hostname ssh.github.com
    Port 443
    User git
EOF

chmod 600 ~/.ssh/config

echo "SSH config for GitHub has been set up successfully."