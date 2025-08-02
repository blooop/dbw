# DBW - Docker Buildx/Bake Worktree

[![CI](https://github.com/blooop/dbw/actions/workflows/ci.yml/badge.svg)](https://github.com/blooop/dbw/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/dbw.svg)](https://badge.fury.io/py/dbw)
[![Python versions](https://img.shields.io/pypi/pyversions/dbw.svg)](https://pypi.org/project/dbw/)
[![Docker Image](https://img.shields.io/docker/v/dbw/ubuntu-base?label=docker)](https://hub.docker.com/r/dbw/ubuntu-base)

Fast development containers with git worktree isolation and extension caching using Docker Buildx and Bake.

## Features

- 🚀 **Fast container startup** - Extensions cached across repos, no rebuilds
- 🌿 **Git worktree isolation** - Switch branches without committing/stashing
- 🔧 **Reusable extensions** - Pre-built tool fragments (fzf, uv, nodejs, etc.)
- 🐳 **Docker Buildx/Bake** - Parallel builds with advanced caching
- 🔄 **DOOD/DIND support** - Works with Docker-outside-Docker or Docker-in-Docker
- 🎯 **Simple CLI** - One command to enter any repo@branch
- 🖥️ **Full development environment** - X11, GPU, SSH keys, user mapping

## Quick Start

### Installation

```bash
# Install with pipx (recommended)
pipx install dbw

# Or with pip
pip install dbw

# Or from source
git clone https://github.com/blooop/dbw.git
cd dbw
pip install -e .
```

### Basic Usage

```bash
# Launch development environment
dbw launch blooop/python_template@main

# With extensions
dbw launch blooop/python_template@main --with fzf,uv

# Work in subfolder
dbw launch osrf/rocker@main#examples

# Run single command
dbw launch blooop/python_template@main git status

# Switch branches (creates new isolated environment)
dbw launch blooop/python_template@feature/new-feature

# List active environments  
dbw list

# Clean up
dbw destroy blooop/python_template@main
dbw prune --days 7
```

## How It Works

DBW creates isolated development environments using:

1. **Git Worktrees** - Each branch gets its own directory, no conflicts
2. **Docker Compose** - Customizable container configuration per repo
3. **Buildx Cache** - Extension images cached globally, instant reuse
4. **Bake Files** - Parallel builds of base + extensions

### Example Workflow

```bash
# First time - clones repo, builds container
dbw launch myuser/myrepo@main --with fzf,uv
# Inside container: full development environment ready

# Switch to feature branch - new worktree, reuses cached extensions  
dbw launch myuser/myrepo@feature/auth
# Inside container: different code, same tools, no rebuild time

# Work on different repo - reuses all cached extensions
dbw launch other/repo@main --with fzf,uv  
# Inside container: extensions already built, immediate startup
```

## Configuration

### Repository Configuration (`.dbw.yml`)

```yaml
# .dbw.yml - Checked into your repository
extensions:
  - fzf
  - uv
  - nodejs

subfolder: src

platforms:
  - linux/amd64
  - linux/arm64

base_image: dbw/ubuntu-base:22.04

env:
  PYTHONPATH: /workspace/src
  NODE_ENV: development

volumes:
  - ~/.aws:/home/dev/.aws:ro

ports:
  - "3000:3000"
  - "8000:8000"
```

### Extensions

Extensions are reusable Docker fragments. Built-in extensions include:

- **fzf** - Fuzzy finder with ripgrep, fd, bat integration
- **uv** - Fast Python package manager and environment management
- **nodejs** - Node.js with npm, common development tools
- **rust** - Rust toolchain with cargo, clippy, rustfmt
- **go** - Go compiler and development tools

#### Creating Custom Extensions

```bash
# Create extension directory
mkdir -p ~/.local/share/dbw/extensions/myext

# Extension fragment
cat > ~/.local/share/dbw/extensions/myext/docker-compose.fragment.yml << EOF
version: '3.8'
services:
  dev:
    environment:
      MY_TOOL_CONFIG: /workspace/.myext
    volumes:
      - myext_cache:/home/dev/.cache/myext
volumes:
  myext_cache:
EOF

# Extension Dockerfile  
cat > ~/.local/share/dbw/extensions/myext/Dockerfile << EOF
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y mytool
LABEL dbw.extension="myext"
EOF

# Add extension
dbw ext add myext ~/.local/share/dbw/extensions/myext
```

#### Repository-specific Extensions

Place extensions in your repo under `.dbw/extensions/`:

```
myrepo/
├── .dbw/
│   ├── dbw.yml
│   └── extensions/
│       └── custom-tool/
│           ├── Dockerfile
│           └── docker-compose.fragment.yml
└── src/
```

## Docker Modes

DBW supports both Docker-outside-Docker (DOOD) and Docker-in-Docker (DIND):

### Docker-outside-Docker (Default)

Uses host Docker socket. Most efficient, requires Docker installed on host.

```bash
dbw launch myuser/repo@main  # Auto-detects DOOD mode
```

### Docker-in-Docker

Runs Docker daemon inside container. Useful for CI or restricted environments.

```bash
# Start DIND services
docker-compose -f docker-compose.dind.yml up -d

# Or use helper script
./scripts/docker-setup.sh dind

dbw launch myuser/repo@main
```

## Advanced Usage

### Buildx Cache Configuration

```bash
# Local cache (default)
export DBW_CACHE_TYPE=local

# Registry cache for team sharing
export DBW_CACHE_TYPE=registry
export DBW_CACHE_REGISTRY=myregistry.com/dbw-cache

# Inline cache
export DBW_CACHE_TYPE=inline
```

### Multi-platform Builds

```yaml
# .dbw.yml
platforms:
  - linux/amd64
  - linux/arm64
```

```bash
# Build for specific platform
dbw launch --platform linux/arm64 myuser/repo@main
```

### Custom Base Images

```bash
# Set globally
export DBW_BASE_IMAGE=myregistry/custom-base:latest

# Or in repository .dbw.yml
base_image: myregistry/custom-base:latest
```

## CLI Reference

### Commands

```bash
dbw launch <owner>/<repo>[@branch][#subfolder] [command]  # Launch environment
dbw destroy <owner>/<repo>[@branch]                       # Remove environment  
dbw list                                                  # List active environments
dbw prune [--days N]                                      # Clean old images/volumes
dbw ext add <name> <source>                               # Add extension
dbw ext rm <name>                                         # Remove extension
dbw ext list                                              # List extensions
dbw doctor                                                # Run diagnostics
dbw update                                                # Update base images
```

### Flags

```bash
--with <ext1,ext2>    # Comma-separated extensions
--rebuild             # Force rebuild images  
--no-gui              # Disable X11 forwarding
--no-gpu              # Disable GPU support
--verbose             # Enable verbose logging
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DBW_BASE_IMAGE` | `dbw/ubuntu-base:latest` | Default base image |
| `DBW_CACHE_TYPE` | `local` | Cache backend: local, registry, inline |
| `DBW_CACHE_REGISTRY` | | Registry URL for cache |
| `DBW_BUILDX_BUILDER` | `dbw_builder` | Buildx builder name |
| `DBW_WORKSPACES_DIR` | `~/.local/share/dbw/workspaces` | Git repositories |
| `DBW_EXTENSIONS_DIR` | `~/.local/share/dbw/extensions` | Extension cache |

## Troubleshooting

### Common Issues

**Container fails to start**
```bash
# Check Docker availability
dbw doctor

# Check logs
docker logs dbw_myrepo_main_dev
```

**Permission denied on Docker socket**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Logout and login again
```

**Extensions not loading**
```bash
# List available extensions
dbw ext list

# Validate extension
docker compose -f ~/.local/share/dbw/extensions/myext/docker-compose.fragment.yml config
```

**X11 not working**
```bash
# Allow X11 forwarding
xhost +local:docker

# Check DISPLAY variable
echo $DISPLAY
```

### Performance Tips

- Use local Buildx cache for fastest builds
- Pre-pull base images: `docker pull dbw/ubuntu-base:latest`
- Use `--rebuild` sparingly, extensions cache aggressively
- Clean up old environments regularly: `dbw prune`

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/blooop/dbw.git
cd dbw
pip install -e .[dev]

# Run tests
pytest

# Format code  
black .
ruff check --fix .

# Type check
mypy src/dbw
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Related Projects

- [VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers) - VS Code integration
- [GitPod](https://gitpod.io/) - Cloud development environments  
- [Rocker](https://github.com/osrf/rocker) - ROS-focused containers
- [DevPod](https://devpod.sh/) - Universal development environments

## Acknowledgments

- Docker team for Buildx and Bake
- Git team for worktree functionality
- All extension authors and contributors