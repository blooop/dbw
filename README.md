# DBW - Docker Buildx/Bake Worktree

Fast development containers with git worktree isolation and extension caching using Docker Buildx and Bake.

[![Ci](https://github.com/blooop/dbw/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/blooop/dbw/actions/workflows/ci.yml?query=branch%3Amain)
[![Codecov](https://codecov.io/gh/blooop/dbw/branch/main/graph/badge.svg?token=Y212GW1PG6)](https://codecov.io/gh/blooop/dbw)
[![GitHub issues](https://img.shields.io/github/issues/blooop/dbw.svg)](https://GitHub.com/blooop/dbw/issues/)
[![GitHub pull-requests merged](https://badgen.net/github/merged-prs/blooop/dbw)](https://github.com/blooop/dbw/pulls?q=is%3Amerged)
[![GitHub release](https://img.shields.io/github/release/blooop/dbw.svg)](https://GitHub.com/blooop/dbw/releases/)
[![License](https://img.shields.io/github/license/blooop/dbw)](https://opensource.org/license/mit/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/downloads/)
[![Pixi Badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json)](https://pixi.sh)

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
# Install with pixi (recommended for development)
pixi install

# Or install with pip
pip install dbw
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

## Development

This project uses [pixi](https://pixi.sh) for dependency management and task automation.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/blooop/dbw.git
cd dbw

# Install dependencies
pixi install

# Run tests
pixi run test

# Run full CI suite
pixi run ci
```

### Available Tasks

```bash
pixi run test          # Run tests
pixi run coverage      # Run tests with coverage
pixi run format        # Format code with ruff
pixi run lint          # Lint code
pixi run mypy          # Type check
pixi run ci            # Run full CI pipeline
pixi run fix           # Auto-fix formatting and linting issues
```

### Docker Integration

DBW includes Docker templates and extensions:

- `templates/` - Base Dockerfile and Compose templates
- `extensions/` - Sample extensions (fzf, uv)
- `docker-compose.dind.yml` - Docker-in-Docker support
- `scripts/docker-setup.sh` - Docker setup automation

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

## Extensions

Built-in extensions include:
- **fzf** - Fuzzy finder with ripgrep, fd, bat integration
- **uv** - Fast Python package manager and environment management

### Creating Custom Extensions

```bash
# Create extension directory
mkdir -p ~/.local/share/dbw/extensions/myext

# Add to DBW
dbw ext add myext path/to/myext
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DBW_BASE_IMAGE` | `dbw/ubuntu-base:latest` | Default base image |
| `DBW_CACHE_TYPE` | `local` | Cache backend: local, registry, inline |
| `DBW_CACHE_REGISTRY` | | Registry URL for cache |
| `DBW_BUILDX_BUILDER` | `dbw_builder` | Buildx builder name |

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

## Contributing

We welcome contributions! Please see the existing project structure and CI setup.

### Development Guidelines

- Use pixi for dependency management
- Follow existing code style (ruff, black)
- Add tests for new functionality
- Update documentation as needed

## License

MIT License - see [LICENSE](LICENSE) file.