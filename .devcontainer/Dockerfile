FROM ubuntu:22.04

# Create vscode user first
RUN groupadd -g 1000 vscode && \
    useradd -u 1000 -g 1000 -m -s /bin/bash vscode

# Install sudo (ensure it succeeds)
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends sudo && \
    echo 'vscode ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers && \
    rm -rf /var/lib/apt/lists/*

