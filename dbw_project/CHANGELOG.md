# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of DBW (Docker Buildx/Bake Worktree)
- Git worktree isolation for branch switching
- Docker Buildx/Bake integration for parallel builds
- Extension system with caching
- Built-in extensions: fzf, uv
- Docker-in-Docker (DIND) support
- Docker-outside-Docker (DOOD) support
- CLI with Typer framework
- Repository configuration via .dbw.yml
- X11 GUI forwarding
- GPU support with NVIDIA runtime
- SSH key forwarding
- Comprehensive test suite
- CI/CD pipeline with GitHub Actions

### Features

#### Core Functionality
- **Git Operations**: Clone repos as bare repositories, manage worktrees per branch
- **Docker Integration**: Generate Docker Compose files, build with Buildx, manage containers
- **Extension System**: Download, cache, and build reusable tool extensions
- **CLI Interface**: Simple commands for launch, destroy, list, prune operations

#### Extensions
- **fzf**: Fuzzy finder with ripgrep, fd, and bat integration
- **uv**: Fast Python package manager with development tools

#### Development Environment
- **User Mapping**: Host user ID/GID mapping for seamless file permissions
- **Tool Integration**: SSH agent, X11 forwarding, GPU access
- **Volume Mounts**: Workspace, Docker socket, SSH keys, X11 socket

#### Configuration
- **Global Configuration**: Environment variables for cache, base images, builder settings
- **Repository Configuration**: .dbw.yml for per-repo defaults and customization
- **Extension Configuration**: Compose fragments and Dockerfiles for tool installation

#### Docker Modes
- **DOOD (Docker-outside-Docker)**: Use host Docker daemon via socket
- **DIND (Docker-in-Docker)**: Run Docker daemon inside container for isolated environments

#### Caching Strategy
- **Buildx Cache**: Local, registry, or inline caching for build speed
- **Extension Images**: SHA-256 based caching prevents rebuilds
- **Layer Reuse**: Efficient Docker layer caching across projects

## [0.1.0] - 2024-XX-XX

### Added
- Initial project structure and core modules
- Basic CLI commands: launch, destroy, list, prune, ext, doctor, update
- Git worktree management with branch isolation
- Docker Compose generation with extension merging
- Extension cache with hash-based image management
- Docker Buildx/Bake file generation for parallel builds
- System diagnostics and health checks
- Repository configuration loading (.dbw.yml)
- Docker-in-Docker and Docker-outside-Docker support
- X11 GUI forwarding and NVIDIA GPU support
- SSH key and agent forwarding
- User ID/GID mapping for seamless file permissions
- Structured logging with file and console output
- Comprehensive error handling with typed exceptions
- Built-in extensions: fzf (fuzzy finder), uv (Python package manager)
- Template system for Dockerfile and Compose generation
- Unit and integration test suites
- CI/CD pipeline with GitHub Actions
- Documentation and contribution guidelines

### Technical Details

#### Architecture
- **Modular Design**: Separate modules for git operations, Docker management, extensions, etc.
- **Type Safety**: Full type hints with mypy strict mode
- **Error Handling**: Custom exception hierarchy with exit codes
- **Logging**: Structured logging with rich console output
- **Configuration**: Pydantic models for validation and serialization

#### Git Integration
- **Bare Repositories**: Clone once, reuse across branches with worktrees
- **Branch Isolation**: Each branch gets its own directory and container
- **Automatic Updates**: Fetch latest changes when accessing existing repos
- **Dirty State Detection**: Prevent branch switches with uncommitted changes

#### Docker Integration
- **Buildx Backend**: Use Docker Buildx for advanced build features
- **Bake Files**: Generate HCL files for parallel multi-target builds
- **Cache Management**: Support for local, registry, and inline caching
- **Multi-platform**: Support for building multiple architectures

#### Extension System
- **Fragment-based**: Extensions are Compose fragments that extend base service
- **Hash-based Caching**: Extensions rebuilt only when content changes
- **Repository Extensions**: Extensions can be defined within repositories
- **Global Cache**: Extensions cached globally and reused across projects

#### Development Environment
- **Full Feature Parity**: X11, GPU, SSH, user mapping work seamlessly
- **Development Tools**: Common development tools pre-installed in base image
- **Shell Integration**: Bash completion, aliases, and environment setup

### Dependencies
- **Python 3.9+**: Core runtime requirement
- **Typer**: CLI framework with rich help and autocomplete
- **GitPython**: Git repository operations
- **ruamel.yaml**: YAML parsing and generation
- **Pydantic**: Data validation and settings management
- **structlog**: Structured logging
- **tenacity**: Retry logic for network operations
- **docker**: Docker API client
- **Jinja2**: Template rendering for Bake files
- **rich**: Rich console output and progress bars

### Development Dependencies
- **pytest**: Test framework with coverage reporting
- **pytest-mock**: Mocking framework for tests
- **pytest-docker**: Docker integration for tests
- **ruff**: Fast Python linter
- **black**: Code formatter
- **mypy**: Static type checker
- **pre-commit**: Git hooks for code quality

### Documentation
- **README.md**: Comprehensive usage guide with examples
- **CONTRIBUTING.md**: Development and contribution guidelines
- **API Documentation**: Docstrings for all public functions
- **CLI Help**: Built-in help system with examples