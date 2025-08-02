# FZF Extension Dockerfile
# Installs fzf (fuzzy finder) and related tools

FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install fzf and related tools
RUN apt-get update && apt-get install -y \
    # FZF and dependencies
    fzf \
    # fd-find (better find alternative, used by fzf)
    fd-find \
    # ripgrep (better grep, useful with fzf)
    ripgrep \
    # bat (better cat with syntax highlighting)
    bat \
    # tree (directory structure viewer)
    tree \
    # Additional shell tools
    tmux \
    zsh \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for fd (Ubuntu packages it as fdfind)
RUN ln -sf /usr/bin/fdfind /usr/local/bin/fd

# Create symlinks for bat (Ubuntu packages it as batcat)
RUN ln -sf /usr/bin/batcat /usr/local/bin/bat

# Install fzf shell integration
RUN mkdir -p /usr/share/fzf && \
    # Get the key bindings and completion scripts
    find /usr/share -name "*.bash" -path "*/fzf/*" -exec cp {} /usr/share/fzf/ \; 2>/dev/null || true && \
    find /usr/share -name "*.zsh" -path "*/fzf/*" -exec cp {} /usr/share/fzf/ \; 2>/dev/null || true

# Create user setup script
RUN echo '#!/bin/bash\n\
# FZF shell integration setup\n\
if [ -f /usr/share/fzf/key-bindings.bash ]; then\n\
    echo "source /usr/share/fzf/key-bindings.bash" >> ~/.bashrc\n\
fi\n\
if [ -f /usr/share/fzf/completion.bash ]; then\n\
    echo "source /usr/share/fzf/completion.bash" >> ~/.bashrc\n\
fi\n\
\n\
# Add useful aliases\n\
echo "alias fzfp='\''fzf --preview \"bat --color=always --style=numbers --line-range=:500 {}\"'\''" >> ~/.bashrc\n\
echo "alias fzfd='\''fd --type d | fzf'\''" >> ~/.bashrc\n\
echo "alias fzfg='\''rg --line-number --no-heading . | fzf --delimiter : --preview \"bat --color=always --line-range {2}: {1}\"'\''" >> ~/.bashrc\n\
' > /usr/local/bin/setup-fzf.sh && chmod +x /usr/local/bin/setup-fzf.sh

# Labels
LABEL dbw.extension="fzf"
LABEL dbw.version="0.1.0"
LABEL dbw.description="Fuzzy finder with ripgrep, fd, and bat integration"