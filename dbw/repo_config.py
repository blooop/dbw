"""Repository configuration loading for dbw."""

from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML

from .config import RepoConfig
from .errors import ConfigError
from .log import get_logger

logger = get_logger(__name__)

yaml = YAML(typ="safe")


def load_repo_config(worktree_path: Path) -> RepoConfig:
    """Load .dbw.yml or .dbw.json from repository root."""

    # Check for YAML config first
    config_files = [
        worktree_path / ".dbw.yml",
        worktree_path / ".dbw.yaml",
        worktree_path / ".dbw.json",
    ]

    for config_file in config_files:
        if config_file.exists():
            try:
                return _load_config_file(config_file)
            except Exception as e:
                logger.warning(
                    "config.load_failed", file=str(config_file), error=str(e), fallback="defaults"
                )
                # Continue to try other files or return defaults

    # Return default config if no file found
    logger.debug("config.not_found", path=str(worktree_path), using="defaults")
    return RepoConfig()


def _load_config_file(config_file: Path) -> RepoConfig:
    """Load configuration from a specific file."""
    logger.info("config.loading", file=str(config_file))

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            if config_file.suffix == ".json":
                import json

                data = json.load(f)
            else:
                data = yaml.load(f)

        if not isinstance(data, dict):
            raise ConfigError(f"Config file must contain a YAML/JSON object, got {type(data)}")

        # Validate and create RepoConfig
        config = RepoConfig.model_validate(data)
        logger.info("config.loaded", file=str(config_file), extensions=config.extensions)

        return config

    except Exception as e:
        raise ConfigError(f"Failed to load config from {config_file}: {e}") from e


def merge_extensions(
    cli_extensions: list[str],
    repo_extensions: list[str],
    config_extensions: list[str],
) -> list[str]:
    """Merge extensions from different sources.

    Priority: CLI > repo discovery > config file
    """
    # Start with config file extensions
    all_extensions = list(config_extensions)

    # Add discovered repo extensions (if not already present)
    for ext in repo_extensions:
        if ext not in all_extensions:
            all_extensions.append(ext)

    # CLI extensions override everything
    if cli_extensions:
        all_extensions = cli_extensions

    logger.info(
        "extensions.merged",
        cli=cli_extensions,
        repo=repo_extensions,
        config=config_extensions,
        final=all_extensions,
    )

    return all_extensions


def get_working_directory(
    worktree_path: Path, subfolder: Optional[str], config: RepoConfig
) -> Path:
    """Determine working directory inside container.

    Priority: CLI subfolder > config subfolder > repo root
    """
    if subfolder:
        work_dir = worktree_path / subfolder
    elif config.subfolder:
        work_dir = worktree_path / config.subfolder
    else:
        work_dir = worktree_path

    # Validate directory exists
    if not work_dir.exists():
        logger.warning(
            "workdir.not_found",
            requested=str(work_dir.relative_to(worktree_path)),
            fallback="repo_root",
        )
        work_dir = worktree_path

    logger.info("workdir.selected", path=str(work_dir.relative_to(worktree_path) or "."))
    return work_dir


def resolve_base_image(config: RepoConfig, default_base: str) -> str:
    """Resolve base image from config or default."""
    return config.base_image or default_base


def example_dbw_config() -> str:
    """Return example .dbw.yml content."""
    return """# .dbw.yml - DBW repository configuration
# All fields are optional

# Default extensions to load
extensions:
  - fzf
  - uv
  # - nodejs
  # - rust

# Default subfolder to start in (relative to repo root)
subfolder: src

# Target platforms for multi-arch builds
platforms:
  - linux/amd64
  - linux/arm64

# Override base image
base_image: dbw/ubuntu-base:22.04

# Additional environment variables
env:
  PYTHONPATH: /workspace/src
  NODE_ENV: development

# Additional volume mounts (host:container)
volumes:
  - ~/.aws:/home/dev/.aws:ro
  - /var/run/docker.sock:/var/run/docker.sock

# Port mappings for dev servers
ports:
  - "3000:3000"  # React dev server
  - "8000:8000"  # Django/FastAPI
"""
