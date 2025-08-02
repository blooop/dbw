# UV Extension Dockerfile
# Installs uv (fast Python package manager) and Python development tools

FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and development dependencies
RUN apt-get update && apt-get install -y \
    # Python and build tools
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    # Build dependencies for Python packages
    build-essential \
    pkg-config \
    # Common development libraries
    libssl-dev \
    libffi-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncursesw5-dev \
    libxml2-dev \
    libxmlsec1-dev \
    liblzma-dev \
    # Version control
    git \
    # Download tools
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH for all users
ENV PATH="/root/.cargo/bin:$PATH"
RUN ln -sf /root/.cargo/bin/uv /usr/local/bin/uv

# Pre-install common Python development tools with uv
RUN uv tool install --force \
    black \
    ruff \
    mypy \
    pytest \
    ipython \
    jupyter \
    pre-commit \
    poetry \
    pipenv

# Create useful aliases and shell functions
RUN echo '#!/bin/bash\n\
# UV convenience functions and aliases\n\
\n\
# Quick project setup\n\
alias uv-init="uv init && uv add --dev pytest black ruff mypy"\n\
alias uv-sync="uv sync --all-extras --dev"\n\
alias uv-lock="uv lock --all-extras"\n\
\n\
# Development shortcuts\n\
alias uv-test="uv run pytest"\n\
alias uv-format="uv run black . && uv run ruff check --fix ."\n\
alias uv-lint="uv run ruff check ."\n\
alias uv-type="uv run mypy ."\n\
\n\
# Virtual environment management\n\
uvenv() {\n\
    if [ -f "pyproject.toml" ]; then\n\
        echo "Activating UV project environment..."\n\
        source .venv/bin/activate\n\
    else\n\
        echo "No pyproject.toml found. Creating new UV project..."\n\
        uv init\n\
        source .venv/bin/activate\n\
    fi\n\
}\n\
\n\
# Quick package installation\n\
uvi() {\n\
    uv add "$@"\n\
}\n\
\n\
uvid() {\n\
    uv add --dev "$@"\n\
}\n\
\n\
# Run commands in the UV environment\n\
uvr() {\n\
    uv run "$@"\n\
}\n\
' > /usr/local/bin/setup-uv.sh && chmod +x /usr/local/bin/setup-uv.sh

# Set up UV completion (will be sourced in .bashrc)
RUN echo '#!/bin/bash\n\
# UV shell completion setup\n\
if command -v uv >/dev/null 2>&1; then\n\
    eval "$(uv --completion bash)"\n\
fi\n\
\n\
# Source UV convenience functions\n\
source /usr/local/bin/setup-uv.sh\n\
\n\
# Auto-activate virtual environment if in UV project\n\
if [ -f "pyproject.toml" ] && [ -d ".venv" ]; then\n\
    source .venv/bin/activate\n\
fi\n\
' > /usr/local/bin/uv-bashrc.sh && chmod +x /usr/local/bin/uv-bashrc.sh

# Labels
LABEL dbw.extension="uv"
LABEL dbw.version="0.1.0"
LABEL dbw.description="Fast Python package manager with development tools"